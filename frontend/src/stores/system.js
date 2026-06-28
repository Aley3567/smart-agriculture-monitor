import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSystemStore = defineStore('system', () => {
  const wsConnected = ref(false)
  const deviceOnline = ref(false)
  const mode = ref('auto')
  const actuators = ref({
    pump: false,
    fertilizer: false,
    skylight: false,
  })

  function setWsConnected(val) {
    wsConnected.value = val
  }

  function updateStatus(status) {
    if (status.device_online !== undefined) deviceOnline.value = status.device_online
    if (status.mode) mode.value = status.mode
    if (status.actuators) actuators.value = { ...status.actuators }
  }

  function setMode(m) {
    mode.value = m
  }

  function setActuator(device, val) {
    actuators.value[device] = val
  }

  return {
    wsConnected,
    deviceOnline,
    mode,
    actuators,
    setWsConnected,
    updateStatus,
    setMode,
    setActuator,
  }
})
