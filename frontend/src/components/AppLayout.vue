<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const navItems = [
  { path: '/dashboard', label: '实时监控', icon: 'leaf' },
  { path: '/history', label: '历史数据', icon: 'clock' },
  { path: '/alarm-log', label: '报警日志', icon: 'bell' },
  { path: '/settings', label: '系统设置', icon: 'sliders' },
]

const currentPath = computed(() => route.path)

function logout() {
  authStore.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="layout-shell">
    <aside class="sidebar">
      <div class="brand">
        <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M15.7 3.8c-6.7.3-12 5.8-12 12.5 0 6.5 5 11.8 11.3 12.4" />
          <path d="M14.8 4.3c3.4 4 5 8.5 4.8 13.6" />
          <path d="M22 9.4c-3.5.5-6.2 2.2-8 5.1" />
          <path d="M26.8 16.2c-3.1-1.2-6.4-.6-9.8 1.8" />
          <path d="M23.8 5.5c-1.1 2.6-.8 5 .8 7.3" />
        />
        </svg>
        <span>智慧农业</span>
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
          <svg v-if="item.icon === 'leaf'" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.1 3.1c4.2 0 7.3 2.6 8 6.4-3.3-.2-5.7-1-7.4-2.4-1.7 1.8-2.3 4.3-1.8 7.7C5.3 13.2 3.2 10.4 3.2 7.4c0-2.4 2.6-4.3 6.9-4.3z" />
          </svg>
          <svg v-else-if="item.icon === 'clock'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="10" cy="10" r="7.2" />
            <path d="M10 5.8v4.5l3 1.8" />
          </svg>
          <svg v-else-if="item.icon === 'bell'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path d="M6 8.6a4 4 0 0 1 8 0c0 2.9 1.4 3.8 1.4 5H4.6c0-1.2 1.4-2.1 1.4-5z" />
            <path d="M8.2 15.4a2 2 0 0 0 3.6 0" />
          </svg>
          <svg v-else viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 5h4.8M11.5 5H17M3 10h8.5M15 10h2M3 15h2.5M9.2 15H17" />
            <circle cx="9.7" cy="5" r="1.7" />
            <circle cx="13.2" cy="10" r="1.7" />
            <circle cx="7.2" cy="15" r="1.7" />
          </svg>
          <span>{{ item.label }}</span>
        </a>
      </nav>

      <div class="sidebar-bottom">
        <button class="greenhouse-switch" type="button">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3.5 9.5 10 4l6.5 5.5" />
            <path d="M5.2 8.8v7h9.6v-7" />
            <path d="M8 15.8v-5h4v5" />
          </svg>
          <span>温室A-1号</span>
          <svg class="chev" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="m6 8 4 4 4-4" />
          </svg>
        </button>

        <button class="user-card" type="button" @click="logout">
          <span class="avatar">
            <svg viewBox="0 0 28 28" fill="none">
              <circle cx="14" cy="9" r="5" fill="#202423" opacity=".85" />
              <path d="M5 24c1.2-5 4.1-7.5 9-7.5s7.8 2.5 9 7.5" fill="#202423" opacity=".85" />
            </svg>
          </span>
          <span class="user-copy">
            <strong>{{ authStore.user?.name }}</strong>
            <small>{{ authStore.user?.role }}</small>
          </span>
          <svg class="chev" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="m6 8 4 4 4-4" />
          </svg>
        </button>
      </div>
    </aside>

    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.layout-shell {
  display: flex;
  min-height: 100vh;
  background: var(--bg-body);
}

.sidebar {
  position: sticky;
  top: 0;
  width: 224px;
  height: 100vh;
  flex: 0 0 224px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background:
    radial-gradient(circle at 72% 8%, rgba(91, 150, 92, 0.22), transparent 33%),
    linear-gradient(180deg, var(--bg-sidebar), var(--bg-sidebar-2));
  color: var(--text-inverse);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 76px;
  padding: 0 24px;
  color: #eef8f0;
  font-size: 21px;
  font-weight: 650;
  letter-spacing: 0.02em;
}

.brand svg {
  width: 32px;
  height: 32px;
  color: #8ad39b;
}

.sidebar-nav {
  flex: 1;
  padding: 8px 10px;
}

.nav-item {
  height: 48px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  border-radius: 6px;
  color: rgba(237, 247, 239, 0.68);
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
}

.nav-item + .nav-item {
  margin-top: 10px;
}

.nav-item:hover {
  background: var(--bg-sidebar-hover);
  color: #fff;
}

.nav-item.active {
  background: var(--bg-sidebar-active);
  color: #fff;
}

.nav-item svg {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
}

.sidebar-bottom {
  display: grid;
  gap: 18px;
  padding: 0 12px 26px;
}

.greenhouse-switch,
.user-card {
  width: 100%;
  display: flex;
  align-items: center;
  border: 1px solid rgba(255, 255, 255, 0.11);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.04);
  color: #f0f7f2;
  text-align: left;
}

.greenhouse-switch {
  height: 56px;
  padding: 0 14px;
  gap: 10px;
  font-weight: 650;
}

.greenhouse-switch svg:first-child {
  width: 19px;
  height: 19px;
}

.chev {
  width: 16px;
  height: 16px;
  margin-left: auto;
  opacity: 0.72;
}

.user-card {
  height: 58px;
  gap: 10px;
  padding: 0 10px;
  border-color: transparent;
  background: transparent;
}

.avatar {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(#d4d8d1, #7f8a7e);
  overflow: hidden;
}

.avatar svg {
  width: 34px;
  height: 34px;
}

.user-copy {
  display: grid;
  line-height: 1.2;
}

.user-copy strong {
  font-size: 15px;
}

.user-copy small {
  margin-top: 4px;
  color: rgba(238, 248, 240, 0.72);
  font-size: 12px;
}

.main-content {
  flex: 1;
  min-width: 0;
  padding: 22px 24px 28px;
  overflow-x: hidden;
}

@media (max-width: 860px) {
  .layout-shell {
    display: block;
  }

  .sidebar {
    position: static;
    width: 100%;
    height: auto;
    min-height: 0;
  }

  .brand {
    height: 60px;
    padding: 0 16px;
  }

  .sidebar-nav {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding: 0 12px 12px;
  }

  .nav-item {
    flex: 0 0 auto;
    height: 40px;
    padding: 0 12px;
    white-space: nowrap;
  }

  .nav-item + .nav-item {
    margin-top: 0;
  }

  .sidebar-bottom {
    display: none;
  }

  .main-content {
    padding: 16px 12px 24px;
  }
}
</style>
