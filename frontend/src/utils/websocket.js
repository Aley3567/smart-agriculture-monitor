import { useSensorStore } from '../stores/sensor'
import { useSystemStore } from '../stores/system'
import { ElNotification } from 'element-plus'
import { PARAM_LABEL } from './constants'

let ws = null
let reconnectTimer = null
const RECONNECT_INTERVAL = 3000

export function connectWebSocket() {
  const url = `ws://localhost:8000/ws/data`

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
      ElNotification({
        title: '报警通知',
        message: `${PARAM_LABEL[msg.param] || msg.param} 当前值 ${msg.value}，超过阈值 ${msg.threshold}`,
        type: 'warning',
        duration: 5000,
      })
    } else if (msg.type === 'status') {
      systemStore.updateStatus(msg)
    }
  }

  ws.onclose = () => {
    const systemStore = useSystemStore()
    systemStore.setWsConnected(false)
    reconnectTimer = setTimeout(connectWebSocket, RECONNECT_INTERVAL)
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
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
}
