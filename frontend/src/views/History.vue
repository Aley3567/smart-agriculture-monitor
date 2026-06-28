<script setup>
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { usePaginatedFetch } from '../composables/usePaginatedFetch'
import api from '../utils/api'
import { formatDateTime, formatShortDate } from '../utils/format'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const { dateRange, tableData, total, currentPage, pageSize, fetch: fetchTable, handlePageChange } =
  usePaginatedFetch('/api/history')
pageSize.value = 10

const selectedSeries = ref(['temp', 'humi', 'light', 'soil'])
const rangeKey = ref('7d')
const chartRows = ref([])

const RANGE_PRESETS = {
  '1d': { label: '1 天', ms: 24 * 3600 * 1000 },
  '7d': { label: '7 天', ms: 7 * 24 * 3600 * 1000 },
  '30d': { label: '30 天', ms: 30 * 24 * 3600 * 1000 },
}

const seriesOptions = [
  { key: 'temp', label: '温度', unit: '°C', color: '#df463f' },
  { key: 'humi', label: '湿度', unit: '%', color: '#3c98f0' },
  { key: 'light', label: '光照', unit: 'lux', color: '#fb8b12' },
  { key: 'soil', label: '土壤湿度', unit: '%', color: '#37a85b' },
]

function fmtNum(key, v) {
  if (typeof v !== 'number' || Number.isNaN(v)) return '—'
  return key === 'light' ? Math.round(v) : Number(v.toFixed(1))
}

const stats = computed(() => seriesOptions.map((s) => {
  const vals = chartRows.value.map(r => r[s.key]).filter(v => typeof v === 'number')
  if (!vals.length) return { ...s, value: '—', avg: '—', min: '—', max: '—' }
  const sum = vals.reduce((a, b) => a + b, 0)
  return {
    ...s,
    value: fmtNum(s.key, vals[vals.length - 1]),
    avg: fmtNum(s.key, sum / vals.length),
    min: fmtNum(s.key, Math.min(...vals)),
    max: fmtNum(s.key, Math.max(...vals)),
  }
}))

const latest = computed(() => chartRows.value.length ? chartRows.value[chartRows.value.length - 1] : null)

const tableRows = computed(() => tableData.value.map(r => ({
  id: r.id,
  time: formatDateTime(r.timestamp),
  temp: fmtNum('temp', r.temp),
  humi: fmtNum('humi', r.humi),
  light: fmtNum('light', r.light),
  soil: fmtNum('soil', r.soil),
})))

const totalPages = computed(() => Math.max(1, Math.ceil((total.value || 0) / pageSize.value)))

const rangeText = computed(() => {
  if (!dateRange.value || dateRange.value.length < 2) return ''
  return `${formatDateTime(dateRange.value[0])} ~ ${formatDateTime(dateRange.value[1])}`
})

const chartOption = computed(() => ({
  animation: false,
  color: seriesOptions.map(item => item.color),
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
    itemGap: 22,
    textStyle: { color: '#4f565f', fontSize: 12 },
    data: selectedSeries.value.map(key => seriesOptions.find(item => item.key === key)?.label),
  },
  grid: { top: 72, left: 50, right: 60, bottom: 42 },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: chartRows.value.map(r => formatShortDate(r.timestamp)),
    axisTick: { show: false },
    axisLine: { lineStyle: { color: '#dedbd5' } },
    axisLabel: { color: '#7d848d', fontSize: 12, hideOverlap: true },
  },
  yAxis: [
    { type: 'value', scale: true, axisLabel: { color: '#7d848d', fontSize: 12 }, splitLine: { lineStyle: { color: '#eeeae4', type: 'dashed' } } },
    { type: 'value', scale: true, position: 'right', axisLabel: { color: '#7d848d', fontSize: 12 }, splitLine: { show: false } },
  ],
  series: selectedSeries.value.map((key) => {
    const option = seriesOptions.find(item => item.key === key)
    return {
      name: option.label,
      type: 'line',
      smooth: true,
      symbol: 'none',
      yAxisIndex: option.key === 'light' ? 1 : 0,
      lineStyle: { width: 2, color: option.color },
      itemStyle: { color: option.color },
      data: chartRows.value.map(r => r[key]),
    }
  }),
}))

async function fetchChart() {
  if (!dateRange.value || dateRange.value.length < 2) return
  const [start, end] = dateRange.value
  try {
    const res = await api.get('/api/history', {
      params: { start: start.toISOString(), end: end.toISOString(), page: 1, page_size: 200 },
    })
    chartRows.value = [...res.data.items].reverse()
  } catch {
    chartRows.value = []
  }
}

function applyRange(key) {
  rangeKey.value = key
  const end = new Date()
  const start = new Date(end.getTime() - RANGE_PRESETS[key].ms)
  dateRange.value = [start, end]
  currentPage.value = 1
  fetchTable()
  fetchChart()
}

function toggleSeries(key) {
  if (selectedSeries.value.includes(key)) {
    selectedSeries.value = selectedSeries.value.filter(item => item !== key)
  } else {
    selectedSeries.value = [...selectedSeries.value, key]
  }
}

function exportCsv() {
  const rows = chartRows.value
  if (!rows.length) return
  const header = '时间,温度(°C),湿度(%),光照(lux),土壤湿度(%)'
  const lines = rows.map(r => `${formatDateTime(r.timestamp)},${r.temp},${r.humi},${r.light},${r.soil}`)
  const csv = '﻿' + [header, ...lines].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `history_${rangeKey.value}_${rows.length}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(() => applyRange('7d'))
</script>

<template>
  <div class="history-page">
    <header class="page-heading">
      <h1 class="page-title">历史数据</h1>
    </header>

    <section class="card filter-card">
      <div class="filter-line">
        <label>时间范围</label>
        <div class="date-tabs">
          <button
            v-for="(preset, key) in RANGE_PRESETS"
            :key="key"
            type="button"
            :class="{ active: rangeKey === key }"
            @click="applyRange(key)"
          >{{ preset.label }}</button>
        </div>
        <span class="range-text">{{ rangeText }}</span>
        <button class="btn btn-soft export-btn" type="button" @click="exportCsv">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M10 3v9"/><path d="m6.5 8.5 3.5 3.5 3.5-3.5"/><path d="M4 15.5h12"/></svg>
          导出 CSV
        </button>
      </div>
      <div class="filter-line second">
        <label>数据系列</label>
        <div class="series-pills">
          <button
            v-for="item in seriesOptions"
            :key="item.key"
            type="button"
            :class="{ active: selectedSeries.includes(item.key) }"
            :style="{ '--pill': item.color }"
            @click="toggleSeries(item.key)"
          >
            <span></span>{{ item.label }}
          </button>
        </div>
      </div>
    </section>

    <section class="stats-row">
      <article v-for="item in stats" :key="item.key" class="card stat-card">
        <div class="stat-top"><span>{{ item.label }}</span><small>{{ item.unit }}</small></div>
        <strong>{{ item.value }}</strong>
        <div class="stat-meta">
          <span>平均 {{ item.avg }}</span>
          <span>最低 {{ item.min }}</span>
          <span>最高 {{ item.max }}</span>
        </div>
      </article>
    </section>

    <div class="history-grid">
      <main class="main-stack">
        <section class="card trend-card">
          <div class="panel-head">
            <h2 class="section-title">趋势对比</h2>
            <span class="chart-hint">最近 {{ chartRows.length }} 个采样点</span>
          </div>
          <v-chart :option="chartOption" autoresize class="trend-chart" />
        </section>

        <section class="card table-card">
          <h2 class="section-title">数据记录</h2>
          <div class="table-scroll">
            <table class="data-table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th class="col-number">温度(°C)</th>
                  <th class="col-number">湿度(%)</th>
                  <th class="col-number">光照(lux)</th>
                  <th class="col-number">土壤湿度(%)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!tableRows.length">
                  <td colspan="5" class="empty-cell">该时间范围内暂无采样记录</td>
                </tr>
                <tr v-for="row in tableRows" :key="row.id">
                  <td>{{ row.time }}</td>
                  <td class="col-number">{{ row.temp }}</td>
                  <td class="col-number">{{ row.humi }}</td>
                  <td class="col-number">{{ row.light }}</td>
                  <td class="col-number">{{ row.soil }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="pagination" v-if="total > 0">
            <span>共 {{ total }} 条</span>
            <button type="button" :disabled="currentPage <= 1" @click="handlePageChange(currentPage - 1)">‹</button>
            <button class="active" type="button">{{ currentPage }} / {{ totalPages }}</button>
            <button type="button" :disabled="currentPage >= totalPages" @click="handlePageChange(currentPage + 1)">›</button>
            <span class="page-size-text">{{ pageSize }} 条/页</span>
          </div>
        </section>
      </main>

      <aside class="right-stack">
        <section class="card side-card latest-card">
          <div class="side-title">
            <h2 class="section-title">最新采样</h2>
            <span>{{ latest ? formatShortDate(latest.timestamp) : '—' }}</span>
          </div>
          <div class="latest-list">
            <div v-for="item in seriesOptions" :key="item.key">
              <span><i :style="{ background: item.color }"></i>{{ item.label }}</span>
              <strong>{{ latest ? fmtNum(item.key, latest[item.key]) : '—' }} <small>{{ item.unit }}</small></strong>
            </div>
          </div>
        </section>

        <section class="card side-card health-card">
          <h2 class="section-title">采样概况</h2>
          <div class="health-list">
            <div><span>范围内记录</span><strong>{{ total }}</strong></div>
            <div><span>图表采样点</span><strong>{{ chartRows.length }}</strong></div>
            <div><span>最新采样</span><strong>{{ latest ? formatDateTime(latest.timestamp).slice(5) : '—' }}</strong></div>
          </div>
        </section>

        <section class="card side-card action-card">
          <h2 class="section-title">操作</h2>
          <button class="btn btn-primary" type="button" @click="exportCsv">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M10 3v9"/><path d="m6.5 8.5 3.5 3.5 3.5-3.5"/><path d="M4 15.5h12"/></svg>
            导出 CSV
          </button>
          <button class="btn btn-soft" type="button" @click="applyRange(rangeKey)">刷新数据</button>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.history-page {
  max-width: 1320px;
  margin: 0 auto;
}

.page-heading {
  margin-bottom: 18px;
}

.filter-card {
  padding: 12px 14px;
  margin-bottom: 12px;
}

.filter-line,
.date-tabs,
.series-pills,
.panel-head,
.stat-top,
.stat-meta,
.side-title,
.latest-list div,
.health-list div {
  display: flex;
  align-items: center;
}

.filter-line {
  gap: 14px;
}

.filter-line + .filter-line {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.filter-line > label {
  color: var(--text-primary);
  font-weight: 650;
}

.date-tabs {
  overflow: hidden;
  border: 1px solid var(--border-light);
  border-radius: 6px;
}

.date-tabs button {
  width: 60px;
  height: 36px;
  border: 0;
  border-right: 1px solid var(--border-light);
  background: #fff;
  cursor: pointer;
}

.date-tabs button:last-child {
  border-right: 0;
}

.date-tabs .active {
  background: #edf8f1;
  color: var(--green-deep);
  font-weight: 750;
}

.range-text {
  color: var(--text-muted);
  font-size: 12px;
  font-family: var(--font-mono);
}

.export-btn {
  margin-left: auto;
}

.series-pills {
  gap: 10px;
}

.series-pills button {
  height: 34px;
  min-width: 82px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid color-mix(in srgb, var(--pill), white 72%);
  border-radius: 999px;
  background: color-mix(in srgb, var(--pill), white 94%);
  color: var(--text-primary);
  font-weight: 650;
  cursor: pointer;
  opacity: .55;
}

.series-pills button.active {
  opacity: 1;
}

.series-pills span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--pill);
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.stat-card {
  padding: 16px;
}

.stat-top {
  justify-content: space-between;
  color: var(--text-primary);
  font-weight: 650;
}

.stat-top small {
  color: var(--text-secondary);
}

.stat-card strong {
  display: block;
  margin-top: 8px;
  font-size: 30px;
  line-height: 1;
}

.stat-meta {
  justify-content: space-between;
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 12px;
}

.history-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 12px;
}

.main-stack,
.right-stack {
  display: grid;
  gap: 12px;
  align-content: start;
  min-width: 0;
}

.trend-card,
.table-card,
.side-card {
  padding: 18px;
}

.panel-head {
  justify-content: space-between;
  margin-bottom: 8px;
}

.chart-hint {
  color: var(--text-muted);
  font-size: 12px;
  font-family: var(--font-mono);
}

.trend-chart {
  width: 100%;
  height: 316px;
}

.table-card h2 {
  margin-bottom: 14px;
}

.empty-cell {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 18px 0;
}

.page-size-text {
  margin-left: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.latest-card {
  min-height: 180px;
}

.side-card {
  min-height: 154px;
}

.side-title {
  justify-content: space-between;
  margin-bottom: 16px;
}

.side-title span {
  color: var(--text-muted);
}

.latest-list,
.health-list {
  display: grid;
  gap: 18px;
}

.latest-list div,
.health-list div {
  justify-content: space-between;
}

.latest-list span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
}

.latest-list i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.latest-list small {
  color: var(--text-secondary);
  font-weight: 500;
}

.health-list strong {
  color: var(--green);
}

.action-card {
  display: grid;
  gap: 12px;
}

.action-card .btn {
  width: 100%;
}

@media (max-width: 1100px) {
  .stats-row,
  .history-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .right-stack {
    grid-column: 1 / -1;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .filter-line {
    align-items: stretch;
    flex-direction: column;
  }

  .date-tabs,
  .series-pills {
    overflow-x: auto;
  }

  .export-btn {
    margin-left: 0;
  }

  .stats-row,
  .history-grid,
  .right-stack {
    grid-template-columns: 1fr;
  }

  .panel-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
