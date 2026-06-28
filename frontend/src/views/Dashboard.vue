<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useSensorStore } from '../stores/sensor'
import { useSystemStore } from '../stores/system'
import api from '../utils/api'
import { PARAM_LABEL, PARAM_UNIT } from '../utils/constants'
import { formatTimeOnly } from '../utils/format'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const router = useRouter()
const sensorStore = useSensorStore()
const systemStore = useSystemStore()

const colors = { temp: '#df463f', humi: '#3c98f0', light: '#fb8b12', soil: '#37a85b' }

const KEY_TO_PARAM = { temp: 'temperature', humi: 'humidity', light: 'light', soil: 'soil_moisture' }

const metricDefs = [
  { key: 'temp', label: '空气温度', icon: 'thermo', unit: '°C', color: colors.temp },
  { key: 'humi', label: '空气湿度', icon: 'drop', unit: '%', color: colors.humi },
  { key: 'light', label: '光照强度', icon: 'sun', unit: 'lux', color: colors.light },
  { key: 'soil', label: '土壤湿度', icon: 'sprout', unit: '%', color: colors.soil },
]

const thresholds = ref({})
const todayAlarms = ref(0)
const recentAlarms = ref([])

const hasData = computed(() => sensorStore.history.timestamps.length > 0)

function fmtVal(key, v) {
  return key === 'light' ? Math.round(v) : Number(v).toFixed(1)
}

function sparkPath(series) {
  if (!series || series.length < 2) return ''
  const min = Math.min(...series)
  const max = Math.max(...series)
  const range = max - min || 1
  const stepX = 180 / (series.length - 1)
  return series.map((v, i) => {
    const x = (i * stepX).toFixed(1)
    const y = (47 - ((v - min) / range) * 44).toFixed(1)
    return `${i === 0 ? 'M' : 'L'}${x} ${y}`
  }).join(' ')
}

const metricCards = computed(() => metricDefs.map((def) => {
  const cur = Number(sensorStore.current[def.key])
  const th = thresholds.value[KEY_TO_PARAM[def.key]]
  return {
    ...def,
    value: hasData.value ? fmtVal(def.key, cur) : '--',
    min: th ? fmtVal(def.key, th.min_value) : '—',
    max: th ? fmtVal(def.key, th.max_value) : '—',
    spark: sensorStore.history[def.key] || [],
    breach: th && hasData.value ? (cur < th.min_value || cur > th.max_value) : false,
  }
}))

const lastUpdateText = computed(() => {
  const ts = sensorStore.history.timestamps
  if (!ts.length) return '等待数据…'
  return `刷新 ${formatTimeOnly(ts[ts.length - 1])}`
})

const chartOption = computed(() => {
  const h = sensorStore.history
  const labels = h.timestamps.map(ts =>
    new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }))
  return {
    animation: false,
    color: [colors.temp, colors.humi, colors.light, colors.soil],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#e6e0d8',
      borderWidth: 1,
      textStyle: { color: '#24292f', fontSize: 12 },
    },
    legend: {
      top: 6,
      left: 0,
      itemWidth: 13,
      itemHeight: 3,
      itemGap: 24,
      textStyle: { color: '#4f565f', fontSize: 12 },
      data: ['空气温度(°C)', '空气湿度(%)', '光照强度(lux)', '土壤湿度(%)'],
    },
    grid: { top: 76, left: 50, right: 60, bottom: 42 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#dedbd5' } },
      axisLabel: { color: '#7d848d', fontSize: 12, hideOverlap: true },
    },
    yAxis: [
      { type: 'value', scale: true, axisLabel: { color: '#7d848d', fontSize: 12 }, splitLine: { lineStyle: { color: '#eeeae4', type: 'dashed' } } },
      { type: 'value', scale: true, position: 'right', axisLabel: { color: '#7d848d', fontSize: 12 }, splitLine: { show: false } },
    ],
    series: [
      { name: '空气温度(°C)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 0, lineStyle: { width: 2 }, data: h.temp },
      { name: '空气湿度(%)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 0, lineStyle: { width: 2 }, data: h.humi },
      { name: '光照强度(lux)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 1, lineStyle: { width: 2 }, data: h.light },
      { name: '土壤湿度(%)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 0, lineStyle: { width: 2 }, data: h.soil },
    ],
  }
})

const deviceRows = computed(() => [{
  name: '终端节点-01',
  type: 'CC2530 终端',
  params: '温湿度 · 光照 · 土壤',
  online: systemStore.deviceOnline,
  last: hasData.value ? formatTimeOnly(sensorStore.history.timestamps.at(-1)) : '—',
}])

const actuatorDefs = [
  { key: 'pump', label: '灌溉水泵', icon: '⌁', tone: 'blue' },
  { key: 'fertilizer', label: '施肥泵', icon: '⌁', tone: 'green' },
  { key: 'skylight', label: '天窗', icon: '□', tone: 'green' },
]

function paramLabel(name) {
  return PARAM_LABEL[name] || name
}

function unitOf(name) {
  return PARAM_UNIT[name] || ''
}

async function fetchStatus() {
  try {
    const res = await api.get('/api/status')
    systemStore.updateStatus(res.data)
  } catch { /* ignore */ }
}

async function fetchThresholds() {
  try {
    const res = await api.get('/api/thresholds')
    thresholds.value = Object.fromEntries(
      res.data.map(t => [t.param_name, { min_value: t.min_value, max_value: t.max_value }]),
    )
  } catch { /* ignore */ }
}

async function fetchSummary() {
  try {
    const res = await api.get('/api/alarms/summary')
    todayAlarms.value = res.data.today
  } catch { /* ignore */ }
}

async function fetchRecentAlarms() {
  const end = new Date()
  const start = new Date(end.getTime() - 7 * 24 * 3600 * 1000)
  try {
    const res = await api.get('/api/alarms', {
      params: { start: start.toISOString(), end: end.toISOString(), page: 1, page_size: 5 },
    })
    recentAlarms.value = res.data.items
  } catch {
    recentAlarms.value = []
  }
}

async function toggleActuator(device) {
  const next = systemStore.actuators[device] ? 'off' : 'on'
  try {
    await api.post('/api/control', { device, action: next })
    systemStore.setActuator(device, next === 'on')
  } catch { /* ignore */ }
}

function refresh() {
  fetchStatus()
  fetchThresholds()
  fetchSummary()
  fetchRecentAlarms()
}

onMounted(refresh)
</script>

<template>
  <div class="monitor-page">
    <header class="topbar">
      <h1 class="page-title">环境监测</h1>
      <div class="top-actions">
        <span class="greenhouse-name">智慧温室</span>
        <span class="online-pill" :class="{ offline: !systemStore.deviceOnline }">
          <span class="status-dot" :class="systemStore.deviceOnline ? 'green' : 'gray'"></span>
          {{ systemStore.deviceOnline ? '在线' : '离线' }}
        </span>
        <span class="refresh-text">{{ lastUpdateText }}</span>
        <button class="icon-btn" title="刷新" type="button" @click="refresh">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M16.2 10a6.2 6.2 0 1 1-1.8-4.4"/><path d="M16.2 4v4h-4"/></svg>
        </button>
        <button class="icon-btn" title="设置" type="button" @click="router.push('/settings')">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="10" cy="10" r="2.6"/><path d="M16 10a6.2 6.2 0 0 0-.1-.9l1.5-1.2-1.7-3-1.9.7a6.7 6.7 0 0 0-1.6-.9L12 2.7H8l-.3 2a6.7 6.7 0 0 0-1.6.9l-1.9-.7-1.7 3 1.5 1.2a6.2 6.2 0 0 0 0 1.8l-1.5 1.2 1.7 3 1.9-.7a6.7 6.7 0 0 0 1.6.9l.3 2h4l.3-2a6.7 6.7 0 0 0 1.6-.9l1.9.7 1.7-3-1.5-1.2c.1-.3.1-.6.1-.9z"/></svg>
        </button>
      </div>
    </header>

    <section class="metric-row">
      <article v-for="metric in metricCards" :key="metric.key" class="metric-card card">
        <div class="metric-head">
          <span class="metric-icon" :class="metric.key">
            <svg v-if="metric.icon === 'thermo'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M8 11.4V4.5a2 2 0 0 1 4 0v6.9a4 4 0 1 1-4 0z"/><path d="M10 7v6"/></svg>
            <svg v-else-if="metric.icon === 'drop'" viewBox="0 0 20 20" fill="currentColor"><path d="M10 2.5c3.7 4.2 5.6 7.2 5.6 9.4A5.6 5.6 0 0 1 4.4 12c0-2.2 1.9-5.2 5.6-9.5z"/></svg>
            <svg v-else-if="metric.icon === 'sun'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="10" cy="10" r="3.2"/><path d="M10 1.8v2.3M10 15.9v2.3M1.8 10h2.3M15.9 10h2.3M4.2 4.2l1.6 1.6M14.2 14.2l1.6 1.6M15.8 4.2l-1.6 1.6M5.8 14.2l-1.6 1.6"/></svg>
            <svg v-else viewBox="0 0 20 20" fill="currentColor"><path d="M6.4 10.6C3.5 9 3 5.7 3.2 3.2c2.9.2 5.8 1.5 6.4 4.6 1.2-2.9 4-4.2 7.1-4.4.3 3.9-1.6 6.6-5.4 7.7v5.7H9.6v-5.5a9 9 0 0 1-3.2-.7z"/></svg>
          </span>
          <strong>{{ metric.label }}</strong>
        </div>
        <div class="metric-value" :class="{ breach: metric.breach }"><span>{{ metric.value }}</span><small>{{ metric.unit }}</small></div>
        <svg class="sparkline" viewBox="0 0 180 54" preserveAspectRatio="none">
          <path :d="sparkPath(metric.spark)" fill="none" :stroke="metric.color" stroke-width="2" />
        </svg>
        <div class="metric-minmax">
          <span>下限 {{ metric.min }}</span>
          <span>上限 {{ metric.max }}</span>
        </div>
      </article>
    </section>

    <div class="dashboard-grid">
      <main class="left-stack">
        <section class="card trend-card">
          <div class="panel-head">
            <h2 class="section-title">实时趋势</h2>
            <span class="chart-hint">实时 · 最近 {{ sensorStore.history.timestamps.length }} 点</span>
          </div>
          <v-chart :option="chartOption" autoresize class="trend-chart" />
        </section>

        <section class="card device-card">
          <h2 class="section-title">设备列表</h2>
          <div class="table-scroll">
            <table class="data-table">
              <thead>
                <tr>
                  <th>设备名称</th>
                  <th>类型</th>
                  <th>采集参数</th>
                  <th>连接状态</th>
                  <th>最后上报</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in deviceRows" :key="row.name">
                  <td>{{ row.name }}</td>
                  <td>{{ row.type }}</td>
                  <td>{{ row.params }}</td>
                  <td><span class="status-dot" :class="row.online ? 'green' : 'gray'"></span> {{ row.online ? '在线' : '离线' }}</td>
                  <td>{{ row.last }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>

      <aside class="right-stack">
        <section class="card side-card">
          <h2 class="section-title">运行状态</h2>
          <div class="state-list">
            <div>
              <span class="side-icon" :class="systemStore.wsConnected ? 'green' : 'orange'">▣</span>
              <span>服务器连接</span>
              <strong :class="{ danger: !systemStore.wsConnected }">{{ systemStore.wsConnected ? '正常' : '断开' }}</strong>
            </div>
            <div>
              <span class="side-icon" :class="systemStore.deviceOnline ? 'green' : 'orange'">▢</span>
              <span>终端设备</span>
              <strong :class="{ danger: !systemStore.deviceOnline }">{{ systemStore.deviceOnline ? '在线' : '离线' }}</strong>
            </div>
            <div>
              <span class="side-icon" :class="todayAlarms > 0 ? 'orange' : 'green'">▣</span>
              <span>今日告警</span>
              <strong :class="{ danger: todayAlarms > 0 }">{{ todayAlarms }} 条</strong>
            </div>
          </div>
        </section>

        <section class="card side-card alarm-card">
          <h2 class="section-title">告警摘要</h2>
          <p v-if="!recentAlarms.length" class="empty-hint">近 7 天暂无告警</p>
          <div v-for="alarm in recentAlarms" :key="alarm.id" class="alarm-item">
            <span class="alarm-mark" :class="alarm.value < alarm.threshold ? 'orange' : 'red'">!</span>
            <div>
              <strong>{{ paramLabel(alarm.param_name) }}{{ alarm.value < alarm.threshold ? '偏低' : '偏高' }}</strong>
              <small>{{ alarm.value }}{{ unitOf(alarm.param_name) }} · 阈值 {{ alarm.threshold }}{{ unitOf(alarm.param_name) }}</small>
            </div>
            <time>{{ formatTimeOnly(alarm.timestamp) }}</time>
          </div>
          <button class="view-all" type="button" @click="router.push('/alarms')">查看全部</button>
        </section>

        <section class="card side-card">
          <h2 class="section-title">执行器控制</h2>
          <div class="actuator-list">
            <div v-for="act in actuatorDefs" :key="act.key">
              <span class="act-icon" :class="act.tone">{{ act.icon }}</span>
              <div>
                <strong>{{ act.label }}</strong>
                <small>{{ systemStore.mode === 'auto' ? '自动' : '手动' }} · {{ systemStore.actuators[act.key] ? '运行中' : '已停止' }}</small>
              </div>
              <button class="toggle" :class="{ active: systemStore.actuators[act.key] }" type="button" @click="toggleActuator(act.key)"></button>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.monitor-page {
  max-width: 1320px;
  margin: 0 auto;
}

.topbar,
.top-actions,
.metric-head,
.panel-head,
.state-list div,
.alarm-item,
.actuator-list > div {
  display: flex;
  align-items: center;
}

.topbar {
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.top-actions {
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.greenhouse-name {
  color: var(--text-primary);
  font-weight: 650;
}

.online-pill {
  height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 12px;
  border: 1px solid #d7eadc;
  border-radius: 6px;
  background: #f2fbf4;
  color: var(--green-deep);
  font-weight: 650;
}

.online-pill.offline {
  border-color: #ecd8d5;
  background: #fbf3f2;
  color: #b9543f;
}

.status-dot.gray {
  background: #b8b8b8;
}

.refresh-text {
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.metric-card {
  min-height: 178px;
  padding: 20px 18px;
}

.metric-head {
  gap: 10px;
  font-size: 15px;
}

.metric-icon {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.metric-icon svg {
  width: 21px;
  height: 21px;
}

.metric-icon.temp { color: var(--red); }
.metric-icon.humi { color: var(--blue); }
.metric-icon.light { color: var(--orange); }
.metric-icon.soil { color: var(--green); }

.metric-value {
  margin: 10px 0 4px 44px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.metric-value span {
  font-size: 33px;
  line-height: 1;
  font-weight: 780;
}

.metric-value small {
  color: var(--text-secondary);
  font-size: 15px;
  font-weight: 650;
}

.metric-value.breach span {
  color: var(--red);
}

.sparkline {
  width: 100%;
  height: 48px;
  margin-top: 8px;
}

.metric-minmax {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: 12px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 382px;
  gap: 12px;
}

.left-stack,
.right-stack {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.trend-card,
.device-card,
.side-card {
  padding: 18px;
}

.panel-head {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}

.chart-hint {
  color: var(--text-muted);
  font-size: 12px;
  font-family: var(--font-mono);
}

.trend-chart {
  width: 100%;
  height: 372px;
}

.device-card {
  min-height: 160px;
}

.device-card h2 {
  margin-bottom: 14px;
}

.right-stack {
  align-content: start;
}

.side-card {
  min-height: 142px;
}

.side-card h2 {
  margin-bottom: 17px;
}

.state-list {
  display: grid;
  gap: 18px;
}

.state-list div {
  gap: 10px;
}

.state-list strong {
  margin-left: auto;
  color: var(--green);
}

.state-list .danger {
  color: #f04b21;
}

.side-icon {
  width: 18px;
  color: var(--green);
}

.side-icon.orange {
  color: var(--orange);
}

.alarm-card {
  min-height: 202px;
}

.empty-hint {
  color: var(--text-muted);
  font-size: 13px;
  padding: 8px 0 14px;
}

.alarm-item {
  gap: 10px;
  padding: 4px 0 14px;
}

.alarm-item + .alarm-item {
  border-top: 1px solid var(--border-light);
  padding-top: 14px;
}

.alarm-mark {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  font-weight: 800;
  font-size: 12px;
  flex-shrink: 0;
}

.alarm-mark.red { background: var(--red); }
.alarm-mark.orange { background: var(--orange); }

.alarm-item div {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.alarm-item small {
  color: var(--text-muted);
}

.alarm-item time {
  margin-left: auto;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  flex-shrink: 0;
}

.view-all {
  width: 100%;
  height: 36px;
  margin-top: 6px;
  border: 0;
  border-top: 1px solid var(--border-light);
  background: #fff;
  color: var(--text-secondary);
  cursor: pointer;
}

.actuator-list {
  display: grid;
  gap: 18px;
}

.actuator-list > div {
  gap: 12px;
}

.act-icon {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--green);
  font-weight: 800;
}

.act-icon.blue {
  color: var(--blue);
}

.actuator-list div div {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.actuator-list small {
  color: var(--text-muted);
}

.actuator-list .toggle {
  margin-left: auto;
  flex-shrink: 0;
}

@media (max-width: 1100px) {
  .metric-row,
  .dashboard-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .right-stack {
    grid-column: 1 / -1;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .top-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .metric-row,
  .dashboard-grid,
  .right-stack {
    grid-template-columns: 1fr;
  }

  .metric-card {
    min-height: 160px;
  }

  .trend-chart {
    height: 300px;
  }
}
</style>
