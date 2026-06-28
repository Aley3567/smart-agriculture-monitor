<script setup>
import AppLayout from './components/AppLayout.vue'
import { computed, watch, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { connectWebSocket, disconnectWebSocket } from './utils/websocket'
import { toasts } from './utils/toast'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const authStore = useAuthStore()
const isPublicPage = computed(() => Boolean(route.meta.public))

watch(() => authStore.isAuthenticated, (isAuthenticated) => {
  if (isAuthenticated) {
    connectWebSocket()
  } else {
    disconnectWebSocket()
  }
}, { immediate: true })

watch(isPublicPage, (publicPage) => {
  if (!publicPage && authStore.isAuthenticated) {
    connectWebSocket()
  }
})

onUnmounted(() => {
  disconnectWebSocket()
})
</script>

<template>
  <router-view v-if="isPublicPage" />
  <AppLayout v-else />
  <div class="toast-container">
    <div v-for="t in toasts" :key="t.id" class="toast" :class="'toast-' + t.type">
      <div>
        <div class="toast-title">{{ t.title }}</div>
        <div class="toast-body">{{ t.message }}</div>
      </div>
    </div>
  </div>
</template>
