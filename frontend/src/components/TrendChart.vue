<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { formatTimeOnly } from '../utils/format'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps({
  timestamps: { type: Array, default: () => [] },
  tempData: { type: Array, default: () => [] },
  humiData: { type: Array, default: () => [] },
  lightData: { type: Array, default: () => [] },
  soilData: { type: Array, default: () => [] },
})

const SERIES = [
  { key: 'temp', name: '温度', color: '#a63d2f', data: () => props.tempData },
  { key: 'humi', name: '湿度', color: '#5b7f95', data: () => props.humiData },
  { key: 'light', name: '光照', color: '#c7853b', data: () => props.lightData },
  { key: 'soil', name: '土壤湿度', color: '#8b6f47', data: () => props.soilData },
]

const option = computed(() => ({
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#fff',
    borderColor: '#e5e0d8',
    borderWidth: 1,
    textStyle: { color: '#2c2c2c', fontSize: 12, fontFamily: 'DM Sans' },
    extraCssText: 'box-shadow: 0 4px 12px rgba(44,62,45,0.1); border-radius: 8px;',
  },
  legend: {
    data: SERIES.map(s => s.name),
    top: 0,
    left: 0,
    textStyle: { color: '#6b6b6b', fontSize: 12, fontFamily: 'DM Sans' },
    icon: 'roundRect',
    itemWidth: 12,
    itemHeight: 3,
    itemGap: 20,
  },
  grid: { left: 48, right: 16, top: 36, bottom: 28 },
  xAxis: {
    type: 'category',
    data: props.timestamps.map(formatTimeOnly),
    axisLine: { lineStyle: { color: '#e5e0d8' } },
    axisLabel: { color: '#a0a0a0', fontSize: 10, fontFamily: 'JetBrains Mono' },
    axisTick: { show: false },
    boundaryGap: false,
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    axisLabel: { color: '#a0a0a0', fontSize: 10, fontFamily: 'JetBrains Mono' },
    splitLine: { lineStyle: { color: '#f0ece4', type: 'dashed' } },
  },
  series: SERIES.map(s => ({
    name: s.name,
    type: 'line',
    data: s.data(),
    smooth: 0.4,
    showSymbol: false,
    lineStyle: { color: s.color, width: 2 },
    itemStyle: { color: s.color },
    areaStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: s.color + '18' },
          { offset: 1, color: s.color + '02' },
        ],
      },
    },
  })),
}))
</script>

<template>
  <v-chart :option="option" autoresize style="width: 100%; height: 280px;" />
</template>
