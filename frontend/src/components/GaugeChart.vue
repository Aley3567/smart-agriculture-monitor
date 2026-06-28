<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { GaugeChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'

use([GaugeChart, CanvasRenderer])

const props = defineProps({
  title: { type: String, required: true },
  value: { type: Number, default: 0 },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  unit: { type: String, default: '' },
  color: { type: String, default: '#00d4ff' },
})

const option = computed(() => ({
  series: [
    {
      type: 'gauge',
      min: props.min,
      max: props.max,
      progress: { show: true, width: 12 },
      axisLine: {
        lineStyle: { width: 12, color: [[1, '#2a3a5a']] },
      },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      pointer: {
        length: '60%',
        width: 4,
        itemStyle: { color: props.color },
      },
      anchor: {
        show: true,
        size: 10,
        itemStyle: { color: props.color },
      },
      title: {
        fontSize: 14,
        color: '#8899aa',
        offsetCenter: [0, '70%'],
      },
      detail: {
        fontSize: 22,
        fontWeight: 700,
        color: props.color,
        offsetCenter: [0, '45%'],
        formatter: `{value} ${props.unit}`,
      },
      itemStyle: { color: props.color },
      data: [{ value: props.value, name: props.title }],
    },
  ],
}))
</script>

<template>
  <v-chart :option="option" autoresize style="width: 100%; height: 200px;" />
</template>
