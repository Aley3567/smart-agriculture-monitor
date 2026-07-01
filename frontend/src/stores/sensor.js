import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { parseTimestamp } from '../utils/format'
import { DEFAULT_BOARD_ID } from '../utils/constants'
import { SENSOR_FIELDS as DEFAULT_SENSOR_FIELDS } from '../utils/sources'

export const useSensorStore = defineStore('sensor', () => {
  const fields = ref({ ...DEFAULT_SENSOR_FIELDS })
  const currentFacts = ref({})
  const currentMeta = ref({
    board_id: DEFAULT_BOARD_ID,
    source: '',
    bridge_mode: '',
    is_test: false,
    timestamp: null,
  })
  const current = ref({
    temp: null,
    humi: null,
    light: null,
    soil: null,
  })

  const MAX_POINTS = 60
  const MAX_ALARMS = 80
  const history = ref({
    timestamps: [],
    temp: [],
    humi: [],
    light: [],
    soil: [],
  })

  const alarms = ref([])

  const measuredFieldKeys = computed(() => Object.keys(fields.value).filter(key => fields.value[key]?.category === 'measured'))
  const modelFieldKeys = computed(() => Object.keys(fields.value).filter(key => fields.value[key]?.category === 'model'))

  const todayAlarmCount = computed(() => {
    const today = new Date().toDateString()
    return alarms.value.filter(a => parseTimestamp(a.timestamp || a._received)?.toDateString() === today).length
  })

  function setFieldCatalog(catalog = {}) {
    if (!catalog || typeof catalog !== 'object') return
    fields.value = {
      ...fields.value,
      ...catalog,
    }
  }

  function fieldFor(key) {
    return fields.value[key] || DEFAULT_SENSOR_FIELDS[key]
  }

  function fieldForParam(param) {
    return Object.values(fields.value).find(field => field.param === param || field.key === param)
  }

  function catalogFromFacts(facts = {}) {
    return Object.fromEntries(Object.entries(facts)
      .filter(([, fact]) => fact && typeof fact === 'object')
      .map(([key, fact]) => {
        const { value, ...field } = fact
        return [key, { ...field, key: field.key || key }]
      }))
  }

  function valuesFromFacts(facts = {}) {
    return Object.fromEntries(Object.entries(facts)
      .filter(([, fact]) => fact?.available && fact.value !== undefined)
      .map(([key, fact]) => [key, fact.value]))
  }

  function factsFromValues(data = {}) {
    return Object.fromEntries(Object.keys(fields.value).map((key) => {
      const field = fieldFor(key)
      return [key, {
        ...field,
        value: field.available ? (data[key] ?? null) : null,
      }]
    }))
  }

  function updateFacts(data = {}, facts = null) {
    if (facts && typeof facts === 'object') {
      setFieldCatalog(catalogFromFacts(facts))
      currentFacts.value = facts
      return
    }
    currentFacts.value = factsFromValues(data)
  }

  function historyKeysFor(values = {}, rows = []) {
    const keys = new Set(Object.keys(fields.value).filter(key => fields.value[key]?.available))
    Object.keys(values).forEach(key => keys.add(key))
    rows.forEach((row) => {
      Object.keys(row || {}).forEach((key) => {
        if (!['id', 'timestamp', 'board_id', 'facts'].includes(key)) keys.add(key)
      })
      Object.entries(row?.facts || {}).forEach(([key, fact]) => {
        if (fact?.available) keys.add(key)
      })
    })
    return [...keys]
  }

  function rowValue(row = {}, key) {
    if (row[key] !== undefined) return row[key]
    const fact = row.facts?.[key]
    if (fact && fact.value !== undefined) return fact.value
    return null
  }

  function metaFromSample(sample = {}, timestamp = null) {
    return {
      board_id: sample.board_id || DEFAULT_BOARD_ID,
      source: sample.source || '',
      bridge_mode: sample.bridge_mode || '',
      is_test: Boolean(sample.is_test),
      timestamp: sample.timestamp || timestamp || null,
    }
  }

  function pushHistoryPoint(values, timestamp) {
    const previousLength = history.value.timestamps.length
    historyKeysFor(values).forEach((key) => {
      if (!Array.isArray(history.value[key])) {
        history.value[key] = Array(previousLength).fill(null)
      }
    })

    history.value.timestamps.push(timestamp)
    Object.keys(history.value).forEach((key) => {
      if (key === 'timestamps') return
      history.value[key].push(values[key] ?? null)
    })

    if (history.value.timestamps.length > MAX_POINTS) {
      Object.keys(history.value).forEach((key) => {
        history.value[key].shift()
      })
    }
  }

  function updateSensorData(data, timestamp, facts = null, catalog = null, meta = {}) {
    setFieldCatalog(catalog)
    const values = { ...data, ...valuesFromFacts(facts || {}) }
    current.value = { ...current.value, ...values }
    updateFacts(current.value, facts)
    currentMeta.value = metaFromSample(meta, timestamp)

    const ts = timestamp || new Date().toISOString()
    pushHistoryPoint(values, ts)
  }

  function addAlarm(alarm) {
    alarms.value.unshift({
      ...alarm,
      _received: new Date().toISOString(),
    })
    if (alarms.value.length > MAX_ALARMS) {
      alarms.value.splice(MAX_ALARMS)
    }
  }

  function hydrateSamples(rows = [], catalog = null) {
    setFieldCatalog(catalog)
    const normalized = [...rows].filter(Boolean)
    normalized.forEach((item) => updateFacts(current.value, item.facts))

    const keys = historyKeysFor({}, normalized)
    history.value = { timestamps: normalized.map(item => item.timestamp) }
    keys.forEach((key) => {
      history.value[key] = normalized.map(item => rowValue(item, key))
    })

    const latest = normalized.at(-1)
    if (latest) {
      const latestValues = Object.fromEntries(keys.map(key => [key, rowValue(latest, key)]))
      current.value = {
        ...current.value,
        ...latestValues,
      }
      updateFacts(current.value, latest.facts)
      currentMeta.value = metaFromSample(latest)
    }
  }

  return {
    fields,
    currentFacts,
    currentMeta,
    current,
    history,
    alarms,
    measuredFieldKeys,
    modelFieldKeys,
    todayAlarmCount,
    setFieldCatalog,
    fieldFor,
    fieldForParam,
    updateSensorData,
    addAlarm,
    hydrateSamples,
  }
})
