<script setup>
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { usePaginatedFetch } from '../composables/usePaginatedFetch'
import { HISTORY_FALLBACK } from '../utils/fallbackData'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const { dateRange, tableData, total, currentPage, pageSize, fetch: fetchData, handlePageChange } =
  usePaginatedFetch('/api/history')

const selectedSeries = ref(['temp', 'humi', 'light', 'soil'])
const interval = ref('5 分钟')

const seriesOptions = [
  { key: 'temp', label: '温度', unit: '°C', color: '#df463f', value: '24.6', avg: '24.1', min: '18.2', max: '28.7' },
  { key: 'humi', label: '湿度', unit: '%', color: '#3c98f0', value: '68.3', avg: '65.4', min: '45.0', max: '82.0' },
  { key: 'light', label: '光照', unit: 'lux', color: '#fb8b12', value: '856', avg: '812', min: '120', max: '1620' },
  { key: 'soil', label: '土壤湿度', unit: '%', color: '#37a85b', value: '32.7', avg: '31.1', min: '21.4', max: '48.6' },
]

const days = ['06/21 00:00', '06/22 00:00', '06/23 00:00', '06/24 00:00', '06/25 00:00', '06/26 00:00', '06/27 00:00', '06/28 00:00']
const displayRows = computed(() => tableData.value.length ? tableData.value.slice(0, 5) : HISTORY_FALLBACK.rows)
const displayTotal = computed(() => total.value || 288)
const totalPages = computed(() => Math.ceil(displayTotal.value / pageSize.value) || 288)

onMounted(() => {
  dateRange.value = [new Date('2026-06-21T00:00:00'), new Date('2026-06-28T23:59:00')]
  fetchData()
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
  grid: { top: 72, left: 50, right: 68, bottom: 42 },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: Array.from({ length: 17 }, (_, i) => days[Math.min(days.length - 1, Math.floor(i / 2))]),
    axisTick: { show: false },
    axisLine: { lineStyle: { color: '#dedbd5' } },
    axisLabel: { color: '#7d848d', fontSize: 12, hideOverlap: true },
  },
  yAxis: [
    { type: 'value', min: -10, max: 40, splitNumber: 5, axisLabel: { color: '#7d848d', fontSize: 12 }, splitLine: { lineStyle: { color: '#eeeae4', type: 'dashed' } } },
    { type: 'value', min: 0, max: 100, splitNumber: 4, axisLabel: { color: '#7d848d', fontSize: 12 }, splitLine: { show: false } },
  ],
  series: selectedSeries.value.map(key => {
    const option = seriesOptions.find(item => item.key === key)
    return {
      name: option.label,
      type: 'line',
      smooth: true,
      symbol: 'none',
      yAxisIndex: key === 'temp' ? 0 : 1,
      lineStyle: { width: 2, color: option.color },
      itemStyle: { color: option.color },
      data: HISTORY_FALLBACK.chart[key],
    }
  }),
}))

function toggleSeries(key) {
  if (selectedSeries.value.includes(key)) {
    selectedSeries.value = selectedSeries.value.filter(item => item !== key)
  } else {
    selectedSeries.value = [...selectedSeries.value, key]
  }
}
</script>

<template>
  <div class="history-page">
    <header class="page-heading">
      <h1 class="page-title">历史数据</h1>
    </header>

    <section class="card filter-card">
      <div class="filter-line">
        <label>时间范围</label>
        <div class="date-range">
          <span>{{ HISTORY_FALLBACK.range.startDate }}</span>
          <span>{{ HISTORY_FALLBACK.range.startTime }}</span>
          <span class="dash">-</span>
          <span>{{ HISTORY_FALLBACK.range.endDate }}</span>
          <span>{{ HISTORY_FALLBACK.range.endTime }}</span>
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="4" y="4.5" width="12" height="12" rx="2"/><path d="M7 2.8v3.5M13 2.8v3.5M4 8h12"/></svg>
        </div>
        <div class="date-tabs">
          <button type="button">1天</button>
          <button class="active" type="button">7天</button>
          <button type="button">30天</button>
          <button type="button">自定义</button>
        </div>
        <button class="btn btn-soft export-btn" type="button">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M10 3v9"/><path d="m6.5 8.5 3.5 3.5 3.5-3.5"/><path d="M4 15.5h12"/></svg>
          导出
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
          <button class="small-select" type="button">⌄</button>
        </div>
        <div class="interval">
          <label>采样间隔</label>
          <button class="select-like" type="button">{{ interval }} <span>⌄</span></button>
        </div>
      </div>
    </section>

    <section class="stats-row">
      <article v-for="item in seriesOptions" :key="item.key" class="card stat-card">
        <div class="stat-top"><span>{{ item.label }}</span><small>{{ item.unit }}</small></div>
        <strong>{{ item.value }}</strong>
        <svg viewBox="0 0 210 26" preserveAspectRatio="none">
          <path d="M0 15 C36 14, 52 16, 84 15 C112 14, 132 18, 160 16 C184 14, 198 15, 210 14" fill="none" :stroke="item.color" stroke-width="2" />
        </svg>
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
            <div class="chart-actions">
              <button class="btn btn-ghost" type="button">自动缩放 <span>⌄</span></button>
              <button class="btn btn-ghost" type="button">重置缩放</button>
            </div>
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
                  <th>数据状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in displayRows" :key="row.id || row.timestamp">
                  <td>{{ row.timestamp }}</td>
                  <td class="col-number">{{ row.temp }}</td>
                  <td class="col-number">{{ row.humi }}</td>
                  <td class="col-number">{{ row.light }}</td>
                  <td class="col-number">{{ row.soil }}</td>
                  <td><span class="status-dot green"></span> {{ row.status || '正常' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="pagination">
            <button disabled type="button">‹</button>
            <button class="active" type="button" @click="handlePageChange(1)">1</button>
            <button type="button" @click="handlePageChange(2)">2</button>
            <button type="button" @click="handlePageChange(3)">3</button>
            <button type="button" @click="handlePageChange(4)">4</button>
            <button type="button" @click="handlePageChange(5)">5</button>
            <span>...</span>
            <button type="button">{{ totalPages }}</button>
            <button type="button">›</button>
            <button class="page-size" type="button">10 条/页 ⌄</button>
          </div>
        </section>
      </main>

      <aside class="right-stack">
        <section class="card side-card latest-card">
          <div class="side-title">
            <h2 class="section-title">最新采样</h2>
            <span>{{ HISTORY_FALLBACK.latest.time }}</span>
          </div>
          <div class="latest-list">
            <div v-for="item in seriesOptions" :key="item.key">
              <span><i :style="{ background: item.color }"></i>{{ item.label }}</span>
              <strong>{{ HISTORY_FALLBACK.latest[item.key] }} <small>{{ item.unit }}</small></strong>
            </div>
          </div>
        </section>

        <section class="card side-card health-card">
          <h2 class="section-title">采样健康</h2>
          <div class="health-list">
            <div><span>采样成功率</span><strong>{{ HISTORY_FALLBACK.health.successRate }}</strong></div>
            <div><span>缺失数据</span><strong>{{ HISTORY_FALLBACK.health.missing }}</strong></div>
            <div><span>设备状态</span><strong>{{ HISTORY_FALLBACK.health.deviceStatus }}</strong></div>
          </div>
        </section>

        <section class="card side-card action-card">
          <h2 class="section-title">操作</h2>
          <button class="btn btn-primary" type="button">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M10 3v9"/><path d="m6.5 8.5 3.5 3.5 3.5-3.5"/><path d="M4 15.5h12"/></svg>
            导出
          </button>
          <button class="btn btn-soft" type="button">查看记录</button>
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
.date-range,
.date-tabs,
.series-pills,
.interval,
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

.date-range {
  height: 36px;
  min-width: 386px;
  gap: 18px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #fff;
}

.date-range svg {
  width: 16px;
  height: 16px;
  margin-left: auto;
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
}

.date-tabs button:last-child {
  width: 72px;
  border-right: 0;
}

.date-tabs .active {
  background: #edf8f1;
  color: var(--green-deep);
  font-weight: 750;
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
}

.series-pills .small-select {
  min-width: 44px;
  border-color: var(--border);
  background: #fff;
}

.series-pills span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--pill);
}

.interval {
  margin-left: auto;
  gap: 12px;
}

.interval label {
  color: var(--text-secondary);
  font-weight: 650;
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

.stat-card svg {
  width: 100%;
  height: 26px;
  margin-top: 10px;
}

.stat-meta {
  justify-content: space-between;
  margin-top: 6px;
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

.chart-actions {
  display: flex;
  gap: 8px;
}

.trend-chart {
  width: 100%;
  height: 316px;
}

.table-card h2 {
  margin-bottom: 14px;
}

.page-size {
  width: 88px;
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

  .date-range {
    min-width: 0;
    width: 100%;
    gap: 8px;
    font-size: 12px;
  }

  .date-tabs,
  .series-pills {
    overflow-x: auto;
  }

  .interval,
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
