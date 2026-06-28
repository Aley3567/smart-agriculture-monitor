import { useSensorStore } from '../stores/sensor'
import { useSystemStore } from '../stores/system'
import { PARAM_LABEL } from './constants'
import { showToast } from './toast'

let ws = null
let reconnectTimer = null
let manualClose = false
const RECONNECT_INTERVAL = 3000

export function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return
  }

  manualClose = false
  const url = `${import.meta.env.VITE_WS_BASE}/ws/data`

  ws = new WebSocket(url)

  ws.onopen = () => {
    const systemStore = useSystemStore()
    systemStore.setWsConnected(true)
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    const sensorStore = useSensorStore()
    const systemStore = useSystemStore()

    if (msg.type === 'sensor_data') {
      sensorStore.updateSensorData(msg.data, msg.timestamp)
    } else if (msg.type === 'alarm') {
      sensorStore.addAlarm(msg)
      showToast({
        title: '报警通知',
        message: `${PARAM_LABEL[msg.param] || msg.param} 当前值 ${msg.value}，超过阈值 ${msg.threshold}`,
        type: 'warn',
      })
    } else if (msg.type === 'status') {
      systemStore.updateStatus(msg)
    }
  }

  ws.onclose = () => {
    const systemStore = useSystemStore()
    systemStore.setWsConnected(false)
    ws = null
    if (!manualClose) {
      reconnectTimer = setTimeout(connectWebSocket, RECONNECT_INTERVAL)
    }
  }

  ws.onerror = () => {
    ws.close()
  }
}

export function sendMessage(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data))
  }
}

export function disconnectWebSocket() {
  manualClose = true
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
}
