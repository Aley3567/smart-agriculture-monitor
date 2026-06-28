<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, computed } from 'vue'
import { useSensorStore } from '../stores/sensor'
import api from '../utils/api'

const sensorStore = useSensorStore()

// --- 状态 ---
const mapContainer = ref(null)
const mapError = ref('')
const mapLoaded = ref(false)

const location = reactive({
  gcjLng: 106.55,
  gcjLat: 29.56,
  wgsLng: 106.5467,
  wgsLat: 29.5573,
  name: '重庆市',
})

const searchKeyword = ref('')
const cityList = ref([])
const showDropdown = ref(false)
const searching = ref(false)

const weather = ref(null)
const weatherLoading = ref(false)
const weatherError = ref('')

let mapInstance = null
let markerInstance = null
let geocoderInstance = null
let searchTimer = null

// --- GCJ02 <-> WGS84 坐标转换 ---
const PI = Math.PI
const SEMI_AXIS = 6378245.0
const EE = 0.00669342162296594

function transformLat(x, y) {
  let ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x))
  ret += (20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0 / 3.0
  ret += (20.0 * Math.sin(y * PI) + 40.0 * Math.sin(y / 3.0 * PI)) * 2.0 / 3.0
  ret += (160.0 * Math.sin(y / 12.0 * PI) + 320 * Math.sin(y * PI / 30.0)) * 2.0 / 3.0
  return ret
}

function transformLng(x, y) {
  let ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x))
  ret += (20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0 / 3.0
  ret += (20.0 * Math.sin(x * PI) + 40.0 * Math.sin(x / 3.0 * PI)) * 2.0 / 3.0
  ret += (150.0 * Math.sin(x / 12.0 * PI) + 300.0 * Math.sin(x / 30.0 * PI)) * 2.0 / 3.0
  return ret
}

function gcj02ToWgs84(lng, lat) {
  let dLat = transformLat(lng - 105.0, lat - 35.0)
  let dLng = transformLng(lng - 105.0, lat - 35.0)
  const radLat = lat / 180.0 * PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180.0) / ((SEMI_AXIS * (1 - EE)) / (magic * sqrtMagic) * PI)
  dLng = (dLng * 180.0) / (SEMI_AXIS / sqrtMagic * Math.cos(radLat) * PI)
  return { lng: lng - dLng, lat: lat - dLat }
}

function wgs84ToGcj02(lng, lat) {
  let dLat = transformLat(lng - 105.0, lat - 35.0)
  let dLng = transformLng(lng - 105.0, lat - 35.0)
  const radLat = lat / 180.0 * PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180.0) / ((SEMI_AXIS * (1 - EE)) / (magic * sqrtMagic) * PI)
  dLng = (dLng * 180.0) / (SEMI_AXIS / sqrtMagic * Math.cos(radLat) * PI)
  return { lng: lng + dLng, lat: lat + dLat }
}

// --- 高德地图加载 ---
function loadAMapScript() {
  return new Promise((resolve, reject) => {
    if (window.AMap) {
      resolve(window.AMap)
      return
    }
    const key = import.meta.env.VITE_AMAP_JS_KEY || '8e30482604491d711f3c060870773585'
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${key}&plugin=AMap.Scale,AMap.ToolBar,AMap.Geocoder`
    script.onload = () => {
      if (window.AMap) {
        resolve(window.AMap)
      } else {
        reject(new Error('AMap 对象未加载'))
      }
    }
    script.onerror = () => reject(new Error('高德地图脚本加载失败，可能是域名白名单限制'))
    document.head.appendChild(script)
  })
}

function initMap(AMap) {
  if (!mapContainer.value) return

  mapInstance = new AMap.Map(mapContainer.value, {
    zoom: 10,
    center: [location.gcjLng, location.gcjLat],
    mapStyle: 'amap://styles/whitesmoke',
  })

  mapInstance.addControl(new AMap.Scale())
  mapInstance.addControl(new AMap.ToolBar({ position: 'RT' }))

  markerInstance = new AMap.Marker({
    position: [location.gcjLng, location.gcjLat],
    draggable: true,
    cursor: 'move',
  })
  mapInstance.add(markerInstance)

  geocoderInstance = new AMap.Geocoder()

  markerInstance.on('dragend', (e) => {
    const pos = e.target.getPosition()
    onMapPick(pos.lng, pos.lat)
  })

  mapInstance.on('click', (e) => {
    const lng = e.lnglat.getLng()
    const lat = e.lnglat.getLat()
    markerInstance.setPosition([lng, lat])
    onMapPick(lng, lat)
  })
}

function onMapPick(gcjLng, gcjLat) {
  location.gcjLng = Math.round(gcjLng * 10000) / 10000
  location.gcjLat = Math.round(gcjLat * 10000) / 10000
  const wgs = gcj02ToWgs84(gcjLng, gcjLat)
  location.wgsLng = Math.round(wgs.lng * 10000) / 10000
  location.wgsLat = Math.round(wgs.lat * 10000) / 10000

  if (geocoderInstance) {
    geocoderInstance.getAddress([gcjLng, gcjLat], (status, result) => {
      if (status === 'complete' && result.regeocode) {
        location.name = result.regeocode.formattedAddress || '未知位置'
      }
    })
  }

  debounceFetchWeather()
}

// --- 天气获取 ---
let weatherTimer = null
function debounceFetchWeather() {
  clearTimeout(weatherTimer)
  weatherTimer = setTimeout(fetchWeather, 400)
}

async function fetchWeather() {
  weatherLoading.value = true
  weatherError.value = ''
  try {
    const res = await api.get('/api/weather', {
      params: { lat: location.wgsLat, lon: location.wgsLng },
    })
    if (res.data.error) {
      weatherError.value = res.data.error
      weather.value = null
    } else {
      weather.value = res.data
    }
  } catch (e) {
    weatherError.value = '网络请求失败'
    weather.value = null
  } finally {
    weatherLoading.value = false
  }
}

// --- 城市搜索 ---
function onSearchInput() {
  clearTimeout(searchTimer)
  const kw = searchKeyword.value.trim()
  if (!kw) {
    cityList.value = []
    showDropdown.value = false
    return
  }
  searching.value = true
  searchTimer = setTimeout(async () => {
    try {
      const res = await api.get('/api/weather/cities', { params: { keywords: kw } })
      cityList.value = res.data.cities || []
      showDropdown.value = cityList.value.length > 0
    } catch {
      cityList.value = []
    } finally {
      searching.value = false
    }
  }, 350)
}

function selectCity(city) {
  showDropdown.value = false
  searchKeyword.value = city.name
  location.gcjLng = city.lng
  location.gcjLat = city.lat
  location.name = city.name

  const wgs = gcj02ToWgs84(city.lng, city.lat)
  location.wgsLng = Math.round(wgs.lng * 10000) / 10000
  location.wgsLat = Math.round(wgs.lat * 10000) / 10000

  if (mapInstance && markerInstance) {
    mapInstance.setCenter([city.lng, city.lat])
    markerInstance.setPosition([city.lng, city.lat])
  }

  fetchWeather()
}

function handleManualCoord() {
  const gcj = wgs84ToGcj02(location.wgsLng, location.wgsLat)
  location.gcjLng = Math.round(gcj.lng * 10000) / 10000
  location.gcjLat = Math.round(gcj.lat * 10000) / 10000

  if (mapInstance && markerInstance) {
    mapInstance.setCenter([location.gcjLng, location.gcjLat])
    markerInstance.setPosition([location.gcjLng, location.gcjLat])
  }

  if (geocoderInstance) {
    geocoderInstance.getAddress([location.gcjLng, location.gcjLat], (status, result) => {
      if (status === 'complete' && result.regeocode) {
        location.name = result.regeocode.formattedAddress || '未知位置'
      }
    })
  }

  fetchWeather()
}

// --- 风向文字 ---
function windDirText(deg) {
  if (deg == null) return '--'
  const dirs = ['北', '东北', '东', '东南', '南', '西南', '西', '西北']
  return dirs[Math.round(deg / 45) % 8] + '风'
}

// --- AQI 等级样式 ---
const aqiClass = computed(() => {
  const aqi = weather.value?.aqi
  if (aqi == null) return ''
  if (aqi <= 50) return 'aqi-good'
  if (aqi <= 100) return 'aqi-moderate'
  if (aqi <= 150) return 'aqi-unhealthy-sg'
  if (aqi <= 200) return 'aqi-unhealthy'
  return 'aqi-hazardous'
})

// --- 室外 vs 棚内对比 ---
const comparisonItems = computed(() => {
  const indoor = sensorStore.current
  const hasIndoor = indoor.temp || indoor.humi || indoor.light || indoor.soil
  const w = weather.value
  return [
    {
      label: '温度',
      unit: '°C',
      outdoor: w ? w.temperature : null,
      indoor: hasIndoor ? indoor.temp : null,
    },
    {
      label: '湿度',
      unit: '%',
      outdoor: w ? w.humidity : null,
      indoor: hasIndoor ? indoor.humi : null,
    },
    {
      label: '辐射/光照',
      unit: w ? 'W/m²' : '',
      outdoor: w ? w.radiation : null,
      indoor: hasIndoor ? indoor.light : null,
      indoorUnit: 'lux',
    },
    {
      label: '土壤含水量',
      unit: '%',
      outdoor: w ? (w.soil_moisture != null ? (w.soil_moisture * 100).toFixed(1) : null) : null,
      indoor: hasIndoor ? indoor.soil : null,
    },
  ]
})

function fmtNum(v) {
  if (v == null) return '--'
  return typeof v === 'number' ? Number(v).toFixed(1) : v
}

// --- 生命周期 ---
onMounted(async () => {
  try {
    const AMap = await loadAMapScript()
    mapLoaded.value = true
    initMap(AMap)
  } catch (e) {
    mapError.value = e.message || '地图加载失败'
  }
  fetchWeather()
})

onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  clearTimeout(weatherTimer)
  if (mapInstance) {
    mapInstance.destroy()
    mapInstance = null
  }
})
</script>

<template>
  <div class="weather-page">
    <header class="topbar">
      <div>
        <h1 class="page-title">环境气象</h1>
        <p class="page-subtitle">室外气象数据查询 - Open-Meteo / 高德地图</p>
      </div>
    </header>

    <div class="weather-layout">
      <!-- 左侧: 配置面板 -->
      <aside class="config-panel card">
        <h2 class="section-title">位置选点</h2>

        <div class="form-group">
          <label>城市搜索</label>
          <div class="search-wrapper">
            <input
              v-model="searchKeyword"
              class="field search-input"
              type="text"
              placeholder="输入城市/区县名称..."
              @input="onSearchInput"
              @focus="showDropdown = cityList.length > 0"
            />
            <div v-if="showDropdown" class="search-dropdown">
              <div
                v-for="city in cityList"
                :key="city.adcode"
                class="dropdown-item"
                @click="selectCity(city)"
              >
                {{ city.name }}
              </div>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>当前位置</label>
          <div class="location-name">{{ location.name }}</div>
        </div>

        <div class="form-group">
          <label>WGS84 坐标</label>
          <div class="coord-row">
            <div class="coord-field">
              <small>纬度</small>
              <input v-model.number="location.wgsLat" class="field" type="number" step="0.0001" />
            </div>
            <div class="coord-field">
              <small>经度</small>
              <input v-model.number="location.wgsLng" class="field" type="number" step="0.0001" />
            </div>
          </div>
          <button class="btn btn-soft coord-btn" type="button" @click="handleManualCoord">
            定位此坐标
          </button>
        </div>

        <div class="form-group">
          <label>GCJ02 坐标 (地图)</label>
          <div class="coord-display">
            <span>{{ location.gcjLat }}, {{ location.gcjLng }}</span>
          </div>
        </div>
      </aside>

      <!-- 右侧: 地图 -->
      <div class="map-area card">
        <div ref="mapContainer" class="map-container">
          <div v-if="mapError" class="map-fallback">
            <div class="fallback-icon">
              <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="24" cy="20" r="6" />
                <path d="M24 4C15 4 8 11 8 20c0 12 16 24 16 24s16-12 16-24c0-9-7-16-16-16z" />
              </svg>
            </div>
            <p class="fallback-title">地图加载失败</p>
            <p class="fallback-desc">{{ mapError }}</p>
            <p class="fallback-hint">可通过左侧手动输入坐标查询天气数据</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 天气数据 -->
    <div v-if="weatherLoading" class="weather-loading">
      <span class="loading-dot"></span> 正在获取天气数据...
    </div>

    <div v-if="weatherError" class="weather-error card">
      {{ weatherError }}
    </div>

    <div v-if="weather" class="weather-cards">
      <!-- 天气概况卡 -->
      <div class="card weather-main-card">
        <div class="weather-main-header">
          <div class="weather-temp">
            <span class="temp-value">{{ fmtNum(weather.temperature) }}</span>
            <span class="temp-unit">&deg;C</span>
          </div>
          <div class="weather-desc">
            <strong>{{ weather.weather_text }}</strong>
            <small>体感 {{ fmtNum(weather.apparent_temperature) }}&deg;C</small>
          </div>
        </div>
        <div class="weather-detail-grid">
          <div class="detail-item">
            <span class="detail-label">湿度</span>
            <span class="detail-value">{{ weather.humidity ?? '--' }}<small>%</small></span>
          </div>
          <div class="detail-item">
            <span class="detail-label">降水</span>
            <span class="detail-value">{{ fmtNum(weather.precipitation) }}<small>mm</small></span>
          </div>
          <div class="detail-item">
            <span class="detail-label">风速</span>
            <span class="detail-value">{{ fmtNum(weather.wind_speed) }}<small>km/h</small></span>
          </div>
          <div class="detail-item">
            <span class="detail-label">风向</span>
            <span class="detail-value text-only">{{ windDirText(weather.wind_direction) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">太阳辐射</span>
            <span class="detail-value">{{ fmtNum(weather.radiation) }}<small>W/m&sup2;</small></span>
          </div>
          <div class="detail-item">
            <span class="detail-label">土壤含水量</span>
            <span class="detail-value">{{ weather.soil_moisture != null ? (weather.soil_moisture * 100).toFixed(1) : '--' }}<small>%</small></span>
          </div>
        </div>
        <div class="weather-time">
          数据时间: {{ weather.time || '--' }}
        </div>
      </div>

      <!-- AQI 卡 -->
      <div class="card aqi-card">
        <h3 class="section-title">空气质量</h3>
        <div class="aqi-main">
          <div class="aqi-number" :class="aqiClass">{{ weather.aqi ?? '--' }}</div>
          <div class="aqi-level">
            <span class="aqi-badge" :class="aqiClass">{{ weather.aqi_level }}</span>
          </div>
        </div>
        <div class="aqi-details">
          <div><span>PM2.5</span><strong>{{ weather.pm2_5 ?? '--' }}</strong></div>
          <div><span>PM10</span><strong>{{ weather.pm10 ?? '--' }}</strong></div>
        </div>
      </div>

      <!-- 室外 vs 棚内对比 -->
      <div class="card compare-card">
        <h3 class="section-title">室外气象 vs 棚内实测</h3>
        <div class="compare-table">
          <div class="compare-header">
            <span>参数</span>
            <span>室外</span>
            <span>棚内</span>
          </div>
          <div v-for="item in comparisonItems" :key="item.label" class="compare-row">
            <span class="compare-label">{{ item.label }}</span>
            <span class="compare-val num">{{ fmtNum(item.outdoor) }}<small v-if="item.outdoor != null"> {{ item.unit }}</small></span>
            <span class="compare-val num">{{ fmtNum(item.indoor) }}<small v-if="item.indoor != null"> {{ item.indoorUnit || item.unit }}</small></span>
          </div>
        </div>
        <p class="compare-hint">棚内数据来自传感器实时采集; 无连接时显示 --</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.weather-page {
  max-width: 1320px;
  margin: 0 auto;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

/* --- 上半: 配置 + 地图 --- */
.weather-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.config-panel {
  padding: 20px 18px;
}

.config-panel h2 {
  margin-bottom: 18px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.search-wrapper {
  position: relative;
}

.search-input {
  width: 100%;
}

.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 100;
  max-height: 240px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid var(--border);
  border-top: 0;
  border-radius: 0 0 var(--radius-control) var(--radius-control);
  box-shadow: 0 6px 16px rgba(19, 43, 28, 0.1);
}

.dropdown-item {
  padding: 9px 12px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-primary);
}

.dropdown-item:hover {
  background: var(--green-soft);
  color: var(--green-deep);
}

.location-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  padding: 6px 0;
  word-break: break-all;
}

.coord-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.coord-field small {
  display: block;
  margin-bottom: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.coord-field .field {
  width: 100%;
}

.coord-btn {
  width: 100%;
  margin-top: 8px;
}

.coord-display {
  padding: 8px 12px;
  background: var(--bg-soft);
  border-radius: var(--radius-control);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 13px;
}

/* --- 地图 --- */
.map-area {
  min-height: 420px;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
  min-height: 420px;
}

.map-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 420px;
  padding: 40px 20px;
  text-align: center;
  color: var(--text-secondary);
}

.fallback-icon svg {
  width: 48px;
  height: 48px;
  color: var(--muted);
}

.fallback-title {
  margin-top: 12px;
  font-weight: 700;
  font-size: 16px;
  color: var(--text-primary);
}

.fallback-desc {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-muted);
  max-width: 360px;
}

.fallback-hint {
  margin-top: 16px;
  font-size: 13px;
  padding: 8px 16px;
  background: var(--green-soft);
  border-radius: var(--radius-control);
  color: var(--green-deep);
}

/* --- 天气加载/错误 --- */
.weather-loading {
  padding: 16px 0;
  color: var(--text-secondary);
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--green);
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.weather-error {
  padding: 14px 18px;
  margin-bottom: 16px;
  color: var(--red);
  font-size: 14px;
  border-left: 3px solid var(--red);
}

/* --- 天气卡片区 --- */
.weather-cards {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px minmax(0, 1fr);
  gap: 12px;
}

/* 天气概况 */
.weather-main-card {
  padding: 22px 20px;
}

.weather-main-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}

.weather-temp {
  display: flex;
  align-items: flex-start;
}

.temp-value {
  font-size: 48px;
  font-weight: 780;
  line-height: 1;
  color: var(--text-primary);
}

.temp-unit {
  font-size: 20px;
  font-weight: 650;
  color: var(--text-secondary);
  margin-top: 4px;
}

.weather-desc {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 8px;
}

.weather-desc strong {
  font-size: 18px;
  color: var(--text-primary);
}

.weather-desc small {
  color: var(--text-muted);
  font-size: 13px;
}

.weather-detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 0;
  border-top: 1px solid var(--border-light);
}

.detail-label {
  color: var(--text-muted);
  font-size: 12px;
}

.detail-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.detail-value small {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-left: 2px;
}

.detail-value.text-only {
  font-family: var(--font-body);
  font-size: 16px;
}

.weather-time {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid var(--border-light);
  color: var(--text-muted);
  font-size: 12px;
  font-family: var(--font-mono);
}

/* AQI 卡 */
.aqi-card {
  padding: 22px 20px;
  display: flex;
  flex-direction: column;
}

.aqi-card h3 {
  margin-bottom: 14px;
}

.aqi-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 12px 0 18px;
}

.aqi-number {
  font-size: 52px;
  font-weight: 780;
  line-height: 1;
  font-family: var(--font-mono);
  color: var(--green);
}

.aqi-badge {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 650;
}

.aqi-good .aqi-number,
.aqi-good { color: var(--green); }
.aqi-good.aqi-badge { background: var(--green-soft); color: var(--green-deep); }

.aqi-moderate .aqi-number,
.aqi-moderate { color: #d4a017; }
.aqi-moderate.aqi-badge { background: #fef9e7; color: #b8860b; }

.aqi-unhealthy-sg .aqi-number,
.aqi-unhealthy-sg { color: var(--orange); }
.aqi-unhealthy-sg.aqi-badge { background: var(--orange-soft); color: #d46e00; }

.aqi-unhealthy .aqi-number,
.aqi-unhealthy { color: var(--red); }
.aqi-unhealthy.aqi-badge { background: var(--red-soft); color: var(--red); }

.aqi-hazardous .aqi-number,
.aqi-hazardous { color: #7b241c; }
.aqi-hazardous.aqi-badge { background: #f9ebea; color: #7b241c; }

.aqi-details {
  display: grid;
  gap: 10px;
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid var(--border-light);
}

.aqi-details > div {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.aqi-details span {
  color: var(--text-secondary);
}

.aqi-details strong {
  font-family: var(--font-mono);
}

/* 对比卡 */
.compare-card {
  padding: 22px 20px;
}

.compare-card h3 {
  margin-bottom: 14px;
}

.compare-table {
  display: grid;
  gap: 0;
}

.compare-header,
.compare-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  padding: 9px 0;
}

.compare-header {
  border-bottom: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
}

.compare-row {
  border-bottom: 1px solid var(--border-light);
}

.compare-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.compare-val {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.compare-val small {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  margin-left: 2px;
}

.compare-hint {
  margin-top: 12px;
  color: var(--text-muted);
  font-size: 12px;
}

/* --- 响应式 --- */
@media (max-width: 1100px) {
  .weather-layout {
    grid-template-columns: 1fr;
  }

  .weather-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .compare-card {
    grid-column: 1 / -1;
  }
}

@media (max-width: 860px) {
  .weather-layout {
    grid-template-columns: 1fr;
  }

  .weather-cards {
    grid-template-columns: 1fr;
  }

  .compare-card {
    grid-column: auto;
  }

  .weather-detail-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
