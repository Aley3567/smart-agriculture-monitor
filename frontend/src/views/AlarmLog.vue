<script setup>
import { onMounted } from 'vue'
import { useSensorStore } from '../stores/sensor'
import { PARAM_LABEL, ACTION_LABEL } from '../utils/constants'
import { formatDateTime } from '../utils/format'
import { usePaginatedFetch } from '../composables/usePaginatedFetch'

const sensorStore = useSensorStore()
const { dateRange, tableData, total, currentPage, pageSize, loading, fetch: fetchAlarms, handlePageChange } =
  usePaginatedFetch('http://localhost:8000/api/alarms')

onMounted(() => {
  const now = new Date()
  const start = new Date(now)
  start.setHours(0, 0, 0, 0)
  dateRange.value = [start, now]
  fetchAlarms()
})
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
          <template #default="{ row }">{{ formatDateTime(row.timestamp) }}</template>
        </el-table-column>
        <el-table-column prop="param" label="参数名" width="120">
          <template #default="{ row }">{{ PARAM_LABEL[row.param_name] || row.param_name }}</template>
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

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
