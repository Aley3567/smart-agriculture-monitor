<script setup>
import { computed, onMounted, ref } from 'vue'
import { useSensorStore } from '../stores/sensor'
import { usePaginatedFetch } from '../composables/usePaginatedFetch'
import api from '../utils/api'
import { ACTION_LABEL, PARAM_LABEL, PARAM_UNIT } from '../utils/constants'
import { formatDateTime } from '../utils/format'
import { sourceMeta } from '../utils/sources'

const { dateRange, tableData, total, currentPage, pageSize, queryParams, fetch: fetchAlarms, handlePageChange } =
  usePaginatedFetch('/api/alarms')

const sensorStore = useSensorStore()
pageSize.value = 10

const summary = ref({ total: 0, today: 0, last_24h: 0, by_param: {}, latest: null })
const rangeKey = ref('24h')
const levelFilter = ref('')
const dataSourceFilter = ref('all')
const sourceFilter = ref('')
const statusFilter = ref('')
const searchKeyword = ref('')
const selectedId = ref(null)

const RANGE_PRESETS = {
  '24h': { label: '近 24 小时', ms: 24 * 3600 * 1000 },
  '7d': { label: '近 7 天', ms: 7 * 24 * 3600 * 1000 },
  '30d': { label: '近 30 天', ms: 30 * 24 * 3600 * 1000 },
}

const DATA_SOURCE_FILTERS = [
  { value: 'all', label: '全部' },
  { value: 'real', label: '真实告警' },
  { value: 'test', label: '测试告警' },
]

const kpis = computed(() => {
  const dist = sourceDistribution.value
  return [
    { label: '今日告警', value: summary.value.today || 0, tone: 'red', note: '后端统计' },
    { label: '未确认', value: '—', tone: 'orange', note: '后端未提供状态字段' },
    { label: '模型告警', value: dist.model || 0, tone: 'green', note: '当前页来源估算' },
    { label: '实测告警', value: dist.measured || 0, tone: 'blue', note: '当前页来源估算' },
    { label: '自动控制', value: '—', tone: 'purple', note: '控制日志单独查询' },
  ]
})

const rows = computed(() => tableData.value.map((item) => {
  const direction = item.value < item.threshold ? 'low' : 'high'
  const source = sourceForParam(item.param_name)
  const level = levelOf(item)
  return {
    id: item.id,
    time: formatDateTime(item.timestamp),
    level,
    levelLabel: level === 'high' ? '高' : '中',
    source,
    sourceKind: sourceKindOf(source),
    sourceRaw: item.source || 'bridge',
    bridgeMode: item.bridge_mode || 'unknown',
    isTest: Boolean(item.is_test),
    sensorDataId: item.sensor_data_id,
    param: PARAM_LABEL[item.param_name] || item.param_name,
    paramRaw: item.param_name,
    value: `${item.value}${unitOf(item.param_name)}`,
    threshold: `${direction === 'low' ? '<' : '>'} ${item.threshold}${unitOf(item.param_name)}`,
    action: ACTION_LABEL[item.action] || item.action,
    status: '状态未接入',
    direction,
    raw: item,
  }
}))

const filteredRows = computed(() => rows.value.filter((row) => {
  if (levelFilter.value && row.level !== levelFilter.value) return false
  if (sourceFilter.value && row.sourceKind !== sourceFilter.value) return false
  if (statusFilter.value && statusFilter.value !== 'pending') return false
  const keyword = searchKeyword.value.trim()
  if (keyword && !`${row.param}${row.action}${row.time}`.includes(keyword)) return false
  return true
}))

const selected = computed(() => {
  if (!filteredRows.value.length) return null
  return filteredRows.value.find(r => r.id === selectedId.value) || filteredRows.value[0]
})

const rangeText = computed(() => {
  if (!dateRange.value || dateRange.value.length < 2) return ''
  return `${formatDateTime(dateRange.value[0])} ~ ${formatDateTime(dateRange.value[1])}`
})

const totalPages = computed(() => Math.max(1, Math.ceil((total.value || 0) / pageSize.value)))

const sourceDistribution = computed(() => {
  const out = { measured: 0, model: 0, control: 0, system: 0, api: 0 }
  rows.value.forEach((row) => {
    out[row.sourceKind] = (out[row.sourceKind] || 0) + 1
  })
  return out
})

const histogram = computed(() => {
  const buckets = new Map()
  rows.value.forEach((row) => {
    const hour = row.time.slice(11, 13)
    buckets.set(hour, (buckets.get(hour) || 0) + 1)
  })
  return [...buckets.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([hour, count]) => ({ hour: `${hour}:00`, count }))
})

function unitOf(param) {
  return PARAM_UNIT[param] || ''
}

function levelOf(row) {
  const unit = Math.abs(Number(row.value) - Number(row.threshold))
  if (row.param_name === 'temperature' && unit >= 3) return 'high'
  if (row.param_name === 'soil_moisture' && unit >= 5) return 'high'
  return row.value > row.threshold ? 'high' : 'medium'
}

function sourceForParam(param) {
  const field = sensorStore.fieldForParam(param)
  if (field) return sourceMeta(field.source)
  return sourceMeta('system')
}

function sourceKindOf(source) {
  if (source.label === '实测') return 'measured'
  if (source.label === '板端模拟') return 'measured'
  if (source.label === '模型') return 'model'
  if (source.label === '控制') return 'control'
  if (source.label === '气象接口') return 'api'
  return 'system'
}

function bridgeModeText(mode) {
  if (mode === 'hardware') return '真实串口'
  if (mode === 'mock') return '模拟数据'
  if (mode === 'test_injection') return '测试注入'
  return '历史未知'
}

function barHeight(count) {
  const max = Math.max(1, ...histogram.value.map(i => i.count))
  return `${Math.max(8, (count / max) * 110)}px`
}

function applyRange(key) {
  rangeKey.value = key
  const end = new Date()
  const start = new Date(end.getTime() - RANGE_PRESETS[key].ms)
  dateRange.value = [start, end]
  currentPage.value = 1
  queryParams.value = { source: dataSourceFilter.value }
  fetchAlarms()
}

function applyDataSourceFilter(value) {
  dataSourceFilter.value = value
  currentPage.value = 1
  queryParams.value = { source: value }
  fetchAlarms()
}

async function fetchSummary() {
  try {
    const res = await api.get('/api/alarms/summary')
    summary.value = res.data
  } catch { /* keep current */ }
}

async function fetchSensorFields() {
  try {
    const res = await api.get('/api/sensor-fields')
    sensorStore.setFieldCatalog(res.data)
  } catch { /* keep fallback catalog */ }
}

function refresh() {
  fetchSensorFields()
  fetchAlarms()
  fetchSummary()
}

function resetFilters() {
  levelFilter.value = ''
  dataSourceFilter.value = 'all'
  sourceFilter.value = ''
  statusFilter.value = ''
  searchKeyword.value = ''
  currentPage.value = 1
  queryParams.value = { source: dataSourceFilter.value }
  fetchAlarms()
}

function selectRow(id) {
  selectedId.value = id
}

onMounted(() => {
  fetchSensorFields()
  applyRange('24h')
  fetchSummary()
})
</script>

<template>
  <div class="alarm-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">告警日志</h1>
        <p class="page-subtitle">按来源追溯告警、阈值规则和控制动作</p>
      </div>
      <button class="btn btn-primary" type="button" @click="refresh">刷新日志</button>
    </header>

    <section class="card filter-card">
      <div class="filter-range">
        <label>时间范围</label>
        <div class="range-tabs">
          <button v-for="(preset, key) in RANGE_PRESETS" :key="key" type="button" :class="{ active: rangeKey === key }" @click="applyRange(key)">
            {{ preset.label }}
          </button>
        </div>
        <span>{{ rangeText }}</span>
      </div>
      <div class="filter-range compact">
        <label>告警来源</label>
        <div class="range-tabs">
          <button
            v-for="item in DATA_SOURCE_FILTERS"
            :key="item.value"
            type="button"
            :class="{ active: dataSourceFilter === item.value }"
            @click="applyDataSourceFilter(item.value)"
          >
            {{ item.label }}
          </button>
        </div>
      </div>
      <label>级别
        <select v-model="levelFilter">
          <option value="">全部</option>
          <option value="high">高</option>
          <option value="medium">中</option>
        </select>
      </label>
      <label>来源类型
        <select v-model="sourceFilter">
          <option value="">全部</option>
          <option value="measured">实测</option>
          <option value="model">模型</option>
          <option value="control">控制</option>
          <option value="system">系统</option>
          <option value="api">气象接口</option>
        </select>
      </label>
      <label>状态
        <select v-model="statusFilter">
          <option value="">全部</option>
          <option value="pending">状态未接入</option>
        </select>
      </label>
      <input v-model="searchKeyword" class="field search-field" type="text" placeholder="输入指标或告警内容">
      <button class="btn btn-soft" type="button" @click="resetFilters">重置</button>
    </section>

    <section class="kpi-row">
      <article v-for="item in kpis" :key="item.label" class="card kpi-card" :class="item.tone">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <p>{{ item.note }}</p>
      </article>
    </section>

    <div class="alarm-layout">
      <main class="alarm-main">
        <section class="card table-panel">
          <h2 class="section-title">告警记录</h2>
          <div class="table-scroll">
            <table class="data-table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>级别</th>
                  <th>指标</th>
                  <th class="col-number">当前值</th>
                  <th class="col-number">阈值</th>
                  <th>来源</th>
                  <th>处理状态</th>
                  <th>触发动作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!filteredRows.length">
                  <td colspan="8" class="empty-cell">该范围内暂无匹配告警</td>
                </tr>
                <tr v-for="row in filteredRows" :key="row.id" :class="{ selected: row.id === selected?.id }" @click="selectRow(row.id)">
                  <td>{{ row.time }}</td>
                  <td><span class="level-dot" :class="row.level"></span>{{ row.levelLabel }}</td>
                  <td>{{ row.param }}</td>
                  <td class="col-number value-cell" :class="{ red: row.level === 'high' }">{{ row.value }}</td>
                  <td class="col-number">{{ row.threshold }}</td>
                  <td>
                    <b class="source-badge" :class="row.source.className">{{ row.source.label }}</b>
                    <b v-if="row.isTest" class="injection-tag">测试注入</b>
                  </td>
                  <td><b class="source-badge source-pending">{{ row.status }}</b></td>
                  <td>{{ row.action }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="pagination" v-if="total > 0">
            <span>共 {{ total }} 条</span>
            <button type="button" :disabled="currentPage <= 1" @click="handlePageChange(currentPage - 1)">‹</button>
            <button class="active" type="button">{{ currentPage }} / {{ totalPages }}</button>
            <button type="button" :disabled="currentPage >= totalPages" @click="handlePageChange(currentPage + 1)">›</button>
          </div>
        </section>

        <div class="chart-row">
          <section class="card dist-card">
            <h2 class="section-title">告警来源分布</h2>
            <div class="donut">
              <strong>{{ rows.length }}</strong>
              <span>当前页</span>
            </div>
            <ul>
              <li><i class="measured"></i>实测 {{ sourceDistribution.measured || 0 }}</li>
              <li><i class="model"></i>模型 {{ sourceDistribution.model || 0 }}</li>
              <li><i class="control"></i>控制 {{ sourceDistribution.control || 0 }}</li>
              <li><i class="system"></i>系统 {{ sourceDistribution.system || 0 }}</li>
            </ul>
          </section>

          <section class="card trend-card">
            <h2 class="section-title">近范围告警趋势</h2>
            <div class="bars">
              <article v-if="!histogram.length" class="bar-empty">暂无数据</article>
              <article v-for="item in histogram" :key="item.hour">
                <span :style="{ height: barHeight(item.count) }"></span>
                <b>{{ item.count }}</b>
                <small>{{ item.hour }}</small>
              </article>
            </div>
          </section>
        </div>
      </main>

      <aside class="alarm-side card">
        <template v-if="selected">
          <div class="detail-head">
            <h2 class="section-title">告警详情</h2>
            <b class="source-badge source-pending">状态未接入</b>
          </div>
          <dl>
            <div><dt>告警内容</dt><dd>{{ selected.param }}{{ selected.direction === 'low' ? '低于阈值' : '超过阈值' }}</dd></div>
            <div><dt>来源说明</dt><dd><b class="source-badge" :class="selected.source.className">{{ selected.source.label }}</b></dd></div>
            <div><dt>数据来源</dt><dd>{{ selected.sourceRaw }} · {{ bridgeModeText(selected.bridgeMode) }}<b v-if="selected.isTest" class="injection-tag">测试数据</b></dd></div>
            <div><dt>采样记录</dt><dd>{{ selected.sensorDataId || '未关联' }}</dd></div>
            <div><dt>首次触发</dt><dd>{{ selected.time }}</dd></div>
            <div><dt>最后触发</dt><dd>{{ selected.time }}</dd></div>
            <div><dt>触发次数</dt><dd>后端未统计</dd></div>
          </dl>

          <h3>决策追溯</h3>
          <div class="trace-flow">
            <article><span>输入数据</span><strong>{{ selected.param }} {{ selected.value }}</strong><small>来自{{ selected.source.label }}</small></article>
            <article><span>阈值规则</span><strong>{{ selected.threshold }}</strong><small>thresholds 表</small></article>
            <article><span>动作指令</span><strong>{{ selected.action }}</strong><small>后端 action 字段</small></article>
            <article><span>当前状态</span><strong>待接入</strong><small>缺少处理状态字段</small></article>
          </div>

          <h3>处理记录</h3>
          <div class="records">
            <article><i></i><div><strong>告警写入</strong><span>{{ selected.time }} · FastAPI</span></div></article>
            <article><i class="pending"></i><div><strong>人工确认</strong><span>后端暂未提供确认接口</span></div></article>
          </div>
          <div class="detail-actions">
            <button class="btn btn-primary" type="button">确认告警</button>
            <button class="btn btn-soft" type="button">标记已恢复</button>
          </div>
        </template>
        <p v-else class="empty-cell">选择左侧记录查看详情</p>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.alarm-page {
  max-width: 1600px;
  margin: 0 auto;
}

.page-head,
.filter-card,
.filter-range,
.range-tabs,
.kpi-row,
.detail-head,
.chart-row {
  display: flex;
  align-items: center;
}

.page-head {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.filter-card {
  gap: 16px;
  padding: 14px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filter-card label,
.filter-range label {
  display: grid;
  gap: 6px;
  color: #475569;
  font-size: 12px;
  font-weight: 750;
}

.filter-range {
  gap: 12px;
  flex: 1;
}

.filter-range.compact {
  flex: 0 1 auto;
}

.range-tabs {
  overflow: hidden;
  border: 1px solid var(--border-light);
  border-radius: 7px;
}

.range-tabs button {
  height: 36px;
  min-width: 96px;
  border: 0;
  border-right: 1px solid var(--border-light);
  background: #fff;
  color: #334155;
  font-weight: 650;
}

.range-tabs button:last-child {
  border-right: 0;
}

.range-tabs .active {
  background: #e9f8ee;
  color: #0a9b45;
  font-weight: 800;
}

.filter-range span {
  color: #64748b;
  font-family: var(--font-mono);
  font-size: 12px;
}

.filter-card select {
  width: 120px;
  height: 36px;
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 0 10px;
  background: #fff;
}

.search-field {
  width: 260px;
  margin-top: 22px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.kpi-card {
  min-height: 108px;
  display: grid;
  gap: 8px;
  padding: 18px;
}

.kpi-card span {
  color: #475569;
  font-weight: 750;
}

.kpi-card strong {
  font-size: 30px;
  line-height: 1;
  font-weight: 850;
}

.kpi-card p {
  color: #64748b;
  font-size: 12px;
}

.kpi-card.red strong { color: #ef4444; }
.kpi-card.orange strong { color: #f97316; }
.kpi-card.green strong { color: #16a34a; }
.kpi-card.blue strong { color: #2563eb; }
.kpi-card.purple strong { color: #7c3aed; }

.alarm-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 520px;
  gap: 16px;
  align-items: start;
}

.alarm-main {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.table-panel,
.dist-card,
.trend-card,
.alarm-side {
  padding: 18px;
}

.table-panel h2 {
  margin-bottom: 14px;
}

.data-table tbody tr {
  cursor: pointer;
}

.data-table tr.selected td {
  background: #eff6ff;
  border-top: 1px solid #bfdbfe;
  border-bottom: 1px solid #bfdbfe;
}

.level-dot {
  width: 8px;
  height: 8px;
  display: inline-block;
  margin-right: 8px;
  border-radius: 50%;
  background: #f97316;
}

.level-dot.high {
  background: #ef4444;
}

.value-cell.red {
  color: #ef4444;
  font-weight: 850;
}

.injection-tag {
  display: inline-flex;
  align-items: center;
  height: 22px;
  margin-left: 8px;
  padding: 0 8px;
  border: 1px solid #fed7aa;
  border-radius: 999px;
  background: #fff7ed;
  color: #c2410c;
  font-size: 12px;
  font-weight: 800;
  vertical-align: middle;
}

.empty-cell {
  text-align: center;
  color: #64748b;
  padding: 18px 0;
}

.chart-row {
  align-items: stretch;
  gap: 16px;
}

.dist-card {
  width: 320px;
}

.dist-card h2,
.trend-card h2 {
  margin-bottom: 14px;
}

.donut {
  width: 150px;
  height: 150px;
  display: grid;
  place-content: center;
  margin: 12px auto;
  border: 22px solid #22c55e;
  border-left-color: #8b5cf6;
  border-bottom-color: #86efac;
  border-radius: 50%;
  text-align: center;
}

.donut strong {
  font-size: 30px;
}

.donut span {
  color: #64748b;
  font-size: 12px;
}

.dist-card ul {
  display: grid;
  gap: 9px;
  list-style: none;
}

.dist-card li {
  color: #334155;
  font-weight: 650;
}

.dist-card i {
  width: 8px;
  height: 8px;
  display: inline-block;
  margin-right: 8px;
  border-radius: 50%;
}

.dist-card i.measured { background: #2563eb; }
.dist-card i.model { background: #16a34a; }
.dist-card i.control { background: #7c3aed; }
.dist-card i.system { background: #94a3b8; }

.trend-card {
  flex: 1;
}

.bars {
  height: 190px;
  display: flex;
  align-items: flex-end;
  gap: 14px;
  padding: 16px 8px 4px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
  overflow-x: auto;
}

.bars article {
  min-width: 46px;
  display: grid;
  justify-items: center;
  gap: 6px;
}

.bars span {
  width: 16px;
  border-radius: 999px 999px 0 0;
  background: #16a34a;
}

.bars b {
  color: #17223b;
  font-size: 12px;
}

.bars small {
  color: #64748b;
  font-size: 11px;
}

.bar-empty {
  align-self: center;
  color: #64748b;
}

.alarm-side {
  position: sticky;
  top: 86px;
}

.detail-head {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.alarm-side dl {
  display: grid;
  gap: 10px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-light);
}

.alarm-side dl div {
  display: grid;
  grid-template-columns: 86px 1fr;
  gap: 10px;
}

.alarm-side dt {
  color: #64748b;
}

.alarm-side dd {
  color: #17223b;
  font-weight: 650;
}

.alarm-side h3 {
  margin: 18px 0 12px;
  color: #17223b;
  font-size: 16px;
}

.trace-flow {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.trace-flow article {
  display: grid;
  gap: 6px;
  min-height: 112px;
  padding: 12px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
  background: #fff;
}

.trace-flow span {
  color: #2563eb;
  font-weight: 800;
}

.trace-flow strong {
  color: #17223b;
}

.trace-flow small {
  color: #64748b;
}

.records {
  display: grid;
  gap: 12px;
}

.records article {
  display: flex;
  gap: 10px;
}

.records i {
  width: 10px;
  height: 10px;
  margin-top: 5px;
  border-radius: 50%;
  background: #f97316;
}

.records i.pending {
  background: #2563eb;
}

.records div {
  display: grid;
  gap: 3px;
}

.records span {
  color: #64748b;
  font-size: 13px;
}

.detail-actions {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}

@media (max-width: 1320px) {
  .alarm-layout {
    grid-template-columns: 1fr;
  }

  .alarm-side {
    position: static;
  }
}

@media (max-width: 1100px) {
  .kpi-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .chart-row,
  .filter-card {
    align-items: stretch;
    flex-direction: column;
  }

  .dist-card {
    width: auto;
  }
}

@media (max-width: 760px) {
  .page-head,
  .filter-range,
  .detail-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .kpi-row,
  .trace-flow {
    grid-template-columns: 1fr;
  }

  .search-field {
    width: 100%;
    margin-top: 0;
  }
}
</style>
