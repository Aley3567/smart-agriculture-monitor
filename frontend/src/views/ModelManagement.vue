<script setup>
import { computed, onMounted } from 'vue'
import { useSensorStore } from '../stores/sensor'
import api from '../utils/api'
import {
  formatFieldValue,
  sourceMeta,
} from '../utils/sources'
import { formatTimeOnly } from '../utils/format'

const sensorStore = useSensorStore()

const latestTime = computed(() => {
  const ts = sensorStore.history.timestamps.at(-1)
  return ts ? formatTimeOnly(ts) : '—'
})

const modelOutputKeys = ['soil', 'co2', 'soil_ec', 'soil_tds', 'soil_fertility', 'infrared']

const statusCards = computed(() => [
  {
    icon: 'cube',
    label: '模型状态',
    value: '运行中',
    meta: '物理/经验公式驱动',
    tone: 'green',
  },
  {
    icon: 'clock',
    label: '状态恢复',
    value: latestTime.value === '—' ? '等待采样' : '来自最新记录',
    meta: latestTime.value,
    tone: 'blue',
  },
  {
    icon: 'wave',
    label: '真实输入',
    value: '3 项',
    meta: '温度、湿度、光照',
    tone: 'blue',
  },
  {
    icon: 'output',
    label: '推算输出',
    value: '6 项',
    meta: '由模型生成',
    tone: 'orange',
  },
])

const modelCards = [
  {
    index: 1,
    title: '土壤水量平衡模型',
    badge: '运行中',
    diagram: 'soil',
    formula: 'soil[t] = f(T, H, L, pump, Δt)',
    formulaNote: '土壤水量 = 蒸发损失 + 灌溉补水 + 时间衰减',
    desc: '用板端温湿度、光照、水泵状态和时间步长估算土壤含水量，强调水量变化过程，不把室外天气当成棚内主驱动。',
    params: [
      { label: '蒸发强度', value: 'ET ∝ T + L' },
      { label: '补水项', value: 'pump × flow' },
      { label: '时间步长', value: 'Δt' },
    ],
    inputs: [
      { label: '温度', source: 'measured' },
      { label: '湿度', source: 'measured' },
      { label: '光照', source: 'measured' },
      { label: '灌溉', source: 'control' },
      { label: '时间', source: 'system' },
    ],
    outputs: [{ label: '土壤湿度', source: 'simulated_backend' }],
  },
  {
    index: 2,
    title: 'CO2 质量守恒模型',
    badge: '运行中',
    diagram: 'co2',
    formula: 'CO2[t+Δt] = CO2[t] + G - R - V',
    formulaNote: 'CO2 变化 = 产生项 - 作物呼吸/光合作用 - 自然通风',
    desc: '根据光照、温度、时间段和自然通风系数估算棚内 CO2 浓度，表现温室内气体积累和消散关系。',
    params: [
      { label: '自然换气率', value: 'V' },
      { label: '光合作用', value: 'R(L)' },
      { label: '产生项', value: 'G' },
    ],
    inputs: [
      { label: '光照', source: 'measured' },
      { label: '温度', source: 'measured' },
      { label: '通风', source: 'system' },
      { label: '时间', source: 'system' },
    ],
    outputs: [{ label: 'CO2 浓度', source: 'simulated_backend' }],
  },
  {
    index: 3,
    title: 'EC / TDS / 肥力模型',
    badge: '运行中',
    diagram: 'ec',
    formula: 'TDS ≈ EC × 640',
    formulaNote: 'EC 为主状态，TDS 和肥力指数由 EC 与土壤湿度推导',
    desc: '以土壤 EC 为核心状态，结合水量、施肥量、温度和土壤湿度变化，推导 TDS 与土壤肥力指数。',
    params: [
      { label: '盐分浓度', value: 'EC' },
      { label: '稀释项', value: 'water' },
      { label: '肥力映射', value: 'normalize(EC)' },
    ],
    inputs: [
      { label: '灌溉EC', source: 'simulated_backend' },
      { label: '水量', source: 'simulated_backend' },
      { label: '施肥量', source: 'control' },
      { label: '温度', source: 'measured' },
      { label: '时间', source: 'system' },
    ],
    outputs: [
      { label: 'EC', source: 'computed_backend' },
      { label: 'TDS', source: 'computed_backend' },
      { label: '肥力', source: 'computed_backend' },
    ],
  },
  {
    index: 4,
    title: '红外事件模型',
    badge: '运行中',
    diagram: 'infrared',
    formula: 'infrared ∈ {0, 1}',
    formulaNote: 'PIR 事件按触发概率、保持时间和距离阈值判定',
    desc: '模拟 PIR 人体/活动检测事件，只用于告警和追溯，不把红外状态等同于灭虫灯开关状态。',
    params: [
      { label: '触发概率', value: 'P(event)' },
      { label: '保持时间', value: '10-45s' },
      { label: '输出状态', value: '0 / 1' },
    ],
    inputs: [
      { label: '红外原始', source: 'simulated_backend' },
      { label: '时间', source: 'system' },
      { label: '光照', source: 'measured' },
    ],
    outputs: [{ label: '红外状态', source: 'simulated_backend' }],
  },
]

const previewCards = computed(() => modelOutputKeys.map((key) => {
  const field = sensorStore.fieldFor(key)
  const available = field?.available
  const source = key === 'soil' ? 'simulated_backend' : (available ? field.source : 'pending')
  return {
    ...field,
    key,
    value: available ? formatFieldValue(field, sensorStore.current[key]) : '—',
    source: sourceMeta(source),
    danger: key === 'infrared',
    path: key === 'infrared'
      ? 'M0 26 L18 20 L36 24 L54 16 L72 30 L90 12 L108 22 L126 18'
      : 'M0 26 L18 18 L36 23 L54 15 L72 21 L90 13 L108 20 L126 12',
  }
}))

function badgeClass(source) {
  return sourceMeta(source).className
}

async function fetchLatestSamples() {
  const end = new Date()
  const start = new Date(end.getTime() - 24 * 3600 * 1000)
  try {
    const res = await api.get('/api/history', {
      params: { start: start.toISOString(), end: end.toISOString(), page: 1, page_size: 60 },
    })
    sensorStore.hydrateSamples([...res.data.items].reverse(), res.data.fields)
  } catch { /* keep websocket-derived state */ }
}

onMounted(fetchLatestSamples)
</script>

<template>
  <div class="model-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">模型管理</h1>
        <p class="page-subtitle">缺失传感器由后端模型补齐，模型基于物理/经验公式与历史数据生成有依据的估算值。</p>
      </div>
    </header>

    <section class="status-grid">
      <article v-for="item in statusCards" :key="item.label" class="status-card card" :class="`tone-${item.tone}`">
        <div class="status-icon" :class="`icon-${item.icon}`">
          <span v-if="item.icon === 'cube'"></span>
          <span v-else-if="item.icon === 'clock'"></span>
          <span v-else-if="item.icon === 'wave'"></span>
          <span v-else></span>
        </div>
        <div>
          <p>{{ item.label }}</p>
          <strong>{{ item.value }}</strong>
          <small>{{ item.meta }}</small>
        </div>
      </article>
    </section>

    <main class="model-grid">
      <section class="model-card card" v-for="item in modelCards" :key="item.index">
        <header class="model-head">
          <div class="title-row">
            <span class="model-index">{{ item.index }}</span>
            <h2>{{ item.title }}</h2>
            <b class="source-badge source-model">{{ item.badge }}</b>
          </div>
        </header>

        <div class="model-body">
          <div class="model-copy">
            <span class="eyebrow">核心公式</span>
            <div class="formula">
              <strong>{{ item.formula }}</strong>
              <small>{{ item.formulaNote }}</small>
            </div>
            <p>{{ item.desc }}</p>

            <div class="param-list">
              <div v-for="param in item.params" :key="param.label">
                <span>{{ param.label }}</span>
                <b>{{ param.value }}</b>
              </div>
            </div>
          </div>

          <div class="principle-figure" :class="`figure-${item.diagram}`" aria-hidden="true">
            <svg v-if="item.diagram === 'soil'" viewBox="0 0 280 160" role="img">
              <defs>
                <linearGradient id="soilCanopy" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stop-color="#46b36b" />
                  <stop offset="1" stop-color="#1f8d4a" />
                </linearGradient>
              </defs>
              <path class="arrow muted" d="M56 122 C48 92 52 68 66 42" />
              <path class="arrow blue" d="M218 122 C232 94 232 72 220 48" />
              <path class="arrow blue" d="M222 86 L250 76" />
              <text x="32" y="38">光照(L)</text>
              <text x="204" y="37">蒸散(ET)</text>
              <text x="226" y="72">降水(P)</text>
              <rect x="78" y="92" width="126" height="32" rx="4" fill="#8a5a2d" />
              <rect x="78" y="84" width="126" height="14" rx="4" fill="#4f8f4f" />
              <path d="M142 84 C132 66 128 48 130 34 C146 48 154 66 146 84 Z" fill="url(#soilCanopy)" />
              <path d="M144 84 C152 64 170 48 188 44 C184 66 166 80 144 84 Z" fill="#69c777" />
              <path d="M140 84 C130 60 106 50 90 50 C96 70 116 84 140 84 Z" fill="#72cf83" />
              <path class="root" d="M142 86 L142 126 M142 100 C126 104 120 114 112 126 M142 102 C158 106 166 116 174 128 M142 112 C134 118 132 124 128 132 M142 114 C152 120 156 128 160 136" />
              <text x="122" y="148">土壤水量</text>
            </svg>

            <svg v-else-if="item.diagram === 'co2'" viewBox="0 0 280 160" role="img">
              <path class="greenhouse" d="M54 124 L54 82 C92 28 188 28 226 82 L226 124 Z" />
              <path class="greenhouse-line" d="M54 82 L226 82 M140 38 L140 124" />
              <path class="arrow green" d="M92 118 L92 72" />
              <path class="arrow green" d="M140 118 L140 64" />
              <path class="arrow green" d="M188 118 L188 72" />
              <circle cx="140" cy="42" r="22" fill="#e9f7ee" stroke="#1f9d55" />
              <text x="126" y="38">CO2</text>
              <path d="M88 124 C88 104 102 100 112 124 M140 124 C140 100 154 94 166 124 M190 124 C190 104 202 99 212 124" class="plant-line" />
              <text x="70" y="146">产生 G</text>
              <text x="126" y="146">呼吸 R</text>
              <text x="186" y="146">通风 V</text>
            </svg>

            <svg v-else-if="item.diagram === 'ec'" viewBox="0 0 280 160" role="img">
              <text x="34" y="48">EC₀</text>
              <text x="78" y="48">+</text>
              <path class="drop" d="M116 34 C105 50 100 60 100 70 C100 82 108 90 120 90 C132 90 140 82 140 70 C140 60 131 50 120 34 Z" />
              <path class="flask" d="M184 34 L176 88 L214 88 L206 34 Z M178 70 L212 70" />
              <path class="arrow dark" d="M148 62 L170 62" />
              <path class="arrow dark" d="M224 62 L252 62" />
              <text x="92" y="116">水量稀释</text>
              <text x="166" y="116">施肥量</text>
              <text x="224" y="116">EC/TDS</text>
            </svg>

            <svg v-else viewBox="0 0 280 160" role="img">
              <path class="zone" d="M52 72 L168 28 L238 68 L120 118 Z" />
              <path class="zone-line" d="M52 72 L120 118 L238 68 M168 28 L120 118" />
              <circle cx="142" cy="84" r="11" fill="#0f8f47" />
              <path class="person" d="M142 96 L142 122 M142 104 L126 116 M142 104 L158 116 M142 122 L128 142 M142 122 L158 142" />
              <path class="sensor-rays" d="M168 56 C190 56 208 62 224 76 M168 66 C188 70 202 78 212 92" />
              <text x="174" y="50">PIR 探测区域</text>
            </svg>
          </div>
        </div>

        <div class="io-strip">
          <div>
            <span>核心输入</span>
            <ul>
              <li v-for="input in item.inputs" :key="input.label">
                <b class="source-badge" :class="badgeClass(input.source)">{{ input.label }}</b>
              </li>
            </ul>
          </div>
          <div>
            <span>核心输出</span>
            <ul>
              <li v-for="output in item.outputs" :key="output.label">
                <b class="source-badge" :class="badgeClass(output.source)">{{ output.label }}</b>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </main>

    <section class="card preview-panel">
      <header>
        <div>
          <h2 class="section-title">模型输出预览</h2>
          <p>当前由模型生成的估算值，用于链路验证、告警判断和历史分析。</p>
        </div>
        <b class="source-badge source-system">更新 {{ latestTime }}</b>
      </header>
      <div class="preview-grid">
        <article v-for="item in previewCards" :key="item.key" :class="{ danger: item.danger }">
          <div class="preview-icon">{{ item.key === 'co2' ? 'CO2' : item.key === 'soil_ec' ? 'EC' : item.key === 'infrared' ? 'IR' : '' }}</div>
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}<small v-if="item.available && item.unit">{{ item.unit }}</small></strong>
          <svg class="sparkline" viewBox="0 0 126 36" aria-hidden="true">
            <path :d="item.path" />
          </svg>
          <footer>
            <small>更新 {{ latestTime }}</small>
            <b class="source-badge" :class="item.source.className">{{ item.source.label }}</b>
          </footer>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.model-page {
  max-width: 1600px;
  margin: 0 auto;
}

.page-head {
  margin-bottom: 16px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.status-card {
  min-height: 108px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px;
}

.status-icon {
  width: 54px;
  height: 54px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #eef8f1;
  color: #159447;
  flex: 0 0 auto;
}

.tone-blue .status-icon {
  background: #eff6ff;
  color: #2563eb;
}

.tone-orange .status-icon {
  background: #fff7ed;
  color: #f97316;
}

.status-icon span {
  width: 26px;
  height: 26px;
  display: block;
  position: relative;
}

.icon-cube span {
  border: 3px solid currentColor;
  border-radius: 5px;
  transform: rotate(30deg);
}

.icon-clock span {
  border: 3px solid currentColor;
  border-radius: 50%;
}

.icon-clock span::before,
.icon-clock span::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 3px;
  background: currentColor;
  transform-origin: top;
}

.icon-clock span::before {
  height: 9px;
  transform: rotate(0deg);
}

.icon-clock span::after {
  height: 11px;
  transform: rotate(120deg);
}

.icon-wave span::before,
.icon-output span::before {
  content: '';
  position: absolute;
  inset: 4px 0;
  border: solid currentColor;
  border-width: 0 0 3px;
  transform: skewX(-22deg);
}

.icon-output span {
  border: 3px solid currentColor;
  border-radius: 4px;
}

.icon-output span::before {
  inset: 7px;
  border-width: 0 0 3px;
}

.status-card p {
  color: #64748b;
  font-weight: 750;
}

.status-card strong {
  display: block;
  margin-top: 4px;
  color: #0f8f47;
  font-size: 22px;
  line-height: 1.15;
}

.tone-blue strong {
  color: #2563eb;
}

.tone-orange strong {
  color: #f97316;
}

.status-card small {
  display: block;
  margin-top: 6px;
  color: #64748b;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.model-card {
  display: grid;
  gap: 14px;
  min-height: 280px;
  padding: 18px;
}

.model-head {
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.model-index {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #0aa344;
  color: #fff;
  font-weight: 850;
  flex: 0 0 auto;
}

.title-row h2 {
  min-width: 0;
  color: #17223b;
  font-size: 19px;
  line-height: 1.25;
}

.model-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 18px;
  align-items: center;
}

.model-copy {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.eyebrow,
.io-strip span {
  color: #475569;
  font-size: 13px;
  font-weight: 800;
}

.formula {
  display: grid;
  gap: 6px;
  min-height: 76px;
  padding: 12px 14px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
  background: linear-gradient(180deg, #fbfcfe 0%, #f8fafc 100%);
}

.formula strong {
  color: #17223b;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 18px;
  font-style: italic;
  line-height: 1.25;
}

.formula small,
.model-copy p {
  color: #64748b;
  line-height: 1.55;
}

.param-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.param-list div {
  display: grid;
  gap: 4px;
  min-height: 54px;
  padding: 9px 10px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
  background: #fff;
}

.param-list span {
  color: #64748b;
  font-size: 12px;
}

.param-list b {
  overflow: hidden;
  color: #17223b;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.principle-figure {
  min-height: 168px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-left: 1px solid var(--border-light);
  padding-left: 16px;
}

.principle-figure svg {
  width: 100%;
  max-width: 280px;
  height: auto;
  overflow: visible;
}

.principle-figure text {
  fill: #334155;
  font-size: 12px;
  font-weight: 700;
}

.arrow,
.greenhouse-line,
.root,
.plant-line,
.flask,
.person,
.sensor-rays,
.zone-line {
  fill: none;
  stroke: currentColor;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.arrow {
  marker-end: none;
}

.muted { color: #94a3b8; }
.blue { color: #318de6; }
.green { color: #159447; }
.dark { color: #334155; }

.root {
  color: #f3e6c9;
  stroke-width: 2.4;
}

.greenhouse {
  fill: rgba(232, 247, 238, 0.72);
  stroke: #9acfb0;
  stroke-width: 3;
}

.greenhouse-line {
  color: #9acfb0;
  stroke-width: 2;
}

.plant-line {
  color: #159447;
}

.drop {
  fill: #e9f4ff;
  stroke: #318de6;
  stroke-width: 3;
}

.flask {
  color: #159447;
}

.zone {
  fill: rgba(33, 157, 85, 0.13);
  stroke: #b7d8c4;
  stroke-width: 2;
}

.zone-line {
  color: #b7d8c4;
  stroke-width: 2;
}

.person,
.sensor-rays {
  color: #0f8f47;
}

.io-strip {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.85fr);
  gap: 14px;
  padding-top: 4px;
}

.io-strip div {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.io-strip ul {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  list-style: none;
}

.preview-panel {
  margin-top: 16px;
  padding: 18px;
}

.preview-panel header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.preview-panel header p {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.preview-grid article {
  display: grid;
  gap: 7px;
  min-height: 168px;
  padding: 16px 12px 12px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
  background: linear-gradient(180deg, #fff 0%, #fbfdfb 100%);
  min-width: 0;
}

.preview-grid article.danger {
  background: linear-gradient(180deg, #fff 0%, #fffafa 100%);
}

.preview-icon {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #eaf5ee;
  color: #0f8f47;
  font-size: 12px;
  font-weight: 850;
}

.preview-grid article:nth-child(1) .preview-icon::before,
.preview-grid article:nth-child(4) .preview-icon::before {
  content: '';
  width: 14px;
  height: 22px;
  border: 3px solid currentColor;
  border-radius: 14px 14px 14px 2px;
  transform: rotate(45deg);
}

.preview-grid article:nth-child(5) .preview-icon::before {
  content: '';
  width: 24px;
  height: 24px;
  background:
    radial-gradient(circle at 50% 76%, currentColor 0 3px, transparent 4px),
    linear-gradient(currentColor, currentColor) 50% 48% / 4px 18px no-repeat,
    radial-gradient(ellipse at 34% 36%, currentColor 0 8px, transparent 9px),
    radial-gradient(ellipse at 66% 36%, currentColor 0 8px, transparent 9px);
}

.danger .preview-icon {
  background: #fff1f2;
  color: #dc2626;
}

.preview-grid span {
  overflow: hidden;
  color: #334155;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-grid strong {
  color: #16a34a;
  font-size: 26px;
  line-height: 1;
}

.danger strong {
  color: #dc2626;
}

.preview-grid small {
  margin-left: 4px;
  color: #64748b;
  font-size: 12px;
}

.sparkline {
  width: 100%;
  height: 36px;
}

.sparkline path {
  fill: none;
  stroke: #159447;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.danger .sparkline path {
  stroke: #ef4444;
}

.preview-grid footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: auto;
}

.preview-grid footer small {
  margin: 0;
  white-space: nowrap;
}

@media (max-width: 1380px) {
  .model-body {
    grid-template-columns: 1fr;
  }

  .principle-figure {
    border-left: 0;
    border-top: 1px solid var(--border-light);
    padding: 14px 0 0;
  }

  .preview-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1100px) {
  .status-grid,
  .model-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .status-grid,
  .model-grid,
  .preview-grid,
  .io-strip,
  .param-list {
    grid-template-columns: 1fr;
  }

  .preview-panel header,
  .title-row {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .model-card {
    min-height: 0;
  }
}
</style>
