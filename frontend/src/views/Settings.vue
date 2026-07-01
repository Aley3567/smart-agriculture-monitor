<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../utils/api'
import { useSystemStore } from '../stores/system'
import { DEFAULT_BOARD_ID } from '../utils/constants'
import { showToast } from '../utils/toast'
import { DEVICE_MAPPINGS, DEVICE_META, sourceMeta } from '../utils/sources'

const systemStore = useSystemStore()
const saving = ref(false)
const ruleSaving = ref(false)

const autoRule = ref({
  enabled: true,
  start_below: 30,
  stop_at_or_above: 45,
  consecutive_samples: 2,
  max_run_sec: 60,
  cooldown_sec: 180,
})

const thresholds = ref({
  temperature: { min: 15, max: 35 },
  humidity: { min: 30, max: 85 },
  light: { min: 10, max: 90 },
  soil_moisture: { min: 30, max: 70 },
  co2: { min: null, max: 1000 },
  soil_ec: { min: 0.5, max: 2.0 },
  soil_tds: { min: 0, max: 1000 },
  soil_fertility: { min: 30, max: 100 },
  infrared: { min: 0, max: 1 },
})

const measuredThresholds = [
  { key: 'temperature', label: '温度', unit: '°C', minLabel: '最小值', maxLabel: '最大值', floor: -20, ceiling: 50, source: 'measured', editable: true, color: '#ef4444' },
  { key: 'humidity', label: '空气湿度', unit: '%', minLabel: '最小值', maxLabel: '最大值', floor: 0, ceiling: 100, source: 'measured', editable: true, color: '#2563eb' },
  { key: 'light', label: '相对光照', unit: '相对值', minLabel: '最小值', maxLabel: '最大值', floor: 0, ceiling: 100, source: 'measured', editable: true, color: '#f97316' },
]

const modelThresholds = [
  { key: 'soil_moisture', label: '土壤湿度', unit: '%', minLabel: '最小值', maxLabel: '最大值', floor: 0, ceiling: 100, source: 'simulated_firmware', editable: true, color: '#16a34a' },
  { key: 'co2', label: 'CO2 浓度', unit: 'ppm', minLabel: '—', maxLabel: '最大值', floor: 0, ceiling: 5000, source: 'simulated_backend', editable: false, color: '#059669' },
  { key: 'soil_ec', label: '土壤EC', unit: 'dS/m', minLabel: '最小值', maxLabel: '最大值', floor: 0, ceiling: 5, source: 'computed_backend', editable: false, color: '#0d9488' },
  { key: 'soil_tds', label: '土壤TDS', unit: 'ppm', minLabel: '最小值', maxLabel: '最大值', floor: 0, ceiling: 2000, source: 'computed_backend', editable: false, color: '#0891b2' },
  { key: 'soil_fertility', label: '土壤肥力', unit: '%', minLabel: '最小值', maxLabel: '最大值', floor: 0, ceiling: 100, source: 'computed_backend', editable: true, color: '#65a30d' },
  { key: 'infrared', label: '红外状态', unit: '', minLabel: '最小值', maxLabel: '最大值', floor: 0, ceiling: 1, source: 'simulated_backend', editable: false, color: '#dc2626' },
]

const editableKeys = computed(() => [...measuredThresholds, ...modelThresholds].filter(i => i.editable).map(i => i.key))

const autoRuleFields = [
  { key: 'start_below', label: '启动阈值', unit: '%', step: 0.1, min: 0 },
  { key: 'stop_at_or_above', label: '停止阈值', unit: '%', step: 0.1, min: 0 },
  { key: 'consecutive_samples', label: '连续样本', unit: '次', step: 1, min: 1 },
  { key: 'max_run_sec', label: '最长运行', unit: '秒', step: 1, min: 1 },
  { key: 'cooldown_sec', label: '冷却时间', unit: '秒', step: 1, min: 0 },
]

const thresholdRows = computed(() => ({
  measured: measuredThresholds.map(toThresholdRow),
  model: modelThresholds.map(toThresholdRow),
}))

const actuatorPolicies = computed(() => Object.values(DEVICE_META).map((device) => ({
  ...device,
  active: Boolean(systemStore.actuators[device.key]),
  stateText: systemStore.actuators[device.key] ? 'ON' : 'OFF',
})))

const mappingRows = computed(() => DEVICE_MAPPINGS.map((row) => {
  const active = row.stateKey === 'system' ? systemStore.wsConnected : Boolean(systemStore.actuators[row.stateKey])
  return {
    ...row,
    active,
    state: active ? 'ON' : 'OFF',
  }
}))

function toThresholdRow(item) {
  const value = thresholds.value[item.key] || { min: 0, max: 0 }
  const span = item.ceiling - item.floor || 1
  const rawLeft = value.min == null ? item.floor : value.min
  const rawRight = value.max == null ? rawLeft : value.max
  const left = Math.max(0, Math.min(100, ((rawLeft - item.floor) / span) * 100))
  const right = Math.max(0, Math.min(100, ((rawRight - item.floor) / span) * 100))
  return {
    ...item,
    min: value.min,
    max: value.max,
    sourceMeta: sourceMeta(item.source),
    bandLeft: Math.min(left, right),
    bandWidth: Math.max(2, Math.abs(right - left)),
  }
}

function valueText(value, unit) {
  if (value == null) return '—'
  return `${value}${unit}`
}

async function loadStatus() {
  try {
    const [thresholdRes, statusRes, ruleRes] = await Promise.all([
      api.get('/api/thresholds'),
      api.get('/api/status'),
      api.get('/api/control-rules/soil-moisture-pump'),
    ])
    if (Array.isArray(thresholdRes.data)) {
      thresholdRes.data.forEach((item) => {
        if (thresholds.value[item.param_name]) {
          thresholds.value[item.param_name] = { min: Number(item.min_value), max: Number(item.max_value) }
        }
      })
    }
    systemStore.updateStatus(statusRes.data || {})
    autoRule.value = normalizeRule(ruleRes.data)
  } catch {
    showToast({ title: '状态未刷新', message: '后端暂不可用，页面保留本地默认值', type: 'warn' })
  }
}

function normalizeRule(rule = autoRule.value) {
  return {
    enabled: Boolean(rule.enabled),
    start_below: Number(rule.start_below),
    stop_at_or_above: Number(rule.stop_at_or_above),
    consecutive_samples: Number(rule.consecutive_samples),
    max_run_sec: Number(rule.max_run_sec),
    cooldown_sec: Number(rule.cooldown_sec),
  }
}

async function saveThresholds() {
  saving.value = true
  try {
    const payload = editableKeys.value.map((param_name) => ({
      param_name,
      min_value: Number(thresholds.value[param_name].min),
      max_value: Number(thresholds.value[param_name].max),
    }))
    await api.put('/api/thresholds', payload)
    showToast({ title: '保存成功', message: '已保存当前后端支持的阈值', type: 'success' })
  } catch {
    showToast({ title: '保存失败', message: '后端不可用，请稍后重试', type: 'warn' })
  } finally {
    saving.value = false
  }
}

async function saveAutoRule({ silent = false } = {}) {
  ruleSaving.value = true
  try {
    const payload = normalizeRule()
    await api.put('/api/control-rules/soil-moisture-pump', payload)
    autoRule.value = payload
    if (!silent) {
      showToast({ title: '保存成功', message: '已保存自动浇水规则', type: 'success' })
    }
  } catch {
    if (!silent) {
      showToast({ title: '保存失败', message: '自动浇水规则未保存，请检查阈值关系', type: 'warn' })
    }
    throw new Error('auto rule save failed')
  } finally {
    ruleSaving.value = false
  }
}

async function saveAll() {
  saving.value = true
  try {
    const payload = editableKeys.value.map((param_name) => ({
      param_name,
      min_value: Number(thresholds.value[param_name].min),
      max_value: Number(thresholds.value[param_name].max),
    }))
    await api.put('/api/thresholds', payload)
    await saveAutoRule({ silent: true })
    showToast({ title: '保存成功', message: '已保存阈值和自动浇水规则', type: 'success' })
  } catch {
    showToast({ title: '保存失败', message: '请检查后端状态或自动浇水阈值关系', type: 'warn' })
  } finally {
    saving.value = false
  }
}

async function setMode(mode) {
  if (systemStore.mode === mode) return
  try {
    await api.put('/api/mode', { mode })
    systemStore.setMode(mode)
    showToast({ title: '已切换', message: mode === 'auto' ? '自动控制启用' : '手动控制启用', type: 'success' })
  } catch {
    showToast({ title: '切换失败', message: '后端不可用，请稍后重试', type: 'warn' })
  }
}

async function toggleActuator(device) {
  const next = systemStore.actuators[device] ? 'off' : 'on'
  try {
    await api.post('/api/control', { board_id: systemStore.currentBoardId || DEFAULT_BOARD_ID, device, action: next })
    systemStore.setActuator(device, next === 'on')
  } catch {
    showToast({ title: '控制失败', message: '串口网关或后端控制接口不可用', type: 'warn' })
  }
}

onMounted(loadStatus)
</script>

<template>
  <div class="control-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">控制与阈值</h1>
        <p class="page-subtitle">配置真实阈值、控制策略和板端引脚映射</p>
      </div>
      <div class="head-actions">
        <button class="btn btn-primary" type="button" @click="saveAll">{{ saving ? '保存中' : '保存配置' }}</button>
        <button class="btn btn-soft mode-btn" :class="{ active: systemStore.mode === 'auto' }" type="button" @click="setMode(systemStore.mode === 'auto' ? 'manual' : 'auto')">
          {{ systemStore.mode === 'auto' ? '自动控制启用' : '手动控制' }}
        </button>
      </div>
    </header>

    <div class="control-grid">
      <main class="threshold-panel card">
        <h2 class="section-title">阈值配置</h2>

        <section class="threshold-section">
          <div class="section-label">实测阈值 <b class="source-badge source-measured">实测</b></div>
          <article v-for="item in thresholdRows.measured" :key="item.key" class="threshold-row">
            <div class="threshold-name">
              <span :style="{ color: item.color }">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><path d="M7 8h10"/><path d="M7 16h10"/></svg>
              </span>
              <strong>{{ item.label }} <small>({{ item.unit }})</small></strong>
            </div>
            <label>{{ item.minLabel }} <input type="number" v-model.number="thresholds[item.key].min"></label>
            <div class="slider-track"><i :style="{ left: `${item.bandLeft}%`, width: `${item.bandWidth}%`, background: item.color }"></i></div>
            <label>{{ item.maxLabel }} <input type="number" v-model.number="thresholds[item.key].max"></label>
            <b class="source-badge" :class="item.sourceMeta.className">{{ item.sourceMeta.label }}</b>
          </article>
        </section>

        <section class="threshold-section">
          <div class="section-label">模型阈值 <b class="source-badge source-model">模型</b></div>
          <article v-for="item in thresholdRows.model" :key="item.key" class="threshold-row" :class="{ disabled: !item.editable }">
            <div class="threshold-name">
              <span :style="{ color: item.color }">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3c4.2 4.8 6.4 8.3 6.4 10.9a6.4 6.4 0 0 1-12.8 0C5.6 11.3 7.8 7.8 12 3z"/></svg>
              </span>
              <strong>{{ item.label }} <small>({{ item.unit }})</small></strong>
            </div>
            <label>{{ item.minLabel }} <input type="number" v-model.number="thresholds[item.key].min" :disabled="!item.editable"></label>
            <div class="slider-track"><i :style="{ left: `${item.bandLeft}%`, width: `${item.bandWidth}%`, background: item.color }"></i></div>
            <label>{{ item.maxLabel }} <input type="number" v-model.number="thresholds[item.key].max" :disabled="!item.editable"></label>
            <b class="source-badge" :class="item.sourceMeta.className">{{ item.sourceMeta.label }}</b>
          </article>
        </section>
      </main>

      <aside class="policy-panel">
        <section class="card auto-rule-card">
          <div class="rule-head">
            <div>
              <h2 class="section-title">自动浇水规则</h2>
              <p>基于土壤湿度控制普通浇水泵</p>
            </div>
            <label class="switch-row">
              <input v-model="autoRule.enabled" type="checkbox">
              <span>{{ autoRule.enabled ? '启用' : '停用' }}</span>
            </label>
          </div>
          <div class="rule-grid">
            <label v-for="field in autoRuleFields" :key="field.key">
              <span>{{ field.label }}</span>
              <input
                v-model.number="autoRule[field.key]"
                type="number"
                :step="field.step"
                :min="field.min"
              >
              <small>{{ field.unit }}</small>
            </label>
          </div>
          <p class="rule-summary">
            土壤湿度连续 {{ autoRule.consecutive_samples }} 次低于 {{ autoRule.start_below }}% 时启动，达到 {{ autoRule.stop_at_or_above }}% 或运行 {{ autoRule.max_run_sec }} 秒后停止，冷却 {{ autoRule.cooldown_sec }} 秒。
          </p>
          <button class="btn btn-soft" type="button" :disabled="ruleSaving" @click="saveAutoRule()">{{ ruleSaving ? '保存中' : '保存自动规则' }}</button>
        </section>

        <section class="card actuator-card">
          <h2 class="section-title">执行器策略</h2>
          <article v-for="item in actuatorPolicies" :key="item.key" class="actuator-policy">
            <span class="device-icon" :style="{ color: item.color }">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 19h10"/><path d="M9 19v-7h6v7"/><path d="M10 12V6h4v6"/><path d="M8 6h8"/></svg>
            </span>
            <div>
              <header>
                <strong>{{ item.label }}</strong>
                <b class="source-badge source-control">{{ item.mode }}</b>
              </header>
              <p>依据：{{ item.basis }}</p>
              <p>控制指令：{{ item.commandOn }} / {{ item.commandOff }}</p>
              <p class="rule-line">当前状态 <b :class="{ on: item.active }">{{ item.stateText }}</b></p>
            </div>
            <button class="toggle" :class="{ active: item.active }" type="button" @click="toggleActuator(item.key)"></button>
          </article>
        </section>
      </aside>
    </div>

    <section class="card mapping-panel">
      <h2 class="section-title">设备映射</h2>
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>设备</th>
              <th>板端引脚</th>
              <th>作用</th>
              <th>当前状态</th>
              <th>命令/说明</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in mappingRows" :key="row.pin">
              <td>{{ row.label }}</td>
              <td>{{ row.pin }}</td>
              <td>{{ row.role }}</td>
              <td><span class="status-dot" :class="row.active ? 'green' : 'gray'"></span> {{ row.state }}</td>
              <td>{{ row.command }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="mapping-note">模型字段可参与演示控制，但告警和控制记录需要保留来源标记；当前后端只执行已有阈值和三路控制命令。</p>
    </section>
  </div>
</template>

<style scoped>
.control-page {
  max-width: 1600px;
  margin: 0 auto;
}

.page-head,
.head-actions,
.threshold-row,
.threshold-name,
.section-label,
.rule-head,
.switch-row,
.actuator-policy,
.actuator-policy header,
.rule-line {
  display: flex;
  align-items: center;
}

.page-head {
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.head-actions {
  gap: 14px;
}

.mode-btn.active {
  border-color: #86efac;
  background: #f0fdf4;
  color: #15803d;
}

.control-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 440px;
  gap: 14px;
  align-items: start;
}

.threshold-panel,
.actuator-card,
.mapping-panel {
  padding: 14px;
}

.threshold-panel h2,
.actuator-card h2,
.mapping-panel h2 {
  margin-bottom: 16px;
}

.threshold-section + .threshold-section {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--border-light);
}

.section-label {
  gap: 10px;
  margin-bottom: 10px;
  color: #0f172a;
  font-size: 16px;
  font-weight: 800;
}

.threshold-row {
  display: grid;
  grid-template-columns: 170px 96px minmax(110px, 1fr) 96px 78px;
  gap: 10px;
  min-height: 50px;
  padding: 7px 0;
  border-bottom: 1px solid var(--border-light);
}

.threshold-row:last-child {
  border-bottom: 0;
}

.threshold-row.disabled {
  opacity: .72;
}

.threshold-name {
  gap: 10px;
  min-width: 0;
}

.threshold-name span {
  width: 26px;
  height: 26px;
  display: inline-flex;
  flex: 0 0 auto;
}

.threshold-name svg {
  width: 24px;
  height: 24px;
}

.threshold-name strong {
  min-width: 0;
  color: #17223b;
}

.threshold-name small {
  color: #64748b;
  font-weight: 600;
}

.threshold-row label {
  display: grid;
  gap: 4px;
  color: #475569;
  font-size: 12px;
  font-weight: 650;
}

.threshold-row input {
  width: 100%;
  height: 30px;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0 10px;
  background: #fff;
  color: #0f172a;
}

.threshold-row input:disabled {
  background: #f8fafc;
  color: #94a3b8;
}

.slider-track {
  position: relative;
  height: 6px;
  border-radius: 999px;
  background: #e8edf4;
}

.slider-track i {
  position: absolute;
  top: 0;
  height: 6px;
  border-radius: 999px;
}

.policy-panel {
  display: grid;
  gap: 14px;
}

.actuator-card {
  display: grid;
  gap: 10px;
}

.auto-rule-card {
  display: grid;
  gap: 14px;
  padding: 14px;
}

.rule-head {
  justify-content: space-between;
  gap: 12px;
}

.rule-head p {
  margin-top: 5px;
  color: #64748b;
  font-size: 13px;
}

.switch-row {
  gap: 8px;
  color: #334155;
  font-weight: 750;
}

.switch-row input {
  width: 16px;
  height: 16px;
  accent-color: var(--green-deep);
}

.rule-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.rule-grid label {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 86px 32px;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
}

.rule-grid span,
.rule-grid small {
  color: #64748b;
  font-size: 12px;
  font-weight: 650;
}

.rule-grid input {
  width: 100%;
  height: 28px;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0 8px;
  color: #0f172a;
}

.rule-summary {
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.actuator-policy {
  gap: 10px;
  min-height: 108px;
  padding: 12px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
}

.device-icon {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
}

.device-icon svg {
  width: 32px;
  height: 32px;
}

.actuator-policy div {
  display: grid;
  gap: 5px;
  min-width: 0;
  flex: 1;
}

.actuator-policy header {
  justify-content: space-between;
  gap: 10px;
}

.actuator-policy strong {
  font-size: 16px;
}

.actuator-policy p {
  color: #475569;
  font-size: 13px;
}

.rule-line b {
  margin-left: 8px;
  color: #94a3b8;
}

.rule-line b.on {
  color: #16a34a;
}

.mapping-panel {
  margin-top: 16px;
}

.mapping-panel h2 {
  margin-bottom: 14px;
}

.mapping-note {
  margin-top: 12px;
  color: #475569;
  font-size: 13px;
}

.status-dot.gray {
  background: #94a3b8;
}

@media (max-width: 1280px) {
  .control-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .page-head,
  .head-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .threshold-row {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .rule-head,
  .switch-row {
    align-items: flex-start;
  }

  .rule-grid {
    grid-template-columns: 1fr;
  }
}
</style>
