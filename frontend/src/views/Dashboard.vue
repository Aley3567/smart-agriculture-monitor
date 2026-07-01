<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GraphicComponent, GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useSensorStore } from '../stores/sensor'
import { useSystemStore } from '../stores/system'
import api from '../utils/api'
import { ACTION_LABEL, DEFAULT_BOARD_ID, PARAM_LABEL, PARAM_UNIT } from '../utils/constants'
import { formatTimeOnly } from '../utils/format'
import {
  DEVICE_META,
  formatFieldValue,
  sourceMeta,
} from '../utils/sources'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, GraphicComponent, CanvasRenderer])

const router = useRouter()
const sensorStore = useSensorStore()
const systemStore = useSystemStore()

const thresholds = ref({})
const recentAlarms = ref([])
const weather = ref(null)
const autoRule = ref(null)
const recentAction = ref(null)

const cardTones = {
  temp: 'warm',
  humi: 'sky',
  light: 'sun',
  soil: 'earth',
  co2: 'mint',
  soil_ec: 'violet',
  soil_tds: 'cyan',
  soil_fertility: 'leaf',
  infrared: 'rose',
}

const hasData = computed(() => sensorStore.history.timestamps.length > 0)
const currentBoardId = computed(() => systemStore.currentBoardId || DEFAULT_BOARD_ID)
const isTestSample = computed(() => Boolean(sensorStore.currentMeta.is_test))
const bridgeModeMeta = computed(() => {
  if (sensorStore.currentMeta.bridge_mode === 'mock') return sourceMeta('bridge_mock')
  if (sensorStore.currentMeta.bridge_mode === 'hardware') return sourceMeta('bridge_hardware')
  if (sensorStore.currentMeta.timestamp) return sourceMeta('bridge_unknown')
  return null
})

const measuredCards = computed(() => sensorStore.measuredFieldKeys.map((key) => {
  const field = sensorStore.fieldFor(key)
  const value = sensorStore.current[key]
  const threshold = thresholds.value[field.param]
  const numeric = Number(value)
  const breach = threshold && value != null && (numeric < threshold.min_value || numeric > threshold.max_value)
  return {
    ...field,
    value: formatFieldValue(field, value),
    breach,
    threshold,
    source: sourceMeta(field.source),
    available: field.available !== false,
    tone: cardTones[key] || 'leaf',
  }
}))

const modelCards = computed(() => sensorStore.modelFieldKeys.map((key) => {
  const field = sensorStore.fieldFor(key)
  const value = field.available ? sensorStore.current[key] : null
  const threshold = thresholds.value[field.param]
  const numeric = Number(value)
  const breach = threshold && value != null && (numeric < threshold.min_value || numeric > threshold.max_value)
  return {
    ...field,
    value: field.available ? formatFieldValue(field, value) : '—',
    breach,
    threshold,
    source: field.available ? sourceMeta(field.source) : sourceMeta('pending'),
    available: field.available,
    muted: !field.available,
    tone: cardTones[key] || 'leaf',
  }
}))

const actuatorCards = computed(() => Object.values(DEVICE_META).map((item) => ({
  ...item,
  active: Boolean(systemStore.actuators[item.key]),
})))

const debugEvents = computed(() => systemStore.debugEvents
  .filter(item => !item.board_id || item.board_id === currentBoardId.value)
  .slice(0, 6))

const autoWateringState = computed(() => {
  const state = systemStore.autoWatering[currentBoardId.value] || {}
  if (state.active) {
    return {
      tone: 'green',
      label: '浇水中',
      detail: state.started_at ? `开始于 ${formatTimeOnly(state.started_at)}` : '普通浇水泵运行中',
    }
  }
  if (state.cooldown_until && new Date(state.cooldown_until) > new Date()) {
    return {
      tone: 'orange',
      label: '冷却中',
      detail: `冷却至 ${formatTimeOnly(state.cooldown_until)}`,
    }
  }
  return {
    tone: 'gray',
    label: '待机',
    detail: '未触发自动浇水',
  }
})

const autoRuleSummary = computed(() => {
  const rule = autoRule.value
  if (!rule) return '规则未读取'
  if (!rule.enabled) return '规则已停用'
  return `低于 ${rule.start_below}% 连续 ${rule.consecutive_samples} 次启动，达到 ${rule.stop_at_or_above}% 停止`
})

const measuredChartOption = computed(() => {
  const h = sensorStore.history
  const labels = h.timestamps.map(formatTimeOnly)
  return makeLineOption({
    labels,
    legend: ['温度(°C)', '空气湿度(%)', '相对光照'],
    colors: ['#ef4444', '#2563eb', '#f97316'],
    series: [
      { name: '温度(°C)', data: h.temp, yAxisIndex: 0 },
      { name: '空气湿度(%)', data: h.humi, yAxisIndex: 0 },
      { name: '相对光照', data: h.light, yAxisIndex: 1 },
    ],
  })
})

const modelChartOption = computed(() => {
  const h = sensorStore.history
  const labels = h.timestamps.map(formatTimeOnly)
  const seriesData = (key) => Array.isArray(h[key]) ? h[key] : h.timestamps.map(() => null)
  return makeLineOption({
    labels,
    legend: ['土壤湿度(%)'],
    colors: ['#16a34a'],
    series: [
      { name: '土壤湿度(%)', data: seriesData('soil'), yAxisIndex: 0 },
    ],
    yAxis: [{ min: 0, max: 100 }],
  })
})

const eventChartOption = computed(() => {
  const h = sensorStore.history
  const seriesData = (key) => Array.isArray(h[key]) ? h[key] : h.timestamps.map(() => null)
  return makeLineOption({
    labels: h.timestamps.map(formatTimeOnly),
    legend: ['红外状态', 'CO2(ppm)'],
    colors: ['#dc2626', '#059669'],
    series: [
      { name: '红外状态', data: seriesData('infrared'), yAxisIndex: 0 },
      { name: 'CO2(ppm)', data: seriesData('co2'), yAxisIndex: 1 },
    ],
  })
})

const weatherCards = computed(() => [
  { label: '室外温度', value: weather.value?.temperature, unit: '°C' },
  { label: '降水', value: weather.value?.precipitation, unit: 'mm' },
  { label: '风速', value: weather.value?.wind_speed, unit: 'km/h' },
  { label: '室外辐射', value: weather.value?.radiation, unit: 'W/m²' },
])

function makeLineOption({ labels, legend, colors, series, yAxis = [] }) {
  const top = legend.length > 3 ? 72 : 52
  const hasRightAxis = series.some(item => item.yAxisIndex === 1)
  return {
    animation: false,
    color: colors,
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#0f172a', fontSize: 12 },
    },
    legend: {
      top: 2,
      left: 0,
      itemWidth: 16,
      itemHeight: 3,
      itemGap: 18,
      textStyle: { color: '#334155', fontSize: 12 },
      data: legend,
    },
    grid: { top, left: 44, right: 48, bottom: 34 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#dbe3ef' } },
      axisLabel: { color: '#64748b', fontSize: 11, hideOverlap: true },
    },
    yAxis: [
      { type: 'value', scale: true, ...yAxis[0], axisLabel: { color: '#64748b', fontSize: 11 }, splitLine: { lineStyle: { color: '#edf2f7', type: 'dashed' } } },
      { type: 'value', show: hasRightAxis, scale: true, position: 'right', ...yAxis[1], axisLabel: { color: '#64748b', fontSize: 11 }, splitLine: { show: false } },
    ],
    series: series.map((item) => ({
      ...item,
      type: 'line',
      smooth: true,
      symbol: 'none',
      connectNulls: false,
      lineStyle: { width: 2 },
    })),
  }
}

function paramLabel(name) {
  return PARAM_LABEL[name] || name
}

function unitOf(name) {
  if (name === 'light') return '相对值'
  return PARAM_UNIT[name] || ''
}

function sourceForParam(param) {
  const field = sensorStore.fieldForParam(param)
  if (field) return sourceMeta(field.source)
  return sourceMeta('system')
}

function fmtWeather(v) {
  if (v == null) return '—'
  return Number(v).toFixed(1)
}

function actionText(log) {
  if (!log) return '暂无动作'
  return ACTION_LABEL[`${log.device}_${log.action}`] || `${DEVICE_META[log.device]?.label || log.device} ${log.action}`
}

function actionSourceText(log) {
  if (!log) return ''
  if (log.source === 'auto') return '自动'
  if (log.source === 'manual') return '手动'
  return log.source || '—'
}

function debugTitle(event) {
  const labels = {
    bridge_connected: 'bridge 已连接云端',
    serial_raw_line: '收到串口原始行',
    serial_parse_failed: '串口解析失败',
    sensor_parsed: '传感器数据解析成功',
    control_received: '收到云端控制命令',
    control_written_serial: '控制命令已写入串口',
    ws_message_invalid: '云端消息格式异常',
  }
  return labels[event?.event] || event?.event || '调试事件'
}

function debugDetail(event) {
  const details = event?.details || {}
  if (details.raw_line) return details.raw_line
  if (details.command) return details.command
  if (details.data) return JSON.stringify(details.data)
  if (details.error) return details.error
  return `board=${event?.board_id || currentBoardId.value}`
}

async function fetchDebugEvents() {
  try {
    const res = await api.get('/api/debug-events', {
      params: { board_id: currentBoardId.value, limit: 20 },
    })
    systemStore.setDebugEvents(res.data?.items || [])
  } catch { /* debug panel is best-effort */ }
}

async function fetchStatus() {
  try {
    const res = await api.get('/api/status')
    systemStore.updateStatus(res.data)
  } catch { /* status remains websocket-derived when API is unavailable */ }
}

async function fetchAutoRule() {
  try {
    const res = await api.get('/api/control-rules/soil-moisture-pump')
    autoRule.value = res.data
  } catch {
    autoRule.value = null
  }
}

async function fetchRecentAction() {
  try {
    const res = await api.get('/api/control-log', {
      params: { board_id: currentBoardId.value, page: 1, page_size: 1 },
    })
    recentAction.value = Array.isArray(res.data?.items) ? res.data.items[0] || null : null
  } catch {
    recentAction.value = null
  }
}

async function fetchThresholds() {
  try {
    const res = await api.get('/api/thresholds')
    thresholds.value = Object.fromEntries(
      res.data.map(t => [t.param_name, { min_value: t.min_value, max_value: t.max_value }]),
    )
  } catch { /* keep last values */ }
}

async function fetchRecentAlarms() {
  const end = new Date()
  const start = new Date(end.getTime() - 7 * 24 * 3600 * 1000)
  try {
    const res = await api.get('/api/alarms', {
      params: { start: start.toISOString(), end: end.toISOString(), page: 1, page_size: 4 },
    })
    recentAlarms.value = res.data.items
  } catch {
    recentAlarms.value = []
  }
}

async function fetchWeather() {
  try {
    const res = await api.get('/api/weather')
    weather.value = res.data?.error ? null : res.data
  } catch {
    weather.value = null
  }
}

async function fetchRecentSamples() {
  const end = new Date()
  const start = new Date(end.getTime() - 24 * 3600 * 1000)
  try {
    const res = await api.get('/api/history', {
      params: { board_id: currentBoardId.value, start: start.toISOString(), end: end.toISOString(), page: 1, page_size: 60 },
    })
    sensorStore.hydrateSamples([...res.data.items].reverse(), res.data.fields)
  } catch { /* websocket remains the primary realtime path */ }
}

async function toggleActuator(device) {
  const next = systemStore.actuators[device] ? 'off' : 'on'
  try {
    await api.post('/api/control', { board_id: currentBoardId.value, device, action: next })
    systemStore.setActuator(device, next === 'on')
    fetchRecentAction()
  } catch { /* control failure is surfaced by unchanged status */ }
}

async function resetActuatorEffects() {
  try {
    await api.post('/api/reset-actuator-effects')
  } catch { /* ignore */ }
}

function refresh() {
  fetchStatus()
  fetchRecentSamples()
  fetchThresholds()
  fetchRecentAlarms()
  fetchWeather()
  fetchAutoRule()
  fetchRecentAction()
  fetchDebugEvents()
}

onMounted(refresh)
</script>

<template>
  <div class="monitor-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">实时监测</h1>
        <p class="page-subtitle">
          当前板卡 {{ currentBoardId }}
          <b v-if="bridgeModeMeta" class="source-badge" :class="bridgeModeMeta.className">{{ bridgeModeMeta.label }}</b>
          <b v-if="isTestSample" class="source-badge source-test test-tag">测试数据</b>
        </p>
      </div>
      <button class="btn btn-soft" type="button" @click="refresh">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M16.2 10a6.2 6.2 0 1 1-1.8-4.4"/><path d="M16.2 4v4h-4"/></svg>
        刷新
      </button>
    </header>

    <div class="dashboard-layout">
      <main class="dashboard-main">
        <section class="panel-block">
          <div class="block-title"><i></i><h2>板端实测</h2></div>
          <div class="measured-grid">
            <article v-for="card in measuredCards" :key="card.key" class="metric-card card" :class="[`tone-${card.tone}`, { breach: card.breach }]">
              <div class="metric-icon">
                <svg v-if="card.key === 'temp'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M9 13.5V5a3 3 0 0 1 6 0v8.5a5 5 0 1 1-6 0z"/><path d="M12 8v8"/></svg>
                <svg v-else-if="card.key === 'humi'" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.8c4.6 5.2 7 9.1 7 12A7 7 0 0 1 5 14.8c0-2.9 2.4-6.8 7-12z"/></svg>
                <svg v-else-if="card.key === 'light'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M18.7 5.3l-2.1 2.1M7.4 16.6l-2.1 2.1"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20v-8"/><path d="M12 12c-3.1 0-5.5-1.6-6.5-4.6 3.4-.5 5.7.4 6.5 2.8"/><path d="M12 12c3.1 0 5.5-1.6 6.5-4.6-3.4-.5-5.7.4-6.5 2.8"/><path d="M7 20h10"/></svg>
              </div>
              <div class="metric-body">
                <div class="metric-title">
                  <span>{{ card.label }}</span>
                  <span class="badge-pair">
                    <b class="source-badge" :class="card.source.className">{{ card.source.label }}</b>
                    <b v-if="!card.available" class="source-badge availability pending">待接入</b>
                  </span>
                </div>
                <div class="metric-value"><strong>{{ card.value }}</strong><small>{{ card.unit }}</small></div>
              </div>
            </article>
          </div>
        </section>

        <section class="panel-block card model-panel">
          <div class="block-title"><i></i><h2>模型推算</h2></div>
          <div class="model-grid">
            <article v-for="card in modelCards" :key="card.key" class="model-card" :class="[`tone-${card.tone}`, { muted: card.muted }]">
              <span class="model-icon">
                <svg v-if="card.key === 'co2'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M7.2 15.5a4.2 4.2 0 1 1 1.2-8.2 5.4 5.4 0 0 1 10.2 2.6A3.2 3.2 0 1 1 18 16H7.2z"/>
                  <path d="M8 19h8"/>
                  <path d="M10 12.6h4"/>
                </svg>
                <svg v-else-if="card.key === 'soil_ec'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M7 4v7.6a5 5 0 0 0 10 0V4"/>
                  <path d="M9.5 4v6.8a2.5 2.5 0 0 0 5 0V4"/>
                  <path d="M12 17v3"/>
                  <path d="M9 20h6"/>
                  <path d="M8 8h2M14 8h2"/>
                </svg>
                <svg v-else-if="card.key === 'soil_tds'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M6 7.5c3.7-2 8.3-2 12 0"/>
                  <path d="M7 16.5c3.1 1.6 6.9 1.6 10 0"/>
                  <circle cx="9" cy="12" r="1.2"/>
                  <circle cx="15" cy="12" r="1.2"/>
                  <path d="M12 10v4"/>
                </svg>
                <svg v-else-if="card.key === 'soil_fertility'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 20v-7"/>
                  <path d="M12 13c-2.8 0-5-1.5-5.8-4.3 3-.4 5 .5 5.8 2.5"/>
                  <path d="M12 13c2.8 0 5-1.5 5.8-4.3-3-.4-5 .5-5.8 2.5"/>
                  <path d="M6 20h12"/>
                  <path d="M8.5 17h7"/>
                </svg>
                <svg v-else-if="card.key === 'infrared'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 12a7 7 0 0 1 14 0"/>
                  <path d="M8.5 12a3.5 3.5 0 0 1 7 0"/>
                  <path d="M12 12v7"/>
                  <path d="M9 19h6"/>
                  <path d="M4 18l2-2M20 18l-2-2"/>
                </svg>
              </span>
              <div class="model-copy">
                <div class="model-title">
                  <strong>{{ card.label }}</strong>
                  <span class="badge-pair">
                    <b class="source-badge" :class="card.source.className">{{ card.source.label }}</b>
                    <b v-if="!card.available" class="source-badge availability pending">待接入</b>
                  </span>
                </div>
                <div class="model-value">{{ card.value }}<small v-if="!card.muted && card.unit">{{ card.unit }}</small></div>
              </div>
            </article>
          </div>
        </section>

        <section class="panel-block">
          <div class="block-title"><i></i><h2>趋势分组视图</h2></div>
          <div class="trend-grid">
            <article class="card trend-card">
              <h3>实测趋势</h3>
              <v-chart :option="measuredChartOption" autoresize class="trend-chart" />
            </article>
            <article class="card trend-card">
              <h3>土壤湿度趋势</h3>
              <v-chart :option="modelChartOption" autoresize class="trend-chart" />
            </article>
            <article class="card trend-card">
              <h3>CO2 / 红外事件</h3>
              <v-chart :option="eventChartOption" autoresize class="trend-chart" />
            </article>
          </div>
        </section>

        <section class="panel-block card weather-strip">
          <div class="block-title"><i></i><h2>室外气象参考（Open-Meteo）</h2><span>不作为棚内实测来源</span></div>
          <div class="weather-grid">
            <article v-for="item in weatherCards" :key="item.label">
              <span>{{ item.label }}</span>
              <strong>{{ fmtWeather(item.value) }}<small>{{ item.unit }}</small></strong>
            </article>
          </div>
        </section>
      </main>

      <aside class="dashboard-side">
        <section class="card side-panel">
          <div class="side-title"><i></i><h2>执行器控制</h2></div>
          <div class="actuator-list">
            <article v-for="item in actuatorCards" :key="item.key">
              <span class="actuator-icon" :style="{ color: item.color }">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M7 19h10"/><path d="M9 19v-7h6v7"/><path d="M10 12V6h4v6"/><path d="M8 6h8"/><path d="M17 9h3v5h-3"/>
                </svg>
              </span>
              <div>
                <strong>{{ item.label }}</strong>
                <small>{{ item.mode }} · {{ item.basis }}</small>
                <small v-if="systemStore.alarmLights[systemStore.currentBoardId] && item.key !== 'pump'" class="alarm-hint">报警期间操作将在报警解除后生效</small>
              </div>
              <span class="act-state">{{ item.active ? '运行' : '关闭' }}</span>
              <button class="toggle" :class="{ active: item.active }" type="button" @click="toggleActuator(item.key)"></button>
            </article>
          </div>
        </section>

        <section class="card side-panel auto-panel">
          <div class="side-title"><i></i><h2>自动浇水</h2></div>
          <div class="auto-state-row">
            <span class="status-dot" :class="autoWateringState.tone"></span>
            <div>
              <strong>{{ autoWateringState.label }}</strong>
              <small>{{ autoWateringState.detail }}</small>
            </div>
          </div>
          <div class="rule-box">
            <span>规则摘要</span>
            <strong>{{ autoRuleSummary }}</strong>
          </div>
          <div class="rule-box">
            <span>最近动作</span>
            <strong>{{ actionText(recentAction) }}</strong>
            <small v-if="recentAction">{{ actionSourceText(recentAction) }} · {{ recentAction.reason || '—' }} · {{ formatTimeOnly(recentAction.timestamp) }}</small>
          </div>
          <button class="btn btn-soft btn-reset-effects" type="button" @click="resetActuatorEffects">
            重置执行器效果
          </button>
        </section>

        <section class="card side-panel debug-panel">
          <div class="side-title">
            <i></i><h2>现场调试</h2>
            <button type="button" @click="fetchDebugEvents">刷新</button>
          </div>
          <p v-if="!debugEvents.length" class="empty-hint">暂无 bridge 调试事件</p>
          <article v-for="event in debugEvents" :key="`${event.timestamp}-${event.event}`" class="debug-row" :class="event.level">
            <span class="debug-dot"></span>
            <div>
              <strong>{{ debugTitle(event) }}</strong>
              <small>{{ debugDetail(event) }}</small>
            </div>
            <time>{{ formatTimeOnly(event.timestamp) }}</time>
          </article>
        </section>

        <section class="card side-panel alarm-panel">
          <div class="side-title">
            <i></i><h2>最近告警</h2>
            <button type="button" @click="router.push('/alarm-log')">查看全部</button>
          </div>
          <p v-if="!recentAlarms.length" class="empty-hint">近 7 天暂无告警</p>
          <article v-for="alarm in recentAlarms" :key="alarm.id" class="alarm-row">
            <span class="alarm-dot"></span>
            <div>
              <strong>{{ paramLabel(alarm.param_name) }}{{ alarm.value < alarm.threshold ? '低于阈值' : '超过阈值' }}</strong>
              <small>
                <b class="source-badge" :class="sourceForParam(alarm.param_name).className">{{ sourceForParam(alarm.param_name).label }}</b>
                {{ alarm.value }}{{ unitOf(alarm.param_name) }} / {{ alarm.threshold }}{{ unitOf(alarm.param_name) }}
              </small>
            </div>
            <time>{{ formatTimeOnly(alarm.timestamp) }}</time>
          </article>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.monitor-page {
  max-width: 1600px;
  margin: 0 auto;
}

.page-head,
.block-title,
.side-title,
.metric-card,
.metric-title,
.trend-card h3,
.actuator-list article,
.alarm-row,
.debug-row,
.weather-strip .block-title {
  display: flex;
  align-items: center;
}

.page-head {
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.page-subtitle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.test-tag {
  min-height: 22px;
}

.dashboard-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
}

.dashboard-main,
.dashboard-side {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.dashboard-main {
  align-content: start;
}

.dashboard-side {
  align-content: stretch;
}

.panel-block {
  min-width: 0;
}

.tone-warm {
  --tone: #ef4444;
  --tone-deep: #b91c1c;
  --tone-border: #fecaca;
  --tone-soft: #fff1f2;
  --tone-glow: rgba(239, 68, 68, 0.14);
}

.tone-sky {
  --tone: #0ea5e9;
  --tone-deep: #0369a1;
  --tone-border: #bae6fd;
  --tone-soft: #eff6ff;
  --tone-glow: rgba(14, 165, 233, 0.14);
}

.tone-sun {
  --tone: #f59e0b;
  --tone-deep: #b45309;
  --tone-border: #fde68a;
  --tone-soft: #fffbeb;
  --tone-glow: rgba(245, 158, 11, 0.16);
}

.tone-earth {
  --tone: #65a30d;
  --tone-deep: #3f6212;
  --tone-border: #d9f99d;
  --tone-soft: #f7fee7;
  --tone-glow: rgba(101, 163, 13, 0.14);
}

.tone-mint {
  --tone: #10b981;
  --tone-deep: #047857;
  --tone-border: #a7f3d0;
  --tone-soft: #ecfdf5;
  --tone-glow: rgba(16, 185, 129, 0.14);
}

.tone-violet {
  --tone: #8b5cf6;
  --tone-deep: #6d28d9;
  --tone-border: #ddd6fe;
  --tone-soft: #f5f3ff;
  --tone-glow: rgba(139, 92, 246, 0.14);
}

.tone-cyan {
  --tone: #06b6d4;
  --tone-deep: #0e7490;
  --tone-border: #a5f3fc;
  --tone-soft: #ecfeff;
  --tone-glow: rgba(6, 182, 212, 0.14);
}

.tone-leaf {
  --tone: #22c55e;
  --tone-deep: #15803d;
  --tone-border: #bbf7d0;
  --tone-soft: #f0fdf4;
  --tone-glow: rgba(34, 197, 94, 0.14);
}

.tone-rose {
  --tone: #f43f5e;
  --tone-deep: #be123c;
  --tone-border: #fecdd3;
  --tone-soft: #fff1f2;
  --tone-glow: rgba(244, 63, 94, 0.14);
}

.block-title,
.side-title {
  gap: 10px;
  margin-bottom: 10px;
}

.block-title i,
.side-title i {
  width: 4px;
  height: 22px;
  border-radius: 999px;
  background: #0aa344;
}

.block-title h2,
.side-title h2 {
  font-size: 17px;
  font-weight: 800;
}

.block-title span {
  margin-left: 8px;
  color: #64748b;
  font-size: 13px;
}

.measured-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  min-height: 104px;
  gap: 10px;
  padding: 13px 14px;
  position: relative;
  overflow: hidden;
  border-color: color-mix(in srgb, var(--tone-border), white 22%);
  background:
    linear-gradient(135deg, var(--tone-soft), #fff 58%),
    radial-gradient(circle at 92% 12%, var(--tone-glow), transparent 34%);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
}

.metric-card::after {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  background: linear-gradient(90deg, var(--tone), transparent);
  opacity: 0.9;
}

.metric-card.breach {
  border-color: #fecaca;
  background:
    linear-gradient(135deg, #fff1f2, #fff 58%),
    radial-gradient(circle at 92% 12%, rgba(239, 68, 68, 0.18), transparent 34%);
}

.metric-icon {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid color-mix(in srgb, var(--tone), white 28%);
  border-radius: 10px;
  background: linear-gradient(145deg, #fff, color-mix(in srgb, var(--tone-soft), white 12%));
  color: var(--tone-deep);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.66), 0 8px 16px var(--tone-glow);
  flex: 0 0 auto;
}

.metric-icon svg {
  width: 25px;
  height: 25px;
}

.metric-body {
  min-width: 0;
  flex: 1;
}

.metric-title {
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  color: #0f172a;
  font-weight: 750;
}

.metric-title > span:first-child {
  white-space: nowrap;
}

.metric-value {
  margin-top: 7px;
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.metric-value strong {
  color: var(--tone-deep);
  font-size: 26px;
  line-height: 1;
  font-weight: 850;
}

.metric-value small {
  color: #334155;
  font-size: 13px;
}

.source-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 2px 9px;
  border: 1px solid transparent;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 750;
  line-height: 1.2;
  white-space: nowrap;
}

.source-measured { border-color: #bfdbfe; background: #eff6ff; color: #2563eb; }
.source-model { border-color: #bbf7d0; background: #f0fdf4; color: #15803d; }
.source-firmware { border-color: #fed7aa; background: #fff7ed; color: #ea580c; }
.source-api { border-color: #bfdbfe; background: #eff6ff; color: #1d4ed8; }
.source-control { border-color: #ddd6fe; background: #f5f3ff; color: #7c3aed; }
.source-test { border-color: #fed7aa; background: #fff7ed; color: #c2410c; }
.source-system,
.source-pending { border-color: #e2e8f0; background: #f8fafc; color: #64748b; }

.badge-pair {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  flex: 0 0 auto;
}

.availability {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #15803d;
}

.availability.pending {
  border-color: #e2e8f0;
  background: #f8fafc;
  color: #64748b;
}

.model-panel {
  padding: 14px;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.model-card {
  min-height: 82px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid color-mix(in srgb, var(--tone-border), white 20%);
  border-radius: 7px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--tone-soft), white 18%), #fff 66%),
    radial-gradient(circle at 96% 8%, var(--tone-glow), transparent 36%);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.04);
}

.model-card.muted {
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--tone-soft), #f8fafc 32%), #fff 70%),
    radial-gradient(circle at 96% 8%, var(--tone-glow), transparent 36%);
}

.model-icon {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  border: 1px solid color-mix(in srgb, var(--tone), white 50%);
  background: linear-gradient(145deg, #fff, color-mix(in srgb, var(--tone-soft), white 8%));
  color: var(--tone-deep);
}

.model-icon svg {
  width: 24px;
  height: 24px;
}

.model-copy {
  min-width: 0;
}

.model-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.model-title strong {
  min-width: 0;
  color: #0f172a;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.25;
  white-space: normal;
}

.model-title .source-badge {
  min-height: 21px;
  padding: 1px 7px;
  font-size: 11px;
}

.model-value {
  margin-top: 7px;
  color: var(--tone-deep);
  font-size: 20px;
  font-weight: 850;
  line-height: 1;
}

.model-card.muted .model-value {
  color: color-mix(in srgb, var(--tone-deep), #64748b 52%);
  font-size: 15px;
}

.model-value small {
  margin-left: 4px;
  color: #334155;
  font-size: 12px;
  font-weight: 600;
}

.trend-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.trend-card {
  min-width: 0;
  padding: 14px;
}

.trend-card h3 {
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 15px;
  font-weight: 800;
}

.trend-chart {
  width: 100%;
  height: 260px;
}

.weather-strip {
  padding: 14px;
}

.weather-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.weather-grid article {
  display: grid;
  gap: 7px;
  padding: 12px 14px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
}

.weather-grid span {
  color: #475569;
  font-weight: 650;
}

.weather-grid strong {
  color: #15803d;
  font-size: 24px;
  line-height: 1;
}

.weather-grid small {
  margin-left: 4px;
  color: #334155;
  font-size: 13px;
}

.side-panel {
  padding: 18px;
  min-height: 0;
}

.actuator-list {
  display: grid;
  gap: 12px;
}

.actuator-list article {
  gap: 12px;
  min-height: 78px;
  padding: 14px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
}

.actuator-icon {
  width: 34px;
  height: 34px;
  display: inline-flex;
  flex: 0 0 auto;
}

.actuator-icon svg {
  width: 34px;
  height: 34px;
}

.actuator-list div {
  display: grid;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.actuator-list small {
  color: #64748b;
  font-size: 12px;
}

.alarm-hint {
  color: #e67e22;
  font-size: 11px;
  line-height: 1.3;
}

.act-state {
  color: #15803d;
  font-size: 12px;
  font-weight: 800;
}

.auto-panel {
  display: grid;
  gap: 12px;
}

.auto-state-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 12px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
}

.auto-state-row div,
.rule-box {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.auto-state-row strong,
.rule-box strong {
  color: #0f172a;
  font-size: 14px;
}

.auto-state-row small,
.rule-box span,
.rule-box small {
  color: #64748b;
  font-size: 12px;
}

.rule-box {
  padding: 12px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
  background: #fff;
}

.btn-reset-effects {
  margin-top: 10px;
  width: 100%;
  font-size: 12px;
  padding: 6px 0;
}

.alarm-panel .side-title button,
.debug-panel .side-title button {
  margin-left: auto;
  border: 0;
  background: transparent;
  color: #64748b;
  font-weight: 650;
}

.alarm-panel {
  display: flex;
  flex-direction: column;
}

.debug-panel {
  display: flex;
  flex-direction: column;
}

.empty-hint {
  color: #64748b;
  font-size: 13px;
  padding: 10px 0;
}

.alarm-row {
  gap: 10px;
  min-height: 0;
  flex: 1;
  border-top: 1px solid var(--border-light);
}

.debug-row {
  gap: 10px;
  min-height: 0;
  border-top: 1px solid var(--border-light);
  padding: 10px 0;
}

.alarm-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #ef4444;
  flex: 0 0 auto;
}

.debug-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #22c55e;
  flex: 0 0 auto;
}

.debug-row.warn .debug-dot {
  background: #f59e0b;
}

.debug-row.error .debug-dot {
  background: #ef4444;
}

.alarm-row div,
.debug-row div {
  display: grid;
  gap: 5px;
  min-width: 0;
  flex: 1;
}

.alarm-row strong,
.debug-row strong {
  color: #17223b;
  font-weight: 750;
}

.alarm-row small,
.debug-row small {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alarm-row time,
.debug-row time {
  color: #64748b;
  font-family: var(--font-mono);
  font-size: 12px;
}

@media (max-width: 1320px) {
  .dashboard-layout {
    grid-template-columns: 1fr;
  }

  .dashboard-side {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: none;
  }
}

@media (max-width: 1100px) {
  .trend-grid,
  .dashboard-side {
    grid-template-columns: 1fr;
  }

  .measured-grid,
  .weather-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .model-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .page-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .measured-grid,
  .model-grid,
  .weather-grid {
    grid-template-columns: 1fr;
  }

  .metric-card {
    align-items: center;
  }
}
</style>
