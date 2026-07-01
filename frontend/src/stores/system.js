import { defineStore } from 'pinia'
import { ref } from 'vue'
import { DEFAULT_BOARD_ID } from '../utils/constants'

export const useSystemStore = defineStore('system', () => {
  const currentBoardId = ref(DEFAULT_BOARD_ID)
  const wsConnected = ref(false)
  const deviceOnline = ref(false)
  const mode = ref('auto')
  const actuators = ref({
    pump: false,
    fertilizer: false,
    pest_light: false,
  })
  const autoWatering = ref({})
  const boards = ref({})
  const debugEvents = ref([])

  function setWsConnected(val) {
    wsConnected.value = val
  }

  function updateStatus(status) {
    if (status.device_online !== undefined) deviceOnline.value = status.device_online
    if (status.mode) mode.value = status.mode
    if (status.actuators) actuators.value = { ...status.actuators }
    if (status.boards) boards.value = { ...status.boards }
    if (status.auto_watering) autoWatering.value = { ...status.auto_watering }
    if (Array.isArray(status.debug_events)) debugEvents.value = status.debug_events.slice(0, 80)
  }

  function setMode(m) {
    mode.value = m
  }

  function setCurrentBoardId(boardId) {
    currentBoardId.value = boardId || DEFAULT_BOARD_ID
  }

  function setActuator(device, val) {
    actuators.value[device] = val
  }

  function setDebugEvents(events = []) {
    debugEvents.value = Array.isArray(events) ? events.slice(0, 80) : []
  }

  function addDebugEvent(event) {
    if (!event) return
    debugEvents.value = [event, ...debugEvents.value].slice(0, 80)
  }

  return {
    currentBoardId,
    wsConnected,
    deviceOnline,
    mode,
    actuators,
    autoWatering,
    boards,
    debugEvents,
    setWsConnected,
    updateStatus,
    setMode,
    setCurrentBoardId,
    setActuator,
    setDebugEvents,
    addDebugEvent,
  }
})
