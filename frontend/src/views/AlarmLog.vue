<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useSensorStore } from '../stores/sensor'

const sensorStore = useSensorStore()
const dateRange = ref([])
const tableData = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const loading = ref(false)

const PARAM_LABEL = {
  temperature: '温度',
  humidity: '湿度',
  light: '光照',
  soil_moisture: '土壤湿度',
  temp: '温度',
  humi: '湿度',
}

const ACTION_LABEL = {
  BLEKLED1: '开启报警灯',
  BLEKLED0: '关闭报警灯',
  BUZZER1: '开启蜂鸣器',
  BUZZER0: '关闭蜂鸣器',
}

onMounted(() => {
  const now = new Date()
  const start = new Date(now)
  start.setHours(0, 0, 0, 0)
  dateRange.value = [start, now]
  fetchAlarms()
})

async function fetchAlarms() {
  if (!dateRange.value || dateRange.value.length < 2) return
  loading.value = true
  try {
    const [start, end] = dateRange.value
    const res = await axios.get('http://localhost:8000/api/alarms', {
      params: {
        start: start.toISOString(),
        end: end.toISOString(),
        page: currentPage.value,
        page_size: pageSize.value,
      },
    })
    tableData.value = res.data.data
    total.value = res.data.total
  } catch {
    tableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handlePageChange(page) {
  currentPage.value = page
  fetchAlarms()
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}
</script>

<template>
  <div class="alarm-page">
    <div class="stat-row">
      <el-card class="stat-card">
        <div class="stat-value">{{ sensorStore.todayAlarmCount }}</div>
        <div class="stat-label">今日报警次数</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-value">{{ total }}</div>
        <div class="stat-label">查询结果总数</div>
      </el-card>
    </div>

    <el-card class="filter-card">
      <div class="filter-row">
        <el-date-picker
          v-model="dateRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          @change="fetchAlarms"
        />
        <el-button type="primary" @click="fetchAlarms" :loading="loading">查询</el-button>
      </div>
    </el-card>

    <el-card class="table-card">
      <template #header><span class="card-title">报警记录</span></template>
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="timestamp" label="时间" width="200">
          <template #default="{ row }">{{ formatTime(row.timestamp) }}</template>
        </el-table-column>
        <el-table-column prop="param" label="参数名" width="120">
          <template #default="{ row }">{{ PARAM_LABEL[row.param] || row.param }}</template>
        </el-table-column>
        <el-table-column prop="value" label="触发值" width="120" />
        <el-table-column prop="threshold" label="阈值" width="120" />
        <el-table-column prop="action" label="执行动作" width="160">
          <template #default="{ row }">{{ ACTION_LABEL[row.action] || row.action }}</template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.alarm-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  max-width: 400px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: var(--accent);
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.card-title {
  color: var(--accent);
  font-size: 16px;
  font-weight: 600;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
