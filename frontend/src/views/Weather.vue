<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useSensorStore } from '../stores/sensor'
import api from '../utils/api'
import { sourceMeta } from '../utils/sources'

const sensorStore = useSensorStore()

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
let searchTimer = null

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
  } catch {
    weatherError.value = '网络请求失败'
    weather.value = null
  } finally {
    weatherLoading.value = false
  }
}

function onSearchInput() {
  clearTimeout(searchTimer)
  const keyword = searchKeyword.value.trim()
  if (!keyword) {
    cityList.value = []
    showDropdown.value = false
    return
  }
  searching.value = true
  searchTimer = setTimeout(async () => {
    try {
      const res = await api.get('/api/weather/cities', { params: { keywords: keyword } })
      cityList.value = res.data.cities || []
      showDropdown.value = cityList.value.length > 0
    } catch {
      cityList.value = []
    } finally {
      searching.value = false
    }
  }, 320)
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
  fetchWeather()
}

function handleManualCoord() {
  location.name = `${location.wgsLat}, ${location.wgsLng}`
  fetchWeather()
}

function fmt(v, digits = 1) {
  if (v == null || Number.isNaN(Number(v))) return '—'
  return Number(v).toFixed(digits)
}

const weatherCards = computed(() => [
  { label: '室外温度', value: fmt(weather.value?.temperature), unit: '°C', icon: 'temp' },
  { label: '室外湿度', value: fmt(weather.value?.humidity, 0), unit: '%', icon: 'humi' },
  { label: '降水', value: fmt(weather.value?.precipitation), unit: 'mm', icon: 'rain' },
  { label: '风速', value: fmt(weather.value?.wind_speed), unit: 'km/h', icon: 'wind' },
  { label: '室外辐射', value: fmt(weather.value?.radiation), unit: 'W/m²', icon: 'sun' },
  { label: 'AQI', value: weather.value?.aqi ?? '—', unit: weather.value?.aqi_level || '', icon: 'leaf' },
])

const comparisonRows = computed(() => {
  const indoor = sensorStore.current
  const hasIndoor = indoor.temp != null || indoor.humi != null || indoor.light != null || indoor.soil != null
  return [
    { label: '温度', outdoor: `${fmt(weather.value?.temperature)} °C`, indoor: hasIndoor && indoor.temp != null ? `${fmt(indoor.temp)} °C` : '—', diff: diffText(indoor.temp, weather.value?.temperature, '°C'), indoorSource: sensorStore.fieldFor('temp').source },
    { label: '湿度', outdoor: `${fmt(weather.value?.humidity, 0)} %`, indoor: hasIndoor && indoor.humi != null ? `${fmt(indoor.humi, 0)} %` : '—', diff: diffText(indoor.humi, weather.value?.humidity, '%'), indoorSource: sensorStore.fieldFor('humi').source },
    { label: '风速', outdoor: `${fmt(weather.value?.wind_speed)} km/h`, indoor: '—', diff: '仅记录室外风况', indoorSource: 'pending' },
    { label: '辐射/相对光照', outdoor: `${fmt(weather.value?.radiation)} W/m²`, indoor: hasIndoor && indoor.light != null ? `${fmt(indoor.light, 0)} 相对值` : '—', diff: '棚内为GL5516 ADC相对值', indoorSource: sensorStore.fieldFor('light').source },
    { label: '土壤含水量', outdoor: weather.value?.soil_moisture != null ? `${fmt(weather.value.soil_moisture * 100)} %` : '—', indoor: hasIndoor && indoor.soil != null ? `${fmt(indoor.soil)} %` : '—', diff: '棚内以传感器为准', indoorSource: sensorStore.fieldFor('soil').source },
  ]
})

function diffText(indoor, outdoor, unit) {
  if (indoor == null || outdoor == null) return '—'
  const diff = Number(indoor) - Number(outdoor)
  return `${diff >= 0 ? '+' : ''}${diff.toFixed(1)} ${unit}`
}

function sourceFor(source) {
  return sourceMeta(source)
}

async function fetchSensorFields() {
  try {
    const res = await api.get('/api/sensor-fields')
    sensorStore.setFieldCatalog(res.data)
  } catch { /* keep fallback catalog */ }
}

onMounted(() => {
  fetchSensorFields()
  fetchWeather()
})
</script>

<template>
  <div class="weather-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">环境气象</h1>
        <p class="page-subtitle">查看室外天气，并与棚内传感器数据对比</p>
      </div>
      <button class="btn btn-soft" type="button" @click="fetchWeather">{{ weatherLoading ? '获取中' : '刷新气象' }}</button>
    </header>

    <section class="card location-panel">
      <div class="search-box">
        <label>位置选点</label>
        <div class="search-wrapper">
          <input
            v-model="searchKeyword"
            class="field"
            type="text"
            placeholder="输入城市/区县名称"
            @input="onSearchInput"
            @focus="showDropdown = cityList.length > 0"
          />
          <div v-if="showDropdown" class="search-dropdown">
            <button v-for="city in cityList" :key="city.adcode" type="button" @click="selectCity(city)">
              {{ city.name }}
            </button>
          </div>
        </div>
      </div>
      <div class="coord-box">
        <label>纬度</label>
        <input v-model.number="location.wgsLat" class="field" type="number" step="0.0001" />
      </div>
      <div class="coord-box">
        <label>经度</label>
        <input v-model.number="location.wgsLng" class="field" type="number" step="0.0001" />
      </div>
      <button class="btn btn-primary" type="button" @click="handleManualCoord">定位此坐标</button>
      <span class="location-name">{{ searching ? '搜索中...' : location.name }}</span>
    </section>

    <p v-if="weatherError" class="weather-error card">{{ weatherError }}</p>

    <section class="weather-card-grid">
      <article v-for="item in weatherCards" :key="item.label" class="card weather-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}<small>{{ item.unit }}</small></strong>
        <b class="source-badge source-api">室外参考</b>
      </article>
    </section>

    <section class="card compare-panel">
      <div class="panel-head">
        <h2 class="section-title">棚内 / 室外对比</h2>
        <span>更新时间：{{ weather?.time || '—' }}</span>
      </div>
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>指标</th>
              <th>室外</th>
              <th>棚内</th>
              <th>差值/说明</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in comparisonRows" :key="row.label">
              <td>{{ row.label }}</td>
              <td>{{ row.outdoor }} <b class="source-badge source-api">参考</b></td>
              <td>{{ row.indoor }} <b class="source-badge" :class="sourceFor(row.indoorSource).className">{{ sourceFor(row.indoorSource).label }}</b></td>
              <td>{{ row.diff }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.weather-page {
  max-width: 1600px;
  margin: 0 auto;
}

.page-head,
.location-panel,
.panel-head {
  display: flex;
  align-items: center;
}

.page-head {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.location-panel {
  gap: 14px;
  padding: 14px;
  margin-bottom: 14px;
}

.search-box,
.coord-box {
  display: grid;
  gap: 6px;
}

.search-box {
  min-width: 320px;
}

.search-box label,
.coord-box label {
  color: #475569;
  font-size: 12px;
  font-weight: 750;
}

.search-wrapper {
  position: relative;
}

.search-wrapper .field {
  width: 100%;
}

.search-dropdown {
  position: absolute;
  z-index: 10;
  top: 100%;
  left: 0;
  right: 0;
  display: grid;
  max-height: 240px;
  overflow-y: auto;
  border: 1px solid var(--border-light);
  border-radius: 0 0 7px 7px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, .08);
}

.search-dropdown button {
  height: 38px;
  border: 0;
  border-bottom: 1px solid var(--border-light);
  background: #fff;
  text-align: left;
  padding: 0 12px;
}

.location-name {
  margin-left: auto;
  color: #0f172a;
  font-weight: 750;
}

.weather-error {
  margin-bottom: 14px;
  padding: 12px 14px;
  color: var(--red);
}

.weather-card-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}

.weather-card {
  min-height: 118px;
  display: grid;
  gap: 8px;
  padding: 16px;
}

.weather-card span {
  color: #475569;
  font-weight: 750;
}

.weather-card strong {
  color: #2563eb;
  font-size: 30px;
  line-height: 1;
}

.weather-card small {
  margin-left: 5px;
  color: #334155;
  font-size: 13px;
}

.panel-head {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-head span {
  color: #64748b;
  font-size: 13px;
}

.compare-panel {
  padding: 18px;
}

.data-table .source-badge {
  margin-left: 6px;
}

@media (max-width: 1180px) {
  .weather-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .location-panel {
    align-items: stretch;
    flex-wrap: wrap;
  }
}

@media (max-width: 760px) {
  .page-head,
  .location-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .search-box,
  .coord-box {
    min-width: 0;
    width: 100%;
  }

  .location-name {
    margin-left: 0;
  }

  .weather-card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
