<script setup>
import { ref, computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { formatShortDate } from '../utils/format'
import { usePaginatedFetch } from '../composables/usePaginatedFetch'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const { dateRange, tableData, total, currentPage, pageSize, loading, fetch: fetchData, handlePageChange } =
  usePaginatedFetch('http://localhost:8000/api/history')
const chartData = ref([])

const selectedSeries = ref(['temp', 'humi', 'light', 'soil'])
const seriesOptions = [
  { label: '温度', value: 'temp' },
  { label: '湿度', value: 'humi' },
  { label: '光照', value: 'light' },
  { label: '土壤湿度', value: 'soil' },
]

const SERIES_CONFIG = {
  temp: { name: '温度', color: '#f56c6c' },
  humi: { name: '湿度', color: '#409eff' },
  light: { name: '光照', color: '#e6a23c' },
  soil: { name: '土壤湿度', color: '#67c23a' },
}

const _baseFetch = fetchData
async function fetchDataWithChart() {
  const result = await _baseFetch()
  if (result) chartData.value = result.items
}

const chartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#1a2a4a',
    borderColor: '#2a3a5a',
    textStyle: { color: '#e0e6ed' },
  },
  legend: {
    data: selectedSeries.value.map(k => SERIES_CONFIG[k].name),
    textStyle: { color: '#8899aa' },
    top: 0,
  },
  grid: { left: 50, right: 20, top: 40, bottom: 30 },
  xAxis: {
    type: 'category',
    data: chartData.value.map(d => formatShortDate(d.timestamp)),
    axisLine: { lineStyle: { color: '#2a3a5a' } },
    axisLabel: { color: '#8899aa', fontSize: 10, rotate: 30 },
    boundaryGap: false,
  },
  yAxis: {
    type: 'value',
    axisLine: { lineStyle: { color: '#2a3a5a' } },
    axisLabel: { color: '#8899aa' },
    splitLine: { lineStyle: { color: '#1a2a4a' } },
  },
  series: selectedSeries.value.map(key => ({
    name: SERIES_CONFIG[key].name,
    type: 'line',
    data: chartData.value.map(d => d[key]),
    smooth: true,
    showSymbol: false,
    lineStyle: { color: SERIES_CONFIG[key].color },
    itemStyle: { color: SERIES_CONFIG[key].color },
  })),
}))
</script>

<template>
  <div class="history-page">
    <el-card class="filter-card">
      <div class="filter-row">
        <el-date-picker
          v-model="dateRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          @change="fetchDataWithChart"
        />
        <el-checkbox-group v-model="selectedSeries" class="series-check">
          <el-checkbox v-for="s in seriesOptions" :key="s.value" :label="s.value">{{ s.label }}</el-checkbox>
        </el-checkbox-group>
        <el-button type="primary" @click="fetchDataWithChart" :loading="loading">查询</el-button>
      </div>
    </el-card>

    <el-card v-if="chartData.length" class="chart-card">
      <template #header><span class="card-title">历史趋势</span></template>
      <v-chart :option="chartOption" autoresize style="width: 100%; height: 350px;" />
    </el-card>

    <el-card class="table-card">
      <template #header><span class="card-title">数据记录</span></template>
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">{{ formatShortDate(row.timestamp) }}</template>
        </el-table-column>
        <el-table-column prop="temp" label="温度(°C)" width="120" />
        <el-table-column prop="humi" label="湿度(%)" width="120" />
        <el-table-column prop="light" label="光照(lux)" width="120" />
        <el-table-column prop="soil" label="土壤湿度(%)" width="140" />
      </el-table>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.series-check {
  display: flex;
  gap: 8px;
}

.series-check .el-checkbox {
  color: var(--text-primary);
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
