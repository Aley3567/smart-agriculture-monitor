<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useSensorStore } from '../stores/sensor'
import { useSystemStore } from '../stores/system'
import api from '../utils/api'
import { DEFAULT_BOARD_ID } from '../utils/constants'
import { formatDateTimeMinute } from '../utils/format'
import { showToast } from '../utils/toast'
import { formatFieldValue, sourceMeta } from '../utils/sources'

const sensorStore = useSensorStore()
const systemStore = useSystemStore()

const loading = ref(false)
const submitting = ref('')
const autoAllowControl = ref(true)

const form = reactive({
  board_id: systemStore.currentBoardId || DEFAULT_BOARD_ID,
  temperature: 24,
  humidity: 60,
  light: 50,
})

const latestSource = computed(() => sourceMeta(sensorStore.currentMeta.source || 'system'))
const latestTime = computed(() => sensorStore.currentMeta.timestamp ? formatDateTimeMinute(sensorStore.currentMeta.timestamp) : '—')

const sensorCards = computed(() => [
  { key: 'temp', label: '温度', model: 'temperature', unit: '°C' },
  { key: 'humi', label: '空气湿度', model: 'humidity', unit: '%' },
  { key: 'light', label: '相对光照', model: 'light', unit: '相对值' },
].map((item) => {
  const field = sensorStore.fieldFor(item.key)
  return {
    ...item,
    current: formatFieldValue(field, sensorStore.current[item.key]),
    available: field?.available !== false,
    source: sourceMeta(field?.source),
  }
}))

function valueOrFallback(value, fallback) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : fallback
}

function fillFromCurrent() {
  form.board_id = sensorStore.currentMeta.board_id || systemStore.currentBoardId || DEFAULT_BOARD_ID
  form.temperature = valueOrFallback(sensorStore.current.temp, form.temperature)
  form.humidity = valueOrFallback(sensorStore.current.humi, form.humidity)
  form.light = valueOrFallback(sensorStore.current.light, form.light)
}

function normalizePayload(allowControl) {
  return {
    board_id: form.board_id || DEFAULT_BOARD_ID,
    temperature: Number(form.temperature),
    humidity: Number(form.humidity),
    light: Number(form.light),
    allow_control: Boolean(allowControl),
  }
}

function isPayloadValid(payload) {
  return ['temperature', 'humidity', 'light'].every(key => Number.isFinite(payload[key]))
}

async function fetchLatestSample() {
  loading.value = true
  const end = new Date()
  const start = new Date(end.getTime() - 24 * 3600 * 1000)
  try {
    const res = await api.get('/api/history', {
      params: {
        board_id: form.board_id || DEFAULT_BOARD_ID,
        start: start.toISOString(),
        end: end.toISOString(),
        page: 1,
        page_size: 1,
      },
    })
    const latest = Array.isArray(res.data?.items) ? res.data.items[0] : null
    if (latest) {
      sensorStore.hydrateSamples([latest], res.data.fields)
    }
    fillFromCurrent()
  } catch {
    fillFromCurrent()
  } finally {
    loading.value = false
  }
}

async function submitSample(kind) {
  const allowControl = kind === 'auto' ? autoAllowControl.value : false
  const payload = normalizePayload(allowControl)
  if (!isPayloadValid(payload)) {
    showToast({ title: '提交失败', message: '请填写完整的数值样本', type: 'warn' })
    return
  }

  submitting.value = kind
  try {
    const res = await api.post('/api/test/sensor-sample', payload)
    const sample = res.data || {}
    sensorStore.updateSensorData(
      {
        temp: sample.temp,
        humi: sample.humi,
        light: sample.light,
        soil: sample.soil,
      },
      sample.timestamp,
      sample.facts,
      null,
      sample,
    )
    fillFromCurrent()
    const status = await api.get('/api/status')
    systemStore.updateStatus(status.data || {})
    showToast({
      title: '测试样本已提交',
      message: kind === 'auto' && allowControl ? '已允许自动浇水规则参与本次测试' : '已写入测试样本，不触发自动控制',
      type: 'success',
    })
  } catch {
    showToast({ title: '提交失败', message: '后端测试接口暂不可用', type: 'warn' })
  } finally {
    submitting.value = ''
  }
}

onMounted(fetchLatestSample)
</script>

<template>
  <div class="test-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">测试模式</h1>
        <p class="page-subtitle">向后端写入一条带测试标记的完整样本，用于演示告警、趋势和自动浇水规则</p>
      </div>
      <button class="btn btn-soft" type="button" @click="fetchLatestSample">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M16.2 10a6.2 6.2 0 1 1-1.8-4.4"/><path d="M16.2 4v4h-4"/></svg>
        {{ loading ? '读取中' : '使用最新值' }}
      </button>
    </header>

    <section class="card latest-panel">
      <div>
        <span>当前板卡</span>
        <strong>{{ form.board_id }}</strong>
      </div>
      <div>
        <span>最新样本</span>
        <strong>{{ latestTime }}</strong>
      </div>
      <div>
        <span>来源</span>
        <strong><b class="source-badge" :class="latestSource.className">{{ sensorStore.currentMeta.is_test ? '测试注入' : latestSource.label }}</b></strong>
      </div>
    </section>

    <main class="test-grid">
      <section class="card form-panel">
        <div class="panel-head">
          <h2 class="section-title">样本值</h2>
          <span>提交字段：temperature / humidity / light（soil 由模型计算）</span>
        </div>

        <div class="sample-grid">
          <article v-for="item in sensorCards" :key="item.key" class="sample-field">
            <header>
              <strong>{{ item.label }}</strong>
              <b class="source-badge" :class="item.available ? item.source.className : 'source-pending'">{{ item.available ? '可用' : '待接入' }}</b>
            </header>
            <label>
              <input v-model.number="form[item.model]" type="number" step="0.1">
              <small>{{ item.unit }}</small>
            </label>
            <p>当前值 {{ item.current }}{{ item.unit }}</p>
          </article>
        </div>
      </section>

      <aside class="action-stack">
        <section class="card action-card">
          <h2 class="section-title">普通测试注入</h2>
          <p>写入测试样本并广播到 Dashboard，默认不允许自动控制。</p>
          <button class="btn btn-primary" type="button" :disabled="Boolean(submitting)" @click="submitSample('normal')">
            {{ submitting === 'normal' ? '提交中' : '提交测试样本' }}
          </button>
        </section>

        <section class="card action-card auto-card">
          <h2 class="section-title">自动浇水测试</h2>
          <p>用于验证低土壤湿度时的自动浇水规则、冷却和控制日志。</p>
          <label class="check-row">
            <input v-model="autoAllowControl" type="checkbox">
            <span>允许本次样本触发自动控制</span>
          </label>
          <button class="btn btn-primary" type="button" :disabled="Boolean(submitting)" @click="submitSample('auto')">
            {{ submitting === 'auto' ? '提交中' : '提交并验证规则' }}
          </button>
        </section>
      </aside>
    </main>
  </div>
</template>

<style scoped>
.test-page {
  max-width: 1600px;
  margin: 0 auto;
}

.page-head,
.latest-panel,
.panel-head,
.sample-field header,
.sample-field label,
.check-row {
  display: flex;
  align-items: center;
}

.page-head {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.latest-panel {
  gap: 14px;
  justify-content: space-between;
  padding: 14px 16px;
  margin-bottom: 16px;
}

.latest-panel div {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.latest-panel span,
.panel-head span,
.sample-field p,
.action-card p {
  color: #64748b;
  font-size: 13px;
}

.latest-panel strong {
  color: #0f172a;
  font-size: 15px;
}

.test-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
  align-items: start;
}

.form-panel,
.action-card {
  padding: 18px;
}

.panel-head {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.sample-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.sample-field {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: #fff;
}

.sample-field header {
  justify-content: space-between;
  gap: 10px;
}

.sample-field label {
  height: 42px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: #fff;
  overflow: hidden;
}

.sample-field input {
  width: 100%;
  height: 100%;
  border: 0;
  padding: 0 12px;
  color: #0f172a;
  outline: none;
}

.sample-field small {
  min-width: 58px;
  padding-right: 12px;
  color: #64748b;
  text-align: right;
}

.action-stack {
  display: grid;
  gap: 14px;
}

.action-card {
  display: grid;
  gap: 12px;
}

.action-card .btn {
  width: 100%;
}

.auto-card {
  border-color: #bbf7d0;
}

.check-row {
  gap: 9px;
  min-height: 36px;
  color: #334155;
  font-weight: 650;
}

.check-row input {
  width: 16px;
  height: 16px;
  accent-color: var(--green-deep);
}

@media (max-width: 980px) {
  .test-grid,
  .sample-grid {
    grid-template-columns: 1fr;
  }

  .page-head,
  .latest-panel,
  .panel-head {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
