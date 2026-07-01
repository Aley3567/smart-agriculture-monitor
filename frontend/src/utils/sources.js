export const SOURCE_META = {
  measured: { label: '实测', className: 'source-measured', tone: 'blue' },
  measured_adc: { label: 'ADC实测', className: 'source-measured', tone: 'blue' },
  measured_firmware: { label: '板端实测', className: 'source-measured', tone: 'blue' },
  computed_backend: { label: '计算', className: 'source-model', tone: 'green' },
  simulated_backend: { label: '模型', className: 'source-model', tone: 'green' },
  simulated_firmware: { label: '板端模拟', className: 'source-firmware', tone: 'orange' },
  api: { label: '气象接口', className: 'source-api', tone: 'blue' },
  control: { label: '控制', className: 'source-control', tone: 'purple' },
  system: { label: '系统', className: 'source-system', tone: 'gray' },
  bridge_hardware: { label: '真实串口', className: 'source-measured', tone: 'blue' },
  bridge_mock: { label: '模拟数据', className: 'source-test', tone: 'orange' },
  bridge_unknown: { label: '历史未知', className: 'source-pending', tone: 'gray' },
  demo_injection: { label: '测试注入', className: 'source-test', tone: 'orange' },
  pending: { label: '待接入', className: 'source-pending', tone: 'gray' },
}

export const SENSOR_FIELDS = {
  temp: {
    key: 'temp',
    param: 'temperature',
    label: '温度',
    unit: '°C',
    source: 'measured',
    detail: 'DHT11 P2.0',
    category: 'measured',
    color: '#ef4444',
    available: true,
  },
  humi: {
    key: 'humi',
    param: 'humidity',
    label: '空气湿度',
    unit: '%',
    source: 'measured',
    detail: 'DHT11 P2.0',
    category: 'measured',
    color: '#2563eb',
    available: true,
  },
  light: {
    key: 'light',
    param: 'light',
    label: '相对光照',
    unit: '相对值',
    source: 'measured',
    detail: 'GL5516 P0.7 ADC 相对光照值',
    category: 'measured',
    color: '#f97316',
    available: true,
  },
  soil: {
    key: 'soil',
    param: 'soil_moisture',
    label: '土壤湿度',
    unit: '%',
    source: 'computed_backend',
    detail: '后端模型推导：由温度、空气湿度、光照推导',
    category: 'model',
    color: '#16a34a',
    available: true,
  },
  co2: {
    key: 'co2',
    param: 'co2',
    label: 'CO2',
    unit: 'ppm',
    source: 'simulated_backend',
    detail: '后端模型模拟 · 由温湿度和光照推导',
    category: 'model',
    color: '#059669',
    available: true,
  },
  soil_ec: {
    key: 'soil_ec',
    param: 'soil_ec',
    label: '土壤EC',
    unit: 'dS/m',
    source: 'computed_backend',
    detail: '后端计算 · 由土壤湿度、温度、空气湿度推导',
    category: 'model',
    color: '#0d9488',
    available: true,
  },
  soil_tds: {
    key: 'soil_tds',
    param: 'soil_tds',
    label: '土壤TDS',
    unit: 'ppm',
    source: 'computed_backend',
    detail: '由土壤EC换算 · TDS = EC * 640',
    category: 'model',
    color: '#0891b2',
    available: true,
  },
  soil_fertility: {
    key: 'soil_fertility',
    param: 'soil_fertility',
    label: '土壤肥力',
    unit: '%',
    source: 'computed_backend',
    detail: '由土壤湿度与EC归一化推导',
    category: 'model',
    color: '#65a30d',
    available: true,
  },
  infrared: {
    key: 'infrared',
    param: 'infrared',
    label: '红外状态',
    unit: '',
    source: 'simulated_backend',
    detail: '后端模拟红外触发状态',
    category: 'model',
    color: '#dc2626',
    available: true,
  },
}

export const MEASURED_FIELD_KEYS = ['temp', 'humi', 'light']
export const MODEL_FIELD_KEYS = ['soil', 'co2', 'soil_ec', 'soil_tds', 'soil_fertility', 'infrared']

export const DEVICE_META = {
  pump: {
    key: 'pump',
    label: '普通浇水泵',
    mode: '自动',
    basis: '土壤湿度 · 板端模拟',
    commandOn: 'BLEGLED1',
    commandOff: 'BLEKLED1',
    pin: 'P0.6',
    role: '控制水泵继电器，执行灌溉',
    source: 'control',
    color: '#2563eb',
  },
  fertilizer: {
    key: 'fertilizer',
    label: '施肥泵/指示',
    mode: '手动优先',
    basis: '土壤肥力/EC · 模型',
    commandOn: 'BLEGLED2',
    commandOff: 'BLEKLED2',
    pin: 'P1.1',
    role: '施肥泵状态指示与控制',
    source: 'control',
    color: '#f97316',
  },
  pest_light: {
    key: 'pest_light',
    label: '灭虫灯/指示',
    mode: '手动控制',
    basis: '红外只告警，不直接等同灭虫灯',
    commandOn: 'BLEGLED3',
    commandOff: 'BLEKLED3',
    pin: 'P1.6',
    role: '灭虫灯继电器输出，驱动杀虫灯',
    source: 'control',
    color: '#7c3aed',
  },
}

export const DEVICE_MAPPINGS = [
  { label: '普通浇水泵继电器', pin: 'P0.6', role: DEVICE_META.pump.role, stateKey: 'pump', command: DEVICE_META.pump.commandOn },
  { label: '普通浇水泵状态指示', pin: 'P1.0', role: '系统运行指示灯', stateKey: 'system', command: '常亮' },
  { label: '施肥泵/指示', pin: 'P1.1', role: DEVICE_META.fertilizer.role, stateKey: 'fertilizer', command: DEVICE_META.fertilizer.commandOn },
  { label: '灭虫灯/指示', pin: 'P1.6', role: DEVICE_META.pest_light.role, stateKey: 'pest_light', command: DEVICE_META.pest_light.commandOn },
]

export function sourceMeta(source) {
  return SOURCE_META[source] || SOURCE_META.pending
}

export function sourceLabel(source) {
  return sourceMeta(source).label
}

export function formatFieldValue(field, value) {
  if (value == null || value === '' || Number.isNaN(Number(value))) return '—'
  if (field === SENSOR_FIELDS.infrared || field?.key === 'infrared') {
    return Number(value) ? '触发' : '未触发'
  }
  if (field?.key === 'light' || field?.key === 'soil_tds' || field?.key === 'co2') {
    return String(Math.round(Number(value)))
  }
  return Number(value).toFixed(1)
}
