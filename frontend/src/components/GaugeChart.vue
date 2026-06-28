<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: Number, default: 0 },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  unit: { type: String, default: '' },
  color: { type: String, default: '#4a7c59' },
  trackColor: { type: String, default: '#e8f0ea' },
})

const emit = defineEmits(['click'])

const CX = 100, CY = 88, R = 62
const START = 150, SPAN = 240
const CIRC = 2 * Math.PI * R
const ARC = CIRC * SPAN / 360

const ratio = computed(() => {
  const range = props.max - props.min || 1
  return Math.max(0, Math.min(1, (props.value - props.min) / range))
})

const fillDash = computed(() => `${ratio.value * ARC} ${CIRC - ratio.value * ARC}`)
const trackDash = `${ARC} ${CIRC - ARC}`

const TICK_N = 20
const ticks = computed(() => {
  const out = []
  for (let i = 0; i <= TICK_N; i++) {
    const f = i / TICK_N
    const rad = (START + f * SPAN) * Math.PI / 180
    const c = Math.cos(rad), s = Math.sin(rad)
    const major = i % 5 === 0
    const inner = R - (major ? 11 : 7)
    out.push({
      x1: CX + inner * c, y1: CY + inner * s,
      x2: CX + (R - 3) * c, y2: CY + (R - 3) * s,
      major,
    })
  }
  return out
})

const endpointLabel = (frac) => {
  const rad = (START + frac * SPAN) * Math.PI / 180
  return { x: CX + (R + 15) * Math.cos(rad), y: CY + (R + 15) * Math.sin(rad) }
}
const minPos = endpointLabel(0)
const maxPos = endpointLabel(1)

const dotPos = computed(() => {
  const rad = (START + ratio.value * SPAN) * Math.PI / 180
  return { x: CX + R * Math.cos(rad), y: CY + R * Math.sin(rad) }
})

const display = computed(() => {
  if (props.value >= 1000) return props.value.toFixed(0)
  if (Number.isInteger(props.value)) return String(props.value)
  return props.value.toFixed(1)
})

const pct = computed(() => Math.round(ratio.value * 100))
</script>

<template>
  <div class="gauge" @click="emit('click')" role="button" tabindex="0">
    <svg viewBox="0 0 200 168" class="gauge-svg">
      <line v-for="(t, i) in ticks" :key="i"
        :x1="t.x1" :y1="t.y1" :x2="t.x2" :y2="t.y2"
        :stroke="t.major ? '#bfb7ac' : '#dcd6cc'" :stroke-width="t.major ? 1.5 : 0.8"
        stroke-linecap="round"/>

      <circle :cx="CX" :cy="CY" :r="R" fill="none" :stroke="trackColor"
        stroke-width="7" :stroke-dasharray="trackDash" stroke-linecap="round"
        :transform="`rotate(${START} ${CX} ${CY})`"/>

      <circle :cx="CX" :cy="CY" :r="R" fill="none" :stroke="color"
        stroke-width="7" :stroke-dasharray="fillDash" stroke-linecap="round"
        :transform="`rotate(${START} ${CX} ${CY})`" class="fill-arc"/>

      <circle v-if="ratio > 0.02"
        :cx="dotPos.x" :cy="dotPos.y" r="5" :fill="color" class="dot"/>

      <text :x="CX" :y="CY - 4" text-anchor="middle" class="val">{{ display }}</text>
      <text :x="CX" :y="CY + 14" text-anchor="middle" class="unit">{{ unit }}</text>

      <text :x="minPos.x" :y="minPos.y" text-anchor="middle" class="range">{{ min }}</text>
      <text :x="maxPos.x" :y="maxPos.y" text-anchor="middle" class="range">{{ max }}</text>
    </svg>

    <div class="foot">
      <span class="lbl">{{ label }}</span>
      <span class="pct" :style="{ color }">{{ pct }}%</span>
    </div>
  </div>
</template>

<style scoped>
.gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  padding: 20px 16px 16px;
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  border: 1px solid var(--border-light);
  transition: transform 0.2s var(--ease-out), box-shadow 0.2s, border-color 0.2s;
}
.gauge:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
  border-color: var(--border);
}
.gauge:active { transform: translateY(-1px) scale(0.99); }

.gauge-svg { width: 170px; height: 143px; }

.fill-arc {
  transition: stroke-dasharray 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.dot {
  transition: cx 0.8s cubic-bezier(0.16, 1, 0.3, 1),
              cy 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.gauge:hover .dot {
  filter: drop-shadow(0 0 4px currentColor);
}

.val {
  font-family: var(--font-display);
  font-size: 28px;
  fill: var(--text-primary);
}
.unit {
  font-family: var(--font-body);
  font-size: 12px;
  fill: var(--text-muted);
}
.range {
  font-family: var(--font-mono);
  font-size: 9px;
  fill: var(--text-muted);
}

.foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin-top: 6px;
  padding: 0 4px;
}
.lbl {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}
.pct {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
}
</style>
