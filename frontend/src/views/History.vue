<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useSensorStore } from '../stores/sensor'
import { usePaginatedFetch } from '../composables/usePaginatedFetch'
import api from '../utils/api'
import { formatDateTime, formatDateTimeMinute, formatShortDate } from '../utils/format'
import {
  formatFieldValue,
  sourceMeta,
} from '../utils/sources'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const sensorStore = useSensorStore()
const { dateRange, tableData, total, currentPage, pageSize, queryParams, fetch: fetchTable, handlePageChange } =
  usePaginatedFetch('/api/history')

pageSize.value = 10

const rangeKey = ref('24h')
const sourceFilter = ref('all')
const chartRows = ref([])
const summary = ref({ total: 0, today: 0, last_24h: 0 })
const nowTick = ref(new Date())
let clockTimer = null

const RANGE_PRESETS = {
  '1h': { label: '近1小时', ms: 60 * 60 * 1000 },
  '24h': { label: '近24小时', ms: 24 * 3600 * 1000 },
  '7d': { label: '近7天', ms: 7 * 24 * 3600 * 1000 },
}

const SOURCE_FILTERS = [
  { value: 'all', label: '全部' },
  { value: 'real', label: '真实数据' },
  { value: 'test', label: '测试数据' },
]

const tableRows = computed(() => tableData.value.map((row) => ({
  id: row.id,
  time: formatDateTimeMinute(row.timestamp),
  source: row.source || 'bridge',
  isTest: Boolean(row.is_test),
  raw: row,
})))

const latest = computed(() => chartRows.value.length ? chartRows.value[chartRows.value.length - 1] : null)
const totalPages = computed(() => Math.max(1, Math.ceil((total.value || 0) / pageSize.value)))
const allFieldKeys = computed(() => [...sensorStore.measuredFieldKeys, ...sensorStore.modelFieldKeys])
const pageNumbers = computed(() => {
  const totalPageCount = totalPages.value
  const current = currentPage.value
  if (totalPageCount <= 7) {
    return Array.from({ length: totalPageCount }, (_, index) => index + 1)
  }
  if (current <= 4) return [1, 2, 3, 4, 5, 'ellipsis-end', totalPageCount]
  if (current >= totalPageCount - 3) {
    return [1, 'ellipsis-start', totalPageCount - 4, totalPageCount - 3, totalPageCount - 2, totalPageCount - 1, totalPageCount]
  }
  return [1, 'ellipsis-start', current - 1, current, current + 1, 'ellipsis-end', totalPageCount]
})

const kpis = computed(() => [
  { label: '采样总数', value: total.value || 0, suffix: '次', tone: 'green', source: SOURCE_FILTERS.find(item => item.value === sourceFilter.value)?.label || '全部' },
  { label: '实测字段', value: sensorStore.measuredFieldKeys.length, suffix: '个', tone: 'blue', source: '后端字段目录' },
  { label: '模型字段', value: sensorStore.modelFieldKeys.length, suffix: '个', tone: 'green', source: '后端字段目录' },
  { label: '异常次数', value: summary.value.last_24h || 0, suffix: '次', tone: 'red', source: '近 24 小时' },
])

const qualityItems = computed(() => [
  { label: '最新同步', value: latest.value ? formatDateTimeMinute(latest.value.timestamp) : '—' },
  { label: '缺失字段（近24小时）', value: `${sensorStore.modelFieldKeys.filter(key => !sensorStore.fieldFor(key)?.available).length} 个模型字段` },
  { label: '字段来源', value: '由后端 sensor-fields 合同返回' },
  { label: '历史曲线', value: '按来源分组，避免混合解读' },
])

const rangeText = computed(() => {
  const preset = RANGE_PRESETS[rangeKey.value]
  if (preset) {
    const end = nowTick.value
    const start = new Date(end.getTime() - preset.ms)
    return `${formatDateTimeMinute(start)} ~ ${formatDateTimeMinute(end)}`
  }
  if (!dateRange.value || dateRange.value.length < 2) return ''
  return `${formatDateTimeMinute(dateRange.value[0])} ~ ${formatDateTimeMinute(dateRange.value[1])}`
})

const measuredChartOption = computed(() => makeLineOption({
  labels: chartRows.value.map(r => formatShortDate(r.timestamp)),
  colors: ['#ef4444', '#2563eb', '#f97316'],
  legend: ['温度(°C)', '空气湿度(%)', '相对光照'],
  series: [
    { name: '温度(°C)', data: chartRows.value.map(r => r.temp), yAxisIndex: 0 },
    { name: '空气湿度(%)', data: chartRows.value.map(r => r.humi), yAxisIndex: 0 },
    { name: '相对光照', data: chartRows.value.map(r => r.light), yAxisIndex: 1 },
  ],
}))

const modelChartOption = computed(() => makeLineOption({
  labels: chartRows.value.map(r => formatShortDate(r.timestamp)),
  colors: ['#16a34a', '#059669', '#0d9488', '#0891b2', '#65a30d', '#dc2626'],
  legend: ['土壤湿度(%)', 'CO2(ppm)', 'EC(dS/m)', 'TDS(ppm)', '肥力(%)', '红外'],
  series: [
    { name: '土壤湿度(%)', data: chartRows.value.map(r => rowValue(r, 'soil')), yAxisIndex: 0 },
    { name: 'CO2(ppm)', data: chartRows.value.map(r => rowValue(r, 'co2')), yAxisIndex: 1 },
    { name: 'EC(dS/m)', data: chartRows.value.map(r => rowValue(r, 'soil_ec')), yAxisIndex: 1 },
    { name: 'TDS(ppm)', data: chartRows.value.map(r => rowValue(r, 'soil_tds')), yAxisIndex: 1 },
    { name: '肥力(%)', data: chartRows.value.map(r => rowValue(r, 'soil_fertility')), yAxisIndex: 0 },
    { name: '红外', data: chartRows.value.map(r => rowValue(r, 'infrared')), yAxisIndex: 0 },
  ],
}))

function makeLineOption({ labels, colors, legend, series }) {
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
      top: 3,
      left: 0,
      itemWidth: 15,
      itemHeight: 3,
      itemGap: 14,
      textStyle: { color: '#334155', fontSize: 12 },
      data: legend,
    },
    grid: { top: 64, left: 46, right: 48, bottom: 34 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#dbe3ef' } },
      axisLabel: { color: '#64748b', fontSize: 11, hideOverlap: true },
    },
    yAxis: [
      { type: 'value', scale: true, axisLabel: { color: '#64748b', fontSize: 11 }, splitLine: { lineStyle: { color: '#edf2f7', type: 'dashed' } } },
      { type: 'value', scale: true, position: 'right', axisLabel: { color: '#64748b', fontSize: 11 }, splitLine: { show: false } },
    ],
    series: series.map(item => ({
      ...item,
      type: 'line',
      smooth: true,
      symbol: 'none',
      connectNulls: false,
      lineStyle: { width: item.data.every(v => v == null) ? 1 : 2, type: item.data.every(v => v == null) ? 'dashed' : 'solid' },
    })),
  }
}

async function fetchChart() {
  if (!dateRange.value || dateRange.value.length < 2) return
  const [start, end] = dateRange.value
  try {
    const res = await api.get('/api/history', {
      params: { start: start.toISOString(), end: end.toISOString(), page: 1, page_size: 200, source: sourceFilter.value },
    })
    sensorStore.setFieldCatalog(res.data.fields)
    chartRows.value = [...res.data.items].reverse()
  } catch {
    chartRows.value = []
  }
}

async function fetchSummary() {
  try {
    const res = await api.get('/api/alarms/summary')
    summary.value = res.data
  } catch { /* keep defaults */ }
}

function applyRange(key) {
  rangeKey.value = key
  const end = new Date()
  const start = new Date(end.getTime() - RANGE_PRESETS[key].ms)
  dateRange.value = [start, end]
  currentPage.value = 1
  queryParams.value = { source: sourceFilter.value }
  fetchTable()
  fetchChart()
}

function applySourceFilter(value) {
  sourceFilter.value = value
  currentPage.value = 1
  queryParams.value = { source: value }
  fetchTable()
  fetchChart()
}

function goPage(page) {
  if (typeof page !== 'number') return
  const next = Math.max(1, Math.min(totalPages.value, page))
  if (next === currentPage.value) return
  handlePageChange(next)
}

function valueOf(row, key) {
  const field = sensorStore.fieldFor(key)
  if (!field.available) return '—'
  return formatFieldValue(field, rowValue(row, key))
}

function rowValue(row, key) {
  if (row[key] !== undefined) return row[key]
  const fact = row.facts?.[key]
  if (fact && fact.value !== undefined) return fact.value
  return null
}

function sourceForField(key) {
  const field = sensorStore.fieldFor(key)
  return field.available ? sourceMeta(field.source) : sourceMeta('pending')
}

function exportCsv() {
  const rows = chartRows.value
  if (!rows.length) return
  const header = '时间,温度(°C),空气湿度(%),相对光照,土壤湿度(%),CO2,EC,TDS,肥力,红外,source,is_test,来源说明'
  const lines = rows.map(r => [
    formatDateTime(r.timestamp),
    r.temp,
    r.humi,
    r.light,
    r.soil,
    rowValue(r, 'co2') ?? '',
    rowValue(r, 'soil_ec') ?? '',
    rowValue(r, 'soil_tds') ?? '',
    rowValue(r, 'soil_fertility') ?? '',
    rowValue(r, 'infrared') ?? '',
    r.source || '',
    Boolean(r.is_test),
    'temp/humi=实测; light=GL5516/P0.7 ADC相对光照值; soil=板端模拟; co2/EC/TDS/肥力/红外=后端模型',
  ].join(','))
  const csv = '﻿' + [header, ...lines].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `history_${rangeKey.value}_${rows.length}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  applyRange('24h')
  fetchSummary()
  clockTimer = window.setInterval(() => {
    nowTick.value = new Date()
  }, 30 * 1000)
})

onUnmounted(() => {
  if (clockTimer) window.clearInterval(clockTimer)
})
</script>

<template>
  <div class="history-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">历史分析</h1>
        <p class="page-subtitle">按来源查看历史趋势、数据质量和导出记录</p>
      </div>
      <button class="btn btn-soft" type="button" @click="exportCsv">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M10 3v9"/><path d="m6.5 8.5 3.5 3.5 3.5-3.5"/><path d="M4 15.5h12"/></svg>
        导出数据
      </button>
    </header>

    <section class="card filter-card">
      <div class="range-field">
        <label>时间范围</label>
        <span>{{ rangeText }}</span>
      </div>
      <div class="granularity">
        <label>时间粒度</label>
        <div class="range-tabs">
          <button
            v-for="(preset, key) in RANGE_PRESETS"
            :key="key"
            type="button"
            :class="{ active: rangeKey === key }"
            @click="applyRange(key)"
          >{{ preset.label }}</button>
        </div>
      </div>
      <div class="granularity">
        <label>数据来源</label>
        <div class="range-tabs">
          <button
            v-for="item in SOURCE_FILTERS"
            :key="item.value"
            type="button"
            :class="{ active: sourceFilter === item.value }"
            @click="applySourceFilter(item.value)"
          >{{ item.label }}</button>
        </div>
      </div>
    </section>

    <section class="kpi-row">
      <article v-for="item in kpis" :key="item.label" class="card kpi-card" :class="item.tone">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}<small>{{ item.suffix }}</small></strong>
        <p>{{ item.source }}</p>
      </article>
    </section>

    <div class="analysis-grid">
      <main class="chart-stack">
        <section class="card chart-panel">
          <div class="panel-head">
            <h2 class="section-title">板端实测趋势</h2>
            <span>温度 / 空气湿度 / 光照</span>
          </div>
          <v-chart :option="measuredChartOption" autoresize class="chart" />
        </section>

        <section class="card chart-panel">
          <div class="panel-head">
            <h2 class="section-title">模型推算趋势</h2>
            <span>当前只有土壤湿度字段可从后端读取</span>
          </div>
          <v-chart :option="modelChartOption" autoresize class="chart" />
        </section>
      </main>

      <aside class="card quality-panel">
        <div class="panel-head tight">
          <h2 class="section-title">数据质量</h2>
        </div>
        <div class="quality-list">
          <article v-for="item in qualityItems" :key="item.label">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </article>
        </div>
      </aside>

      <section class="card table-panel">
        <h2 class="section-title">数据记录</h2>
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>时间</th>
                <th v-for="key in allFieldKeys" :key="key" class="col-number">
                  {{ sensorStore.fieldFor(key).label }}
                  <b class="source-badge" :class="sourceForField(key).className">{{ sourceForField(key).label }}</b>
                </th>
                <th>来源说明</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!tableRows.length">
                <td :colspan="3 + allFieldKeys.length" class="empty-cell">该时间范围内暂无采样记录</td>
              </tr>
              <tr v-for="row in tableRows" :key="row.id">
                <td>{{ row.time }}</td>
                <td v-for="key in allFieldKeys" :key="key" class="col-number">
                  {{ valueOf(row.raw, key) }}<small v-if="sensorStore.fieldFor(key).available && sensorStore.fieldFor(key).unit"> {{ sensorStore.fieldFor(key).unit }}</small>
                </td>
                <td class="source-note">
                  <span>{{ row.source }} · 来源由后端字段合同返回</span>
                  <b v-if="row.isTest" class="injection-tag">测试注入</b>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pagination" v-if="total > 0">
          <span>共 {{ total }} 条</span>
          <button type="button" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">上一页</button>
          <template v-for="page in pageNumbers" :key="page">
            <span v-if="typeof page !== 'number'" class="page-ellipsis">…</span>
            <button v-else type="button" :class="{ active: page === currentPage }" @click="goPage(page)">{{ page }}</button>
          </template>
          <button type="button" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">下一页</button>
          <span class="page-size-text">{{ pageSize }} 条/页</span>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.history-page {
  max-width: 1600px;
  margin: 0 auto;
}

.page-head,
.filter-card,
.range-field,
.granularity,
.panel-head {
  display: flex;
  align-items: center;
}

.page-head {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.filter-card {
  justify-content: space-between;
  gap: 18px;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.range-field,
.granularity {
  gap: 14px;
}

.range-field label,
.granularity label {
  color: #334155;
  font-weight: 750;
}

.range-field span {
  min-width: 420px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  padding: 0 14px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
  background: #fff;
  color: #0f172a;
  font-family: var(--font-mono);
  font-size: 13px;
}

.range-tabs {
  display: flex;
  overflow: hidden;
  border: 1px solid var(--border-light);
  border-radius: 7px;
}

.range-tabs button {
  height: 36px;
  min-width: 88px;
  border: 0;
  border-right: 1px solid var(--border-light);
  background: #fff;
  color: #334155;
  font-weight: 650;
}

.range-tabs button:last-child {
  border-right: 0;
}

.range-tabs .active {
  background: #e9f8ee;
  color: #0a9b45;
  font-weight: 800;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.kpi-card {
  min-height: 112px;
  display: grid;
  gap: 8px;
  padding: 18px 20px;
}

.kpi-card span {
  color: #475569;
  font-weight: 700;
}

.kpi-card strong {
  font-size: 30px;
  line-height: 1;
  font-weight: 850;
}

.kpi-card small {
  margin-left: 4px;
  color: #475569;
  font-size: 13px;
  font-weight: 650;
}

.kpi-card p {
  color: #64748b;
  font-size: 13px;
}

.kpi-card.green strong { color: #16a34a; }
.kpi-card.blue strong { color: #2563eb; }
.kpi-card.red strong { color: #ef4444; }

.analysis-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
}

.chart-stack {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  min-width: 0;
}

.chart-panel,
.quality-panel,
.table-panel {
  padding: 18px;
  min-width: 0;
}

.panel-head {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-head span {
  color: #64748b;
  font-size: 12px;
}

.panel-head.tight {
  justify-content: flex-start;
}

.chart {
  width: 100%;
  height: 330px;
}

.quality-list {
  display: grid;
  gap: 12px;
}

.quality-list article {
  display: grid;
  gap: 6px;
  min-height: 70px;
  padding: 14px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
}

.quality-list span {
  color: #64748b;
  font-weight: 650;
}

.quality-list strong {
  color: #17223b;
  font-size: 15px;
}

.table-panel {
  grid-column: 1 / -1;
}

.table-panel h2 {
  margin-bottom: 14px;
}

.data-table th {
  vertical-align: middle;
}

.data-table th .source-badge {
  margin-left: 6px;
}

.data-table small {
  color: #64748b;
}

.source-note {
  color: #64748b;
  font-size: 12px;
}

.source-note span,
.injection-tag {
  vertical-align: middle;
}

.injection-tag {
  display: inline-flex;
  align-items: center;
  height: 22px;
  margin-left: 8px;
  padding: 0 8px;
  border: 1px solid #fed7aa;
  border-radius: 999px;
  background: #fff7ed;
  color: #c2410c;
  font-size: 12px;
  font-weight: 800;
}

.empty-cell {
  text-align: center;
  color: #64748b;
  padding: 18px 0;
}

.page-size-text {
  margin-left: 8px;
  color: #64748b;
}

.pagination {
  flex-wrap: wrap;
  gap: 6px;
}

.pagination button {
  min-width: 34px;
  height: 32px;
  padding: 0 10px;
}

.page-ellipsis {
  width: 28px;
  text-align: center;
  color: #64748b;
}

@media (max-width: 1200px) {
  .analysis-grid,
  .chart-stack {
    grid-template-columns: 1fr;
  }

  .kpi-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 820px) {
  .page-head,
  .filter-card,
  .range-field,
  .granularity {
    align-items: stretch;
    flex-direction: column;
  }

  .range-field span {
    min-width: 0;
    width: 100%;
  }

  .range-tabs {
    overflow-x: auto;
  }

  .kpi-row {
    grid-template-columns: 1fr;
  }
}
</style>
