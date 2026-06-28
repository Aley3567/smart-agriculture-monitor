<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../utils/api'
import { useSystemStore } from '../stores/system'
import { useAuthStore } from '../stores/auth'
import { showToast } from '../utils/toast'
import { SETTINGS_FALLBACK } from '../utils/fallbackData'

const systemStore = useSystemStore()
const authStore = useAuthStore()
const saving = ref(false)

const thresholds = ref({
  temperature: { min: 18, max: 32 },
  humidity: { min: 45, max: 80 },
  light: { min: 500, max: 1600 },
  soil_moisture: { min: 35, max: 70 },
})

const params = [
  { key: 'temperature', label: '空气温度', desc: '联动通风与遮阳', unit: '°C', floor: -10, ceiling: 50, color: '#df463f' },
  { key: 'humidity', label: '空气湿度', desc: '联动通风与喷淋', unit: '%', floor: 0, ceiling: 100, color: '#3c98f0' },
  { key: 'light', label: '光照强度', desc: '联动天窗与补光', unit: 'lux', floor: 0, ceiling: 2000, color: '#fb8b12' },
  { key: 'soil_moisture', label: '土壤湿度', desc: '联动水泵灌溉', unit: '%', floor: 0, ceiling: 100, color: '#37a85b' },
]

const statusCards = computed(() => [
  { label: '运行模式', value: systemStore.mode === 'manual' ? '手动控制' : '自动控制', icon: 'shield', tone: 'green' },
  { label: '终端设备', value: systemStore.deviceOnline ? '在线' : '离线', icon: 'device', tone: systemStore.deviceOnline ? 'green' : 'orange' },
  { label: '有效阈值', value: '4/4', icon: 'link', tone: 'green' },
  { label: '策略状态', value: '可编辑', icon: 'sliders', tone: 'green' },
])

const thresholdCards = computed(() => params.map(item => {
  const value = thresholds.value[item.key]
  const span = item.ceiling - item.floor || 1
  const left = Math.max(0, Math.min(100, ((value.min - item.floor) / span) * 100))
  const right = Math.max(0, Math.min(100, ((value.max - item.floor) / span) * 100))
  return { ...item, min: value.min, max: value.max, bandLeft: left, bandWidth: Math.max(2, right - left) }
}))

const policies = SETTINGS_FALLBACK.policies
const changes = SETTINGS_FALLBACK.changes

onMounted(async () => {
  try {
    const [thresholdRes, statusRes] = await Promise.all([
      api.get('/api/thresholds'),
      api.get('/api/status'),
    ])
    if (Array.isArray(thresholdRes.data)) {
      thresholdRes.data.forEach(item => {
        if (thresholds.value[item.param_name]) {
          thresholds.value[item.param_name] = {
            min: Number(item.min_value),
            max: Number(item.max_value),
          }
        }
      })
    }
    systemStore.updateStatus(statusRes.data || {})
  } catch {
    systemStore.updateStatus({
      device_online: false,
      mode: 'auto',
      actuators: { pump: true, fertilizer: true, skylight: true },
    })
  }
})

async function saveThresholds() {
  saving.value = true
  try {
    const payload = Object.entries(thresholds.value).map(([param_name, value]) => ({
      param_name,
      min_value: Number(value.min),
      max_value: Number(value.max),
    }))
    await api.put('/api/thresholds', payload)
    showToast({ title: '保存成功', message: '策略已保存', type: 'success' })
  } catch {
    showToast({ title: '本地预览', message: '后端不可用，已保留页面配置', type: 'warn' })
  } finally {
    saving.value = false
  }
}

function setMode(mode) {
  systemStore.setMode(mode)
}

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const pwdError = ref('')
const pwdSuccess = ref('')
const pwdSaving = ref(false)

async function changePassword() {
  pwdError.value = ''
  pwdSuccess.value = ''
  if (!oldPassword.value) { pwdError.value = '请输入原密码'; return }
  if (newPassword.value.length < 6) { pwdError.value = '新密码至少6位'; return }
  if (newPassword.value !== confirmPassword.value) { pwdError.value = '两次密码不一致'; return }
  pwdSaving.value = true
  try {
    await authStore.changePassword({
      oldPassword: oldPassword.value,
      newPassword: newPassword.value,
    })
    pwdSuccess.value = '密码修改成功'
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (err) {
    pwdError.value = err.response?.data?.detail || '修改失败'
  } finally {
    pwdSaving.value = false
  }
}
</script>

<template>
  <div class="settings-page">
    <header class="topbar">
      <div>
        <h1 class="page-title">系统设置</h1>
        <p class="page-subtitle">环境阈值、控制模式与设备联动策略</p>
      </div>
      <button class="btn btn-primary" type="button" @click="saveThresholds">{{ saving ? '保存中' : '保存策略' }}</button>
    </header>

    <section class="status-row">
      <article v-for="item in statusCards" :key="item.label" class="card status-card">
        <span class="status-icon" :class="item.tone">
          <svg v-if="item.icon === 'shield'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 5 6v5.2c0 4.4 2.8 7.6 7 9.8 4.2-2.2 7-5.4 7-9.8V6l-7-3z"/><path d="M12 8v6"/></svg>
          <svg v-else-if="item.icon === 'device'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 18h14M8 18v-5h8v5M9 5h6v8H9z"/><path d="M12 13v5"/></svg>
          <svg v-else-if="item.icon === 'link'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.1 0l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1"/><path d="M14 11a5 5 0 0 0-7.1 0l-2 2A5 5 0 0 0 12 20l1.1-1.1"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h8M16 6h4M4 12h4M12 12h8M4 18h10M18 18h2"/><circle cx="14" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="16" cy="18" r="2"/></svg>
        </span>
        <div>
          <span>{{ item.label }}</span>
          <strong :class="{ orange: item.tone === 'orange' }">{{ item.value }}</strong>
        </div>
      </article>
    </section>

    <div class="settings-grid">
      <main class="left-stack">
        <section class="card threshold-panel">
          <div class="panel-head">
            <h2 class="section-title">报警阈值</h2>
            <span class="badge badge-success">配置完整</span>
          </div>
          <div class="threshold-list">
            <article v-for="card in thresholdCards" :key="card.key" class="threshold-item">
              <div class="threshold-title">
                <span class="status-dot" :style="{ background: card.color }"></span>
                <div>
                  <strong>{{ card.label }}</strong>
                  <small>{{ card.desc }}</small>
                </div>
                <span class="unit">{{ card.unit }}</span>
              </div>
              <div class="track">
                <span :style="{ left: `${card.bandLeft}%`, width: `${card.bandWidth}%`, background: card.color }"></span>
              </div>
              <div class="range-label">
                <span>{{ card.floor }}{{ card.unit }}</span>
                <strong>{{ card.min }} - {{ card.max }}{{ card.unit }}</strong>
                <span>{{ card.ceiling }}{{ card.unit }}</span>
              </div>
              <div class="threshold-inputs">
                <label>最小值 <input type="number" v-model.number="thresholds[card.key].min"></label>
                <label>最大值 <input type="number" v-model.number="thresholds[card.key].max"></label>
              </div>
            </article>
          </div>
        </section>

        <section class="card recent-card">
          <div class="panel-head">
            <h2 class="section-title">最近修改</h2>
            <button class="btn btn-ghost" type="button">查看全部</button>
          </div>
          <div class="table-scroll">
            <table class="data-table">
              <thead><tr><th>时间</th><th>修改内容</th><th>修改人</th><th>结果</th></tr></thead>
              <tbody>
                <tr v-for="row in changes" :key="row[0] + row[1]">
                  <td>{{ row[0] }}</td>
                  <td>{{ row[1] }}</td>
                  <td>{{ row[2] }}</td>
                  <td>{{ row[3] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>

      <aside class="right-stack">
        <section class="card mode-card">
          <h2 class="section-title">运行模式</h2>
          <div class="mode-options">
            <button class="mode-option" :class="{ active: systemStore.mode === 'auto' }" type="button" @click="setMode('auto')">
              <span></span>
              <div><strong>自动控制</strong><small>系统按照策略自动执行联动</small></div>
            </button>
            <button class="mode-option" :class="{ active: systemStore.mode === 'manual' }" type="button" @click="setMode('manual')">
              <span></span>
              <div><strong>手动控制</strong><small>手动操作执行器设备</small></div>
            </button>
          </div>
        </section>

        <section class="card connection-card">
          <div class="panel-head">
            <h2 class="section-title">连接状态</h2>
            <button class="btn btn-ghost" type="button">刷新状态</button>
          </div>
          <div class="connection-list">
            <div v-for="item in SETTINGS_FALLBACK.connection" :key="item[0]">
              <span class="status-dot" :class="{ orange: item[2] === 'orange' }"></span>
              <span>{{ item[0] }}</span>
              <strong :class="{ orange: item[2] === 'orange' }">{{ item[1] }}</strong>
            </div>
          </div>
        </section>

        <section class="card policy-card">
          <div class="panel-head">
            <h2 class="section-title">联动策略</h2>
            <button class="btn btn-soft" type="button">编辑策略</button>
          </div>
          <table class="policy-table">
            <thead><tr><th>触发条件</th><th>联动设备</th><th>执行动作</th></tr></thead>
            <tbody>
              <tr v-for="row in policies" :key="row[0] + row[1]">
                <td>{{ row[0] }}</td>
                <td>{{ row[1] }}</td>
                <td>{{ row[2] }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="card pwd-card">
          <h2 class="section-title">修改密码</h2>
          <div class="pwd-form">
            <label>原密码 <input type="password" v-model="oldPassword" autocomplete="current-password"></label>
            <label>新密码 <input type="password" v-model="newPassword" autocomplete="new-password" placeholder="至少6位"></label>
            <label>确认密码 <input type="password" v-model="confirmPassword" autocomplete="new-password"></label>
            <p v-if="pwdError" class="pwd-msg pwd-error">{{ pwdError }}</p>
            <p v-if="pwdSuccess" class="pwd-msg pwd-ok">{{ pwdSuccess }}</p>
            <button class="btn btn-primary" type="button" @click="changePassword" :disabled="pwdSaving">
              {{ pwdSaving ? '保存中' : '修改密码' }}
            </button>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  max-width: 1260px;
  margin: 0 auto;
}

.topbar,
.status-card,
.panel-head,
.threshold-title,
.range-label,
.threshold-inputs,
.mode-options,
.mode-option,
.connection-list div {
  display: flex;
  align-items: center;
}

.topbar {
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.status-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.status-card {
  height: 76px;
  gap: 18px;
  padding: 16px 22px;
}

.status-icon {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #79b789;
}

.status-icon.orange {
  color: var(--orange);
}

.status-icon svg {
  width: 32px;
  height: 32px;
}

.status-card div {
  display: grid;
  gap: 2px;
}

.status-card span {
  color: var(--text-muted);
}

.status-card strong {
  font-size: 21px;
}

.status-card .orange {
  color: var(--orange);
}

.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 460px;
  gap: 14px;
}

.left-stack,
.right-stack {
  display: grid;
  gap: 12px;
  align-content: start;
  min-width: 0;
}

.threshold-panel,
.recent-card,
.mode-card,
.connection-card,
.policy-card {
  padding: 16px;
}

.panel-head {
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.threshold-list {
  display: grid;
}

.threshold-item {
  padding: 11px 0 10px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
}

.threshold-item + .threshold-item {
  margin-top: -1px;
}

.threshold-title {
  gap: 10px;
  padding: 0 12px;
}

.threshold-title div {
  display: grid;
  gap: 2px;
}

.threshold-title small {
  color: var(--text-muted);
}

.unit {
  margin-left: auto;
  min-width: 34px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #f4f4f4;
  color: var(--text-muted);
  font-weight: 700;
  font-size: 12px;
}

.track {
  position: relative;
  height: 6px;
  margin: 11px 12px 6px;
  border-radius: 999px;
  background: #f0f0ee;
}

.track span {
  position: absolute;
  top: 0;
  height: 6px;
  border-radius: 999px;
}

.range-label {
  justify-content: space-between;
  margin: 0 12px 6px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 12px;
}

.range-label strong {
  color: var(--text-primary);
  font-size: 13px;
}

.threshold-inputs {
  gap: 34px;
  padding: 0 12px;
}

.threshold-inputs label {
  flex: 1;
  display: grid;
  gap: 5px;
  color: var(--text-muted);
  font-size: 12px;
}

.threshold-inputs input {
  height: 29px;
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 0 10px;
  background: #fff;
  color: var(--text-primary);
}

.recent-card {
  padding-top: 8px;
}

.recent-card .data-table td {
  height: 24px;
  font-size: 12px;
}

.mode-card h2 {
  margin-bottom: 18px;
}

.mode-options {
  gap: 16px;
}

.mode-option {
  flex: 1;
  min-height: 88px;
  gap: 12px;
  padding: 18px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
  background: #fff;
  text-align: left;
}

.mode-option.active {
  border-color: #2d8b4d;
  box-shadow: inset 0 0 0 1px rgba(45, 139, 77, 0.25);
}

.mode-option > span {
  width: 18px;
  height: 18px;
  border: 1px solid var(--border);
  border-radius: 50%;
}

.mode-option.active > span {
  border: 5px solid #4a9d61;
}

.mode-option div {
  display: grid;
  gap: 5px;
}

.mode-option small {
  color: var(--text-muted);
}

.connection-list {
  display: grid;
  padding: 12px 16px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
}

.connection-list div {
  height: 34px;
  gap: 10px;
}

.connection-list strong {
  margin-left: auto;
  color: var(--green-deep);
}

.connection-list .orange {
  color: var(--orange);
}

.connection-list .status-dot:not(.orange) {
  background: #858b92;
}

.policy-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.policy-table th,
.policy-table td {
  height: 38px;
  padding: 0 12px;
  border: 1px solid var(--border-light);
  text-align: left;
}

.policy-table th {
  background: #fafafa;
  color: var(--text-muted);
}

.pwd-card {
  padding: 16px;
}

.pwd-card h2 {
  margin-bottom: 16px;
}

.pwd-form {
  display: grid;
  gap: 12px;
}

.pwd-form label {
  display: grid;
  gap: 5px;
  color: var(--text-muted);
  font-size: 12px;
}

.pwd-form input {
  height: 36px;
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  padding: 0 12px;
  background: #fff;
  color: var(--text-primary);
  outline: none;
}

.pwd-form input:focus {
  border-color: var(--green-deep);
  box-shadow: 0 0 0 3px rgba(36, 113, 61, 0.1);
}

.pwd-msg {
  font-size: 13px;
}

.pwd-error {
  color: var(--red);
}

.pwd-ok {
  color: var(--green-deep);
}

.pwd-form .btn {
  width: 100%;
  height: 36px;
}

@media (max-width: 1120px) {
  .status-row,
  .settings-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .right-stack {
    grid-column: 1 / -1;
  }
}

@media (max-width: 860px) {
  .topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .topbar .btn {
    width: 100%;
  }

  .status-row,
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .mode-options,
  .threshold-inputs {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
}
</style>
