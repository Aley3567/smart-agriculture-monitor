<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useSystemStore } from '../stores/system'
import api from '../utils/api'
import { formatTimeOnly } from '../utils/format'
import { ACTION_LABEL, PARAM_LABEL, PARAM_UNIT } from '../utils/constants'
import { sourceMeta } from '../utils/sources'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const systemStore = useSystemStore()
const now = ref(new Date())
const alarmMessages = ref([])
const showMessages = ref(false)
const showUserMenu = ref(false)
const showProfile = ref(false)
const showLogoutConfirm = ref(false)
const localName = ref(authStore.user?.name || '')
const localAvatar = ref(authStore.user?.avatar || '')
const readAlarmIds = ref(readLocalArray('smart-agriculture-read-alarms'))
let clockTimer = null

const navItems = [
  { path: '/dashboard', label: '实时监测', icon: 'home' },
  { path: '/history', label: '历史分析', icon: 'chart' },
  { path: '/control', label: '控制与阈值', icon: 'sliders' },
  { path: '/test-mode', label: '测试模式', icon: 'test' },
  { path: '/models', label: '模型管理', icon: 'cube' },
  { path: '/weather', label: '环境气象', icon: 'cloud' },
  { path: '/alarm-log', label: '告警日志', icon: 'alert' },
]

const currentPath = computed(() => {
  if (route.path === '/settings') return '/control'
  return route.path
})

const statusItems = computed(() => [
  {
    label: systemStore.wsConnected ? '主平台运行中' : '主平台连接中断',
    tone: systemStore.wsConnected ? 'green' : 'red',
  },
  {
    label: 'OneNET旁路状态待接入',
    tone: 'blue',
  },
  {
    label: systemStore.deviceOnline ? '串口网关已连接' : '串口网关未连接',
    tone: systemStore.deviceOnline ? 'green' : 'orange',
  },
])

const nowText = computed(() => now.value.toLocaleString('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
}).replace(/\//g, '-'))

const notificationItems = computed(() => [
  {
    id: 'welcome',
    kind: 'system',
    title: `欢迎回来，${authStore.user?.name || 'useraley'}`,
    detail: '智慧农业环境监测平台已连接',
    time: now.value,
    source: sourceMeta('system'),
  },
  ...alarmMessages.value.map((item) => {
    const source = sourceForParam(item.param_name)
    return {
      id: `alarm-${item.id}`,
      rawId: item.id,
      kind: 'alarm',
      title: `${PARAM_LABEL[item.param_name] || item.param_name}${Number(item.value) < Number(item.threshold) ? '低于阈值' : '超过阈值'}`,
      detail: `${item.value}${paramUnit(item.param_name)} / ${item.threshold}${paramUnit(item.param_name)} · ${ACTION_LABEL[item.action] || item.action}`,
      time: item.timestamp,
      source,
    }
  }),
])

const unreadCount = computed(() => alarmMessages.value.filter(item => !readAlarmIds.value.includes(item.id)).length)

function readLocalArray(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

function persistReadAlarms() {
  localStorage.setItem('smart-agriculture-read-alarms', JSON.stringify(readAlarmIds.value.slice(0, 80)))
}

function sourceForParam(param) {
  if (['temperature', 'humidity'].includes(param)) return sourceMeta('measured')
  if (param === 'light') return sourceMeta('measured')
  if (['soil_moisture', 'soil'].includes(param)) return sourceMeta('simulated_firmware')
  return sourceMeta('system')
}

function paramUnit(param) {
  if (param === 'light') return '相对值'
  return PARAM_UNIT[param] || ''
}

async function fetchMessages() {
  try {
    const res = await api.get('/api/alarms', { params: { page: 1, page_size: 6 } })
    alarmMessages.value = Array.isArray(res.data?.items) ? res.data.items : []
  } catch {
    alarmMessages.value = []
  }
}

function toggleMessages() {
  showMessages.value = !showMessages.value
  showUserMenu.value = false
  if (showMessages.value && alarmMessages.value.length) {
    const ids = alarmMessages.value.map(item => item.id)
    readAlarmIds.value = [...new Set([...ids, ...readAlarmIds.value])]
    persistReadAlarms()
  }
}

function openAlarm(item) {
  if (item.kind !== 'alarm') return
  showMessages.value = false
  router.push({ path: '/alarm-log', query: { id: item.rawId } })
}

function toggleUserMenu() {
  showUserMenu.value = !showUserMenu.value
  showMessages.value = false
}

function openProfile() {
  localName.value = authStore.user?.name || ''
  localAvatar.value = authStore.user?.avatar || ''
  showProfile.value = true
  showUserMenu.value = false
}

function saveProfile() {
  authStore.updateLocalProfile({ name: localName.value.trim() || authStore.user?.username, avatar: localAvatar.value })
  showProfile.value = false
}

function chooseAvatar(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    localAvatar.value = String(reader.result || '')
  }
  reader.readAsDataURL(file)
}

function requestLogout() {
  showLogoutConfirm.value = true
  showUserMenu.value = false
}

function logout() {
  authStore.logout()
  showLogoutConfirm.value = false
  router.replace('/login')
}

onMounted(() => {
  fetchMessages()
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  if (clockTimer) window.clearInterval(clockTimer)
})
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="brand">
        <span class="brand-mark">
          <svg viewBox="0 0 32 32" fill="none">
            <path d="M27 4C15.8 4.3 7.5 10.8 6.2 22.7c7.6-1.1 14.4-6 17.1-13.4-3.3 2.1-7.1 3.3-11.3 3.7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M6 23c3.6-4.8 8.2-8.1 13.8-9.8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </span>
        <span>智慧农业环境监测平台</span>
      </div>

      <nav class="sidebar-nav" aria-label="主导航">
        <a
          v-for="item in navItems"
          :key="item.path"
          :href="item.path"
          class="nav-item"
          :class="{ active: currentPath === item.path }"
          @click.prevent="router.push(item.path)"
        >
          <svg v-if="item.icon === 'home'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="m3 11 9-8 9 8"/><path d="M5 10.5V21h14V10.5"/><path d="M9 21v-6h6v6"/>
          </svg>
          <svg v-else-if="item.icon === 'chart'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 20V4"/><path d="M4 20h16"/><path d="M8 16V9"/><path d="M12 16V5"/><path d="M16 16v-4"/>
          </svg>
          <svg v-else-if="item.icon === 'sliders'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 7h7"/><path d="M15 7h5"/><path d="M4 12h4"/><path d="M12 12h8"/><path d="M4 17h10"/><path d="M18 17h2"/><circle cx="13" cy="7" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="16" cy="17" r="2"/>
          </svg>
          <svg v-else-if="item.icon === 'test'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 3h6"/><path d="M10 3v5l-4.8 8.6A3 3 0 0 0 7.8 21h8.4a3 3 0 0 0 2.6-4.4L14 8V3"/><path d="M7.6 15h8.8"/><path d="M10 18h.01"/><path d="M14 18h.01"/>
          </svg>
          <svg v-else-if="item.icon === 'cube'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3z"/><path d="M12 12 4.4 7.8"/><path d="m12 12 7.6-4.2"/><path d="M12 12v9"/>
          </svg>
          <svg v-else-if="item.icon === 'cloud'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M7 18h10a4 4 0 0 0 .4-8A6 6 0 0 0 5.7 11.5 3.4 3.4 0 0 0 7 18z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3 2.8 19h18.4L12 3z"/><path d="M12 8v5"/><path d="M12 17h.01"/>
          </svg>
          <span>{{ item.label }}</span>
        </a>
      </nav>

      <button class="sidebar-collapse" type="button" title="收起侧边栏">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="m12 5-5 5 5 5"/>
        </svg>
      </button>
    </aside>

    <div class="app-main">
      <header class="global-topbar">
        <div class="platform-status">
          <span v-for="item in statusItems" :key="item.label" class="platform-pill">
            <i :class="item.tone"></i>{{ item.label }}
          </span>
        </div>
        <div class="topbar-right">
          <span class="time-pill">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="10" cy="10" r="7.2"/><path d="M10 5.8V10l2.8 1.8"/>
            </svg>
            {{ nowText }}
          </span>
          <div class="topbar-popover">
            <button class="bell-btn" type="button" title="消息" @click="toggleMessages">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <path d="M6 8.6a4 4 0 0 1 8 0c0 2.9 1.4 3.8 1.4 5H4.6c0-1.2 1.4-2.1 1.4-5z"/><path d="M8.2 15.4a2 2 0 0 0 3.6 0"/>
            </svg>
              <b v-if="unreadCount">{{ unreadCount > 9 ? '9+' : unreadCount }}</b>
            </button>
          </div>

          <div class="topbar-popover">
            <button class="admin-menu" type="button" @click="toggleUserMenu">
            <span class="avatar-dot">
              <img v-if="authStore.user?.avatar" :src="authStore.user.avatar" alt="">
              <svg v-else viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="6.7" r="3.4" fill="currentColor"/><path d="M3.8 18c.8-4.4 2.8-6.5 6.2-6.5s5.4 2.1 6.2 6.5" fill="currentColor"/>
              </svg>
            </span>
            <span>{{ authStore.user?.name || '管理员' }}</span>
            <svg class="chev" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="m6 8 4 4 4-4"/>
            </svg>
            </button>
            <section v-if="showUserMenu" class="dropdown-panel user-panel">
              <button type="button" @click="openProfile">个人中心</button>
              <button type="button" class="danger" @click="requestLogout">退出登录</button>
            </section>
          </div>
        </div>
      </header>

      <main class="content-area">
        <router-view />
      </main>
    </div>

    <div v-if="showMessages" class="modal-backdrop message-backdrop" @click.self="showMessages = false">
      <section class="message-modal">
        <header>
          <div>
            <h2>消息中心</h2>
            <p>{{ unreadCount ? `${unreadCount} 条未读消息` : '暂无未读消息' }}</p>
          </div>
          <div class="message-actions">
            <button type="button" @click="router.push('/alarm-log'); showMessages = false">查看全部</button>
            <button class="modal-close" type="button" title="关闭" @click="showMessages = false">×</button>
          </div>
        </header>
        <div class="message-list">
          <article
            v-for="item in notificationItems"
            :key="item.id"
            class="message-item"
            :class="item.kind"
            @click="openAlarm(item)"
          >
            <i></i>
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.detail }}</p>
              <span><b class="source-badge" :class="item.source.className">{{ item.source.label }}</b>{{ formatTimeOnly(item.time) }}</span>
            </div>
          </article>
        </div>
      </section>
    </div>

    <div v-if="showProfile" class="modal-backdrop" @click.self="showProfile = false">
      <section class="profile-modal">
        <header>
          <h2>个人中心</h2>
          <button type="button" @click="showProfile = false">×</button>
        </header>
        <div class="profile-body">
          <label class="avatar-picker">
            <span class="profile-avatar">
              <img v-if="localAvatar" :src="localAvatar" alt="">
              <svg v-else viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="6.7" r="3.4" fill="currentColor"/><path d="M3.8 18c.8-4.4 2.8-6.5 6.2-6.5s5.4 2.1 6.2 6.5" fill="currentColor"/>
              </svg>
            </span>
            <input type="file" accept="image/*" @change="chooseAvatar">
            <b>更换头像</b>
          </label>
          <label>
            <span>昵称</span>
            <input v-model="localName" class="field">
          </label>
          <dl>
            <div><dt>账号</dt><dd>{{ authStore.user?.username }}</dd></div>
            <div><dt>角色</dt><dd>{{ authStore.user?.role }}</dd></div>
            <div><dt>登录时间</dt><dd>{{ nowText }}</dd></div>
          </dl>
        </div>
        <footer>
          <button class="btn btn-ghost" type="button" @click="showProfile = false">取消</button>
          <button class="btn btn-primary" type="button" @click="saveProfile">保存</button>
        </footer>
      </section>
    </div>

    <div v-if="showLogoutConfirm" class="modal-backdrop" @click.self="showLogoutConfirm = false">
      <section class="confirm-modal">
        <h2>确认退出当前账号？</h2>
        <p>退出后需要重新登录才能继续查看监测数据。</p>
        <footer>
          <button class="btn btn-ghost" type="button" @click="showLogoutConfirm = false">取消</button>
          <button class="btn btn-primary danger-btn" type="button" @click="logout">确认退出</button>
        </footer>
      </section>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 224px minmax(0, 1fr);
  background: var(--bg-body);
}

.app-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-light);
  background: #fff;
}

.brand {
  height: 70px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  border-bottom: 1px solid var(--border-light);
  color: #0f1f3a;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.25;
}

.brand-mark {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: #0e9f48;
  color: #fff;
  flex: 0 0 auto;
}

.brand-mark svg {
  width: 28px;
  height: 28px;
}

.sidebar-nav {
  display: grid;
  gap: 8px;
  padding: 22px 14px;
}

.nav-item {
  height: 52px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 16px;
  border-radius: 7px;
  color: #102044;
  text-decoration: none;
  font-size: 15px;
  font-weight: 700;
}

.nav-item:hover,
.nav-item.active {
  background: #eaf7ef;
  color: #0a9b45;
}

.nav-item svg {
  width: 22px;
  height: 22px;
  flex: 0 0 auto;
}

.sidebar-collapse {
  width: 32px;
  height: 32px;
  margin: auto 18px 18px auto;
  border: 1px solid var(--border-light);
  border-radius: 50%;
  background: #fff;
  color: #64748b;
}

.sidebar-collapse svg {
  width: 16px;
  height: 16px;
}

.app-main {
  min-width: 0;
}

.global-topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 0 28px;
  border-bottom: 1px solid var(--border-light);
  background: rgba(255, 255, 255, .92);
  backdrop-filter: blur(12px);
}

.platform-status,
.topbar-right,
.platform-pill,
.time-pill,
.admin-menu,
.bell-btn {
  display: flex;
  align-items: center;
}

.platform-status {
  gap: 14px;
  min-width: 0;
  flex-wrap: wrap;
}

.platform-pill {
  height: 38px;
  gap: 9px;
  padding: 0 18px;
  border: 1px solid #e2e8f0;
  border-radius: 7px;
  background: #fff;
  color: #17223b;
  font-weight: 650;
  white-space: nowrap;
}

.platform-pill i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--muted);
}

.platform-pill i.green { background: #10a64a; }
.platform-pill i.blue { background: #2563eb; }
.platform-pill i.orange { background: #f97316; }
.platform-pill i.red { background: #dc2626; }

.topbar-right {
  gap: 16px;
  color: #0f172a;
}

.topbar-popover {
  position: relative;
}

.time-pill {
  gap: 8px;
  white-space: nowrap;
  font-family: var(--font-mono);
  color: #17223b;
}

.time-pill svg,
.bell-btn svg {
  width: 20px;
  height: 20px;
}

.bell-btn {
  position: relative;
  width: 34px;
  height: 34px;
  justify-content: center;
  border: 0;
  background: transparent;
  color: #0f1f3a;
}

.bell-btn b {
  position: absolute;
  top: 0;
  right: 1px;
  min-width: 17px;
  height: 17px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  border-radius: 999px;
  background: #16a34a;
  color: #fff;
  font-size: 10px;
  font-weight: 800;
}

.dropdown-panel {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 60;
  width: 320px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.14);
}

.message-modal {
  width: min(560px, calc(100vw - 32px));
  max-height: min(680px, calc(100vh - 48px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 28px 70px rgba(15, 23, 42, .24);
}

.message-modal header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 72px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-light);
}

.message-modal h2 {
  font-size: 19px;
  line-height: 1.2;
}

.message-modal header p {
  margin-top: 5px;
  color: #64748b;
  font-size: 13px;
}

.message-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.message-actions button,
.user-panel button {
  border: 0;
  background: transparent;
  color: var(--green-deep);
  font-weight: 750;
}

.message-actions .modal-close {
  width: 32px;
  height: 32px;
  color: #64748b;
  font-size: 24px;
  line-height: 1;
}

.message-list {
  display: grid;
  overflow: auto;
  padding: 6px 18px 10px;
}

.message-item {
  display: grid;
  grid-template-columns: 9px minmax(0, 1fr);
  gap: 10px;
  padding: 15px 0;
  border-bottom: 1px solid var(--border-light);
  cursor: default;
}

.message-item:last-child {
  border-bottom: 0;
}

.message-item.alarm {
  cursor: pointer;
}

.message-item i {
  width: 8px;
  height: 8px;
  margin-top: 7px;
  border-radius: 999px;
  background: #16a34a;
}

.message-item.alarm i {
  background: #ef4444;
}

.message-item strong {
  display: block;
  color: #17223b;
}

.message-item p {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.4;
}

.message-item span {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 7px;
  color: #64748b;
  font-family: var(--font-mono);
  font-size: 12px;
}

.admin-menu {
  height: 38px;
  gap: 8px;
  border: 0;
  background: transparent;
  color: #0f1f3a;
  font-weight: 700;
}

.avatar-dot {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #0aa344;
  color: #fff;
  overflow: hidden;
}

.avatar-dot svg {
  width: 18px;
  height: 18px;
}

.avatar-dot img,
.profile-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.chev {
  width: 16px;
  height: 16px;
}

.user-panel {
  width: 170px;
  padding: 6px;
}

.user-panel button {
  width: 100%;
  height: 38px;
  padding: 0 10px;
  border-radius: 6px;
  text-align: left;
  color: #17223b;
}

.user-panel button:hover {
  background: #f4faf6;
}

.user-panel .danger {
  color: #dc2626;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, .28);
}

.message-backdrop {
  background: rgba(15, 23, 42, .42);
}

.profile-modal,
.confirm-modal {
  width: min(440px, 100%);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 24px 60px rgba(15, 23, 42, .2);
}

.profile-modal header {
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  border-bottom: 1px solid var(--border-light);
}

.profile-modal header h2,
.confirm-modal h2 {
  font-size: 18px;
}

.profile-modal header button {
  width: 32px;
  height: 32px;
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 24px;
}

.profile-body {
  display: grid;
  gap: 16px;
  padding: 18px;
}

.avatar-picker {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--green-deep);
  font-weight: 750;
  cursor: pointer;
}

.avatar-picker input {
  display: none;
}

.profile-avatar {
  width: 54px;
  height: 54px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 50%;
  background: #0aa344;
  color: #fff;
}

.profile-avatar svg {
  width: 32px;
  height: 32px;
}

.profile-body label:not(.avatar-picker) {
  display: grid;
  gap: 7px;
  color: #475569;
  font-weight: 700;
}

.profile-body dl {
  display: grid;
  border-top: 1px solid var(--border-light);
}

.profile-body dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);
}

.profile-body dt {
  color: #64748b;
}

.profile-body dd {
  color: #17223b;
  font-weight: 750;
}

.profile-modal footer,
.confirm-modal footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 18px;
  border-top: 1px solid var(--border-light);
}

.confirm-modal {
  padding-top: 18px;
}

.confirm-modal h2,
.confirm-modal p {
  padding: 0 18px;
}

.confirm-modal p {
  margin-top: 8px;
  color: #64748b;
}

.danger-btn {
  border-color: #dc2626;
  background: #dc2626;
  box-shadow: none;
}

.content-area {
  padding: 24px 28px 30px;
}

@media (max-width: 1100px) {
  .app-shell {
    grid-template-columns: 84px minmax(0, 1fr);
  }

  .brand {
    justify-content: center;
    padding: 0;
  }

  .brand span:last-child,
  .nav-item span {
    display: none;
  }

  .nav-item {
    justify-content: center;
    padding: 0;
  }

  .global-topbar {
    height: auto;
    min-height: 70px;
    align-items: flex-start;
    flex-direction: column;
    padding: 14px 20px;
  }

  .topbar-right {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (max-width: 760px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .app-sidebar {
    position: static;
    height: auto;
  }

  .brand {
    justify-content: flex-start;
    padding: 0 16px;
  }

  .brand span:last-child,
  .nav-item span {
    display: inline;
  }

  .sidebar-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 12px;
  }

  .sidebar-collapse {
    display: none;
  }

  .platform-status {
    display: grid;
    width: 100%;
  }

  .topbar-right {
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
  }

  .content-area {
    padding: 16px;
  }
}
</style>
