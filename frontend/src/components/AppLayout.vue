<script setup>
import { useRouter, useRoute } from 'vue-router'
import { useSystemStore } from '../stores/system'
import { computed } from 'vue'

const router = useRouter()
const route = useRoute()
const systemStore = useSystemStore()

const activeMenu = computed(() => route.path)

const menuItems = [
  { path: '/dashboard', label: '实时监控', icon: 'Monitor' },
  { path: '/history', label: '历史数据', icon: 'DataLine' },
  { path: '/settings', label: '系统设置', icon: 'Setting' },
  { path: '/alarm-log', label: '报警日志', icon: 'Bell' },
]

function handleMenuSelect(path) {
  router.push(path)
}
</script>

<template>
  <el-container class="app-layout">
    <el-aside width="200px" class="app-aside">
      <div class="logo-area">
        <span class="logo-text">智慧农业</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        background-color="#0f1f3a"
        text-color="#8899aa"
        active-text-color="#00d4ff"
        @select="handleMenuSelect"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <h1 class="header-title">智慧农业环境监测系统</h1>
        <div class="header-status">
          <span class="status-dot" :class="systemStore.wsConnected ? 'online' : 'offline'"></span>
          <span class="status-text">{{ systemStore.wsConnected ? '已连接' : '未连接' }}</span>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-layout {
  height: 100vh;
  background: var(--bg-primary);
}

.app-aside {
  background: #0f1f3a;
  border-right: 1px solid var(--border-color);
  overflow-y: auto;
}

.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--border-color);
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 2px;
}

.app-header {
  height: 60px;
  background: #0f1f3a;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.status-dot.online {
  background: var(--success);
  box-shadow: 0 0 8px var(--success);
}

.status-dot.offline {
  background: var(--danger);
  box-shadow: 0 0 8px var(--danger);
}

.status-text {
  font-size: 14px;
  color: var(--text-secondary);
}

.app-main {
  background: var(--bg-primary);
  padding: 20px;
  overflow-y: auto;
}
</style>
