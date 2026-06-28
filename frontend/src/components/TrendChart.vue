<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  timestamps: { type: Array, default: () => [] },
  tempData: { type: Array, default: () => [] },
  humiData: { type: Array, default: () => [] },
  lightData: { type: Array, default: () => [] },
  soilData: { type: Array, default: () => [] },
})

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

const option = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#1a2a4a',
    borderColor: '#2a3a5a',
    textStyle: { color: '#e0e6ed' },
  },
  legend: {
    data: ['温度', '湿度', '光照', '土壤湿度'],
    textStyle: { color: '#8899aa' },
    top: 0,
  },
  grid: {
    left: 50,
    right: 20,
    top: 40,
    bottom: 30,
  },
  xAxis: {
    type: 'category',
    data: props.timestamps.map(formatTime),
    axisLine: { lineStyle: { color: '#2a3a5a' } },
    axisLabel: { color: '#8899aa', fontSize: 10 },
    boundaryGap: false,
  },
  yAxis: {
    type: 'value',
    axisLine: { lineStyle: { color: '#2a3a5a' } },
    axisLabel: { color: '#8899aa' },
    splitLine: { lineStyle: { color: '#1a2a4a' } },
  },
  series: [
    {
      name: '温度',
      type: 'line',
      data: props.tempData,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#f56c6c' },
      itemStyle: { color: '#f56c6c' },
    },
    {
      name: '湿度',
      type: 'line',
      data: props.humiData,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#409eff' },
      itemStyle: { color: '#409eff' },
    },
    {
      name: '光照',
      type: 'line',
      data: props.lightData,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#e6a23c' },
      itemStyle: { color: '#e6a23c' },
    },
    {
      name: '土壤湿度',
      type: 'line',
      data: props.soilData,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#67c23a' },
      itemStyle: { color: '#67c23a' },
    },
  ],
}))
</script>

<template>
  <v-chart :option="option" autoresize style="width: 100%; height: 300px;" />
</template>
