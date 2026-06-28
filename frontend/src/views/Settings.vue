<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useSystemStore } from '../stores/system'
import { ElMessage } from 'element-plus'

const systemStore = useSystemStore()
const loading = ref(false)
const saving = ref(false)

const thresholds = ref({
  temperature: { min: 0, max: 40 },
  humidity: { min: 20, max: 90 },
  light: { min: 100, max: 1500 },
  soil_moisture: { min: 20, max: 80 },
})

const PARAM_LABELS = {
  temperature: '温度 (°C)',
  humidity: '湿度 (%)',
  light: '光照 (lux)',
  soil_moisture: '土壤湿度 (%)',
}

onMounted(async () => {
  loading.value = true
  try {
    const [thRes, stRes] = await Promise.all([
      axios.get('http://localhost:8000/api/thresholds'),
      axios.get('http://localhost:8000/api/status'),
    ])

    if (Array.isArray(thRes.data)) {
      thRes.data.forEach(item => {
        if (thresholds.value[item.param_name]) {
          thresholds.value[item.param_name].min = item.min_value
          thresholds.value[item.param_name].max = item.max_value
        }
      })
    }

    systemStore.updateStatus(stRes.data)
  } catch {
    // keep defaults
  } finally {
    loading.value = false
  }
})

async function saveThresholds() {
  saving.value = true
  try {
    const payload = Object.entries(thresholds.value).map(([name, val]) => ({
      param_name: name,
      min_value: val.min,
      max_value: val.max,
    }))
    await axios.put('http://localhost:8000/api/thresholds', payload)
    ElMessage.success('阈值保存成功')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleMode(val) {
  const newMode = val ? 'auto' : 'manual'
  try {
    await axios.put('http://localhost:8000/api/mode', { mode: newMode })
    systemStore.setMode(newMode)
    ElMessage.success(`已切换到${newMode === 'auto' ? '自动' : '手动'}模式`)
  } catch {
    ElMessage.error('模式切换失败')
  }
}
</script>

<template>
  <div class="settings-page" v-loading="loading">
    <el-card class="settings-card">
      <template #header><span class="card-title">报警阈值设置</span></template>
      <el-form label-width="140px" label-position="left">
        <el-form-item v-for="(val, key) in thresholds" :key="key" :label="PARAM_LABELS[key]">
          <div class="threshold-row">
            <span class="threshold-label">最小值</span>
            <el-input-number v-model="val.min" :step="1" controls-position="right" size="default" />
            <span class="threshold-label">最大值</span>
            <el-input-number v-model="val.max" :step="1" controls-position="right" size="default" />
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveThresholds" :loading="saving">保存阈值</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="settings-card">
      <template #header><span class="card-title">运行模式</span></template>
      <div class="mode-row">
        <span class="mode-label">当前模式</span>
        <el-switch
          :model-value="systemStore.mode === 'auto'"
          @change="toggleMode"
          active-text="自动"
          inactive-text="手动"
          active-color="#00d4ff"
          inactive-color="#e6a23c"
        />
        <el-tag :type="systemStore.mode === 'auto' ? 'success' : 'warning'" size="large">
          {{ systemStore.mode === 'auto' ? '自动模式' : '手动模式' }}
        </el-tag>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 700px;
}

.threshold-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.threshold-label {
  font-size: 13px;
  color: var(--text-secondary);
  min-width: 42px;
}

.mode-row {
  display: flex;
  align-items: center;
  gap: 20px;
}

.mode-label {
  font-size: 14px;
  color: var(--text-primary);
}
</style>
