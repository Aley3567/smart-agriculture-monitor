import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useSensorStore = defineStore('sensor', () => {
  const current = ref({
    temp: 0,
    humi: 0,
    light: 0,
    soil: 0,
  })

  const MAX_POINTS = 60
  const history = ref({
    timestamps: [],
    temp: [],
    humi: [],
    light: [],
    soil: [],
  })

  const alarms = ref([])

  const todayAlarmCount = computed(() => {
    const today = new Date().toDateString()
    return alarms.value.filter(a => new Date(a.timestamp || a._received).toDateString() === today).length
  })

  function updateSensorData(data, timestamp) {
    current.value = { ...data }

    const ts = timestamp || new Date().toISOString()
    history.value.timestamps.push(ts)
    history.value.temp.push(data.temp)
    history.value.humi.push(data.humi)
    history.value.light.push(data.light)
    history.value.soil.push(data.soil)

    if (history.value.timestamps.length > MAX_POINTS) {
      history.value.timestamps.shift()
      history.value.temp.shift()
      history.value.humi.shift()
      history.value.light.shift()
      history.value.soil.shift()
    }
  }

  function addAlarm(alarm) {
    alarms.value.unshift({
      ...alarm,
      _received: new Date().toISOString(),
    })
  }

  return {
    current,
    history,
    alarms,
    todayAlarmCount,
    updateSensorData,
    addAlarm,
  }
})
