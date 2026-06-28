<script setup>
import { useSensorStore } from '../stores/sensor'
import { useSystemStore } from '../stores/system'
import { sendMessage } from '../utils/websocket'
import GaugeChart from '../components/GaugeChart.vue'
import TrendChart from '../components/TrendChart.vue'
import axios from 'axios'

const sensorStore = useSensorStore()
const systemStore = useSystemStore()

const ACTUATOR_LABELS = {
  pump: '水泵',
  fertilizer: '施肥',
  skylight: '天窗',
}

async function handleActuatorChange(device, val) {
  const action = val ? 'on' : 'off'
  try {
    await axios.post('http://localhost:8000/api/control', { device, action })
    sendMessage({ type: 'control', device, action })
    systemStore.setActuator(device, val)
  } catch {
    systemStore.setActuator(device, !val)
  }
}
</script>

<template>
  <div class="dashboard">
    <div class="gauge-row">
      <el-card class="gauge-card">
        <GaugeChart title="温度" :value="sensorStore.current.temp" :min="-10" :max="50" unit="°C" color="#f56c6c" />
      </el-card>
      <el-card class="gauge-card">
        <GaugeChart title="湿度" :value="sensorStore.current.humi" :min="0" :max="100" unit="%" color="#409eff" />
      </el-card>
      <el-card class="gauge-card">
        <GaugeChart title="光照" :value="sensorStore.current.light" :min="0" :max="2000" unit="lux" color="#e6a23c" />
      </el-card>
      <el-card class="gauge-card">
        <GaugeChart title="土壤湿度" :value="sensorStore.current.soil" :min="0" :max="100" unit="%" color="#67c23a" />
      </el-card>
    </div>

    <div class="bottom-row">
      <el-card class="trend-card">
        <template #header>
          <span class="card-title">实时趋势</span>
        </template>
        <TrendChart
          :timestamps="sensorStore.history.timestamps"
          :tempData="sensorStore.history.temp"
          :humiData="sensorStore.history.humi"
          :lightData="sensorStore.history.light"
          :soilData="sensorStore.history.soil"
        />
      </el-card>

      <el-card class="actuator-card">
        <template #header>
          <div class="actuator-header">
            <span class="card-title">执行器控制</span>
            <el-tag :type="systemStore.mode === 'auto' ? 'success' : 'warning'" size="small">
              {{ systemStore.mode === 'auto' ? '自动模式' : '手动模式' }}
            </el-tag>
          </div>
        </template>
        <div class="actuator-list">
          <div v-for="(label, key) in ACTUATOR_LABELS" :key="key" class="actuator-item">
            <span class="actuator-label">{{ label }}</span>
            <el-switch
              :model-value="systemStore.actuators[key]"
              @change="(val) => handleActuatorChange(key, val)"
              active-color="#00d4ff"
              inactive-color="#2a3a5a"
            />
            <span class="actuator-status" :class="systemStore.actuators[key] ? 'on' : 'off'">
              {{ systemStore.actuators[key] ? '运行中' : '已关闭' }}
            </span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.gauge-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.gauge-card {
  text-align: center;
}

.bottom-row {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 16px;
}

.card-title {
  color: var(--accent);
  font-size: 16px;
  font-weight: 600;
}

.actuator-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.actuator-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.actuator-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.actuator-label {
  font-size: 14px;
  color: var(--text-primary);
  min-width: 40px;
}

.actuator-status {
  font-size: 12px;
  min-width: 50px;
  text-align: right;
}

.actuator-status.on {
  color: var(--accent);
}

.actuator-status.off {
  color: var(--text-secondary);
}
</style>
