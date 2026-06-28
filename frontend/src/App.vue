<script setup>
import AppLayout from './components/AppLayout.vue'
import { onMounted, onUnmounted } from 'vue'
import { connectWebSocket, disconnectWebSocket } from './utils/websocket'

onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  disconnectWebSocket()
})
</script>

<template>
  <AppLayout />
</template>
