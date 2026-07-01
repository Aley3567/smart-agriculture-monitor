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

const modelCards = [
  {
    index: 1,
    title: '土壤水量平衡模型',
    badge: '运行口径',
    formula: 'soil[t] = f(T, H, L, pump, Δt)',
    desc: '由真实温度、真实空气湿度、光照、水泵状态和时间步长驱动，不把天气 API 当作棚内土壤湿度主驱动。',
    inputs: ['温度', '湿度', '光照', '灌溉', '时间'],
    outputs: ['土壤湿度'],
    available: true,
  },
  {
    index: 2,
    title: 'CO2 质量守恒模型',
    badge: '待后端字段',
    formula: 'CO2[t+Δt] = CO2[t] + G - R - V',
    desc: '依赖光照、温度、红外事件、时间段和固定自然通风系数；不绑定第三路执行器。',
    inputs: ['光照', '温度', '红外事件', '时间'],
    outputs: ['CO2浓度'],
    available: false,
  },
  {
    index: 3,
    title: 'EC / TDS / 肥力模型',
    badge: '待后端字段',
    formula: 'TDS ≈ EC × 640',
    desc: '内部维护 soil_ec 主状态，并由水量、施肥量、温度、土壤湿度共同影响 EC，再推导 TDS 和肥力指数。',
    inputs: ['灌溉EC', '水量', '施肥量', '温度', '时间'],
    outputs: ['EC', 'TDS', '肥力'],
    available: false,
  },
  {
    index: 4,
    title: '红外事件模型',
    badge: '待后端字段',
    formula: 'infrared ∈ {0, 1}',
    desc: '按 PIR 人体/活动检测事件处理，只用于告警与追溯，不把红外状态等同于灭虫灯状态。',
    inputs: ['红外原始事件', '时间'],
    outputs: ['红外状态'],
    available: false,
  },
]

const sourceRows = computed(() => [
  ...Object.values(sensorStore.fields).map(field => ({
    input: field.key,
    label: field.label,
    source: field.source,
    use: field.available ? field.detail : '字段待接入',
  })),
  { input: 'weather', label: 'weather', source: 'api', use: '辅助参考，不直接控制' },
])

const previewCards = computed(() => sensorStore.modelFieldKeys.map((key) => {
  const field = sensorStore.fieldFor(key)
  const available = field.available
  return {
    ...field,
    value: available ? formatFieldValue(field, sensorStore.current[key]) : '—',
    source: sourceMeta(available ? field.source : 'pending'),
  }
}))

function sourceFor(row) {
  return sourceMeta(row.source)
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
        <p class="page-subtitle">说明后端模型口径、来源映射与当前输出接入状态</p>
      </div>
    </header>

    <div class="model-layout">
      <main class="model-main">
        <section class="model-card card" v-for="item in modelCards" :key="item.index">
          <div class="model-index">{{ item.index }}</div>
          <div class="model-copy">
            <header>
              <h2>{{ item.title }}</h2>
              <b class="source-badge" :class="item.available ? 'source-model' : 'source-pending'">{{ item.badge }}</b>
            </header>
            <div class="formula">{{ item.formula }}</div>
            <p>{{ item.desc }}</p>
            <div class="io-row">
              <div>
                <span>核心输入</span>
                <ul><li v-for="input in item.inputs" :key="input">{{ input }}</li></ul>
              </div>
              <div>
                <span>核心输出</span>
                <ul><li v-for="output in item.outputs" :key="output">{{ output }}</li></ul>
              </div>
            </div>
          </div>
        </section>

        <section class="card preview-panel">
          <h2 class="section-title">模型输出预览</h2>
          <div class="preview-grid">
            <article v-for="item in previewCards" :key="item.key">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}<small v-if="item.available && item.unit">{{ item.unit }}</small></strong>
              <b class="source-badge" :class="item.source.className">{{ item.source.label }}</b>
            </article>
          </div>
          <p>说明：预览只读取当前前端已收到的字段；后端未提供的模型输出显示为待接入。</p>
        </section>
      </main>

      <aside class="model-side">
        <section class="card source-panel">
          <h2 class="section-title">来源映射表</h2>
          <table class="source-table">
            <thead><tr><th>字段</th><th>来源</th><th>用途</th></tr></thead>
            <tbody>
              <tr v-for="row in sourceRows" :key="row.input">
                <td>{{ row.label || row.input }}</td>
                <td><b class="source-badge" :class="sourceFor(row).className">{{ sourceFor(row).label }}</b></td>
                <td>{{ row.use }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="card param-panel">
          <h2 class="section-title">模型参数与版本</h2>
          <dl>
            <div><dt>模型版本</dt><dd>前端展示口径 v1</dd></div>
            <div><dt>数据更新周期</dt><dd>随 WebSocket 采样</dd></div>
            <div><dt>模型更新时间</dt><dd>{{ latestTime }}</dd></div>
            <div><dt>参数校准方式</dt><dd>后端完整模型接入后配置</dd></div>
          </dl>
        </section>
      </aside>
    </div>
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

.model-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
}

.model-main,
.model-side {
  display: grid;
  gap: 16px;
  align-content: start;
  min-width: 0;
}

.model-main {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.model-card {
  display: flex;
  gap: 16px;
  min-height: 248px;
  padding: 18px;
}

.model-index {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #0aa344;
  color: #fff;
  font-size: 18px;
  font-weight: 850;
  flex: 0 0 auto;
}

.model-copy {
  display: grid;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.model-copy header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.model-copy h2 {
  font-size: 18px;
  line-height: 1.25;
}

.formula {
  min-height: 52px;
  display: flex;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
  background: #f8fafc;
  color: #17223b;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 18px;
  font-style: italic;
}

.model-copy p {
  color: #475569;
  line-height: 1.65;
}

.io-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: auto;
}

.io-row div {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
}

.io-row span {
  color: #64748b;
  font-weight: 750;
}

.io-row ul {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  list-style: none;
}

.io-row li {
  padding: 4px 8px;
  border-radius: 5px;
  background: #f0fdf4;
  color: #15803d;
  font-size: 12px;
  font-weight: 750;
}

.preview-panel {
  grid-column: 1 / -1;
  padding: 18px;
}

.preview-panel h2 {
  margin-bottom: 14px;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.preview-grid article {
  display: grid;
  justify-items: center;
  gap: 8px;
  min-height: 118px;
  padding: 16px 10px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
  text-align: center;
}

.preview-grid span {
  color: #334155;
  font-weight: 750;
}

.preview-grid strong {
  color: #16a34a;
  font-size: 24px;
  line-height: 1;
}

.preview-grid small {
  margin-left: 4px;
  color: #64748b;
  font-size: 12px;
}

.preview-panel p {
  margin-top: 12px;
  color: #64748b;
  font-size: 13px;
}

.source-panel,
.param-panel {
  padding: 18px;
}

.source-panel h2,
.param-panel h2 {
  margin-bottom: 14px;
}

.source-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.source-table th,
.source-table td {
  height: 42px;
  padding: 0 10px;
  border: 1px solid var(--border-light);
  text-align: left;
}

.source-table th {
  background: #f8fafc;
  color: #64748b;
}

.param-panel dl {
  display: grid;
  gap: 12px;
}

.param-panel dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-light);
}

.param-panel dl div:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.param-panel dt {
  color: #64748b;
}

.param-panel dd {
  color: #17223b;
  font-weight: 750;
  text-align: right;
}

@media (max-width: 1300px) {
  .model-layout,
  .model-main {
    grid-template-columns: 1fr;
  }

  .preview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .preview-grid,
  .io-row {
    grid-template-columns: 1fr;
  }

  .model-card {
    flex-direction: column;
  }
}
</style>
