<script setup>
import { computed, onMounted, ref } from 'vue'
import { usePaginatedFetch } from '../composables/usePaginatedFetch'
import api from '../utils/api'
import { PARAM_LABEL, PARAM_UNIT, ACTION_LABEL } from '../utils/constants'
import { formatDateTime } from '../utils/format'

const { dateRange, tableData, total, currentPage, pageSize, fetch: fetchAlarms, handlePageChange } =
  usePaginatedFetch('/api/alarms')

const summary = ref({ total: 0, today: 0, last_24h: 0, by_param: {}, latest: null })
const paramFilter = ref('')
const rangeKey = ref('7d')
const selectedId = ref(null)

const RANGE_PRESETS = {
  '24h': { label: '近 24 小时', ms: 24 * 3600 * 1000 },
  '7d': { label: '近 7 天', ms: 7 * 24 * 3600 * 1000 },
  '30d': { label: '近 30 天', ms: 30 * 24 * 3600 * 1000 },
}

function unitOf(param) {
  return PARAM_UNIT[param] || ''
}

function directionOf(row) {
  return row.value < row.threshold ? 'low' : 'high'
}

const rows = computed(() => tableData.value
  .filter(r => !paramFilter.value || r.param_name === paramFilter.value)
  .map(r => ({
    id: r.id,
    time: formatDateTime(r.timestamp),
    param: PARAM_LABEL[r.param_name] || r.param_name,
    paramRaw: r.param_name,
    value: `${r.value}${unitOf(r.param_name)}`,
    threshold: `${r.value < r.threshold ? '<' : '>'} ${r.threshold}${unitOf(r.param_name)}`,
    action: ACTION_LABEL[r.action] || r.action,
    raw: r,
  })))

const selected = computed(() => {
  const list = rows.value
  if (!list.length) return null
  return list.find(r => r.id === selectedId.value) || list[0]
})

const rangeText = computed(() => {
  if (!dateRange.value || dateRange.value.length < 2) return ''
  return `${formatDateTime(dateRange.value[0])} ~ ${formatDateTime(dateRange.value[1])}`
})

const totalPages = computed(() => Math.max(1, Math.ceil((total.value || 0) / pageSize.value)))

const paramDist = computed(() => Object.entries(summary.value.by_param || {})
  .map(([k, v]) => ({ label: PARAM_LABEL[k] || k, count: v }))
  .sort((a, b) => b.count - a.count))

const adviceMap = {
  temperature: ['核对温室通风与天窗开度', '高温启动降温、低温注意保温', '关注作物耐受温度区间'],
  humidity: ['检查通风与施肥联动是否生效', '湿度过高警惕病害,过低及时补水', '核对湿度传感器是否结露'],
  light: ['强光放下遮阳,弱光开启补光/天窗', '核对光照传感器是否被遮挡', '结合作物需光特性调节'],
  soil_moisture: ['土壤过干及时灌溉,过湿暂停供水', '检查滴灌管路与水泵状态', '按土壤墒情设定灌溉阈值'],
}
const advice = computed(() => {
  const p = selected.value?.paramRaw
  return adviceMap[p] || ['核对对应传感器读数是否正常', '检查相关执行器联动是否生效', '持续关注该参数变化趋势']
})

function applyRange(key) {
  rangeKey.value = key
  const end = new Date()
  const start = new Date(end.getTime() - RANGE_PRESETS[key].ms)
  dateRange.value = [start, end]
  fetchAlarms()
}

async function fetchSummary() {
  try {
    const res = await api.get('/api/alarms/summary')
    summary.value = res.data
  } catch { /* 保持上一次数据 */ }
}

function refresh() {
  fetchAlarms()
  fetchSummary()
}

function selectRow(id) {
  selectedId.value = id
}

onMounted(() => {
  applyRange('7d')
  fetchSummary()
})
</script>

<template>
  <div class="alarm-page">
    <header class="topbar">
      <h1 class="page-title">报警日志</h1>
      <button class="btn btn-primary" type="button" @click="refresh">刷新日志</button>
    </header>

    <div class="alarm-grid">
      <main class="left-stack">
        <section class="summary-row">
          <article class="card summary-card">
            <span>今日报警</span>
            <div><strong class="red">{{ summary.today }}</strong></div>
          </article>
          <article class="card summary-card">
            <span>近 24 小时</span>
            <div><strong class="orange">{{ summary.last_24h }}</strong></div>
          </article>
          <article class="card summary-card">
            <span>累计报警</span>
            <div><strong class="blue">{{ summary.total }}</strong></div>
          </article>
          <article class="card summary-card">
            <span>最常触发</span>
            <div>
              <strong class="green param-strong">{{ paramDist[0]?.label || '—' }}</strong>
              <small v-if="paramDist[0]">{{ paramDist[0].count }} 次</small>
            </div>
          </article>
        </section>

        <section class="card filter-card">
          <div class="filter-group wide">
            <label>时间范围</label>
            <div class="range-tabs">
              <button
                v-for="(preset, key) in RANGE_PRESETS"
                :key="key"
                type="button"
                :class="{ active: rangeKey === key }"
                @click="applyRange(key)"
              >{{ preset.label }}</button>
            </div>
            <small class="range-text">{{ rangeText }}</small>
          </div>
          <div class="filter-group">
            <label>参数类型</label>
            <select v-model="paramFilter" class="select-real">
              <option value="">全部</option>
              <option value="temperature">温度</option>
              <option value="humidity">湿度</option>
              <option value="light">光照</option>
              <option value="soil_moisture">土壤湿度</option>
            </select>
          </div>
          <button class="btn btn-soft query-btn" type="button" @click="refresh">刷新</button>
        </section>

        <section class="card event-card">
        <h2 class="section-title">事件明细</h2>
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>发生时间</th>
                <th>参数类型</th>
                <th class="col-number">触发值</th>
                <th class="col-number">阈值</th>
                <th>执行动作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!rows.length">
                <td colspan="5" class="empty-cell">该时间范围内暂无报警记录</td>
              </tr>
              <tr
                v-for="row in rows"
                :key="row.id"
                :class="{ hot: row.id === selected?.id }"
                @click="selectRow(row.id)"
              >
                <td>{{ row.time }}</td>
                <td>{{ row.param }}</td>
                <td class="col-number">{{ row.value }}</td>
                <td class="col-number">{{ row.threshold }}</td>
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
      </main>

      <aside class="right-stack">
        <section class="card detail-card">
          <div class="detail-head">
            <h2 class="section-title">报警详情</h2>
          </div>
          <template v-if="selected">
            <div class="detail-title">
              <span class="badge" :class="directionOf(selected.raw) === 'low' ? 'badge-info' : 'badge-danger'">
                {{ directionOf(selected.raw) === 'low' ? '偏低' : '偏高' }}
              </span>
              <strong>{{ selected.param }}{{ directionOf(selected.raw) === 'low' ? '低于下限' : '高于上限' }}</strong>
            </div>
            <dl>
              <div><dt>发生时间</dt><dd>{{ selected.time }}</dd></div>
              <div><dt>参数类型</dt><dd>{{ selected.param }}</dd></div>
              <div><dt>触发值</dt><dd>{{ selected.value }}</dd></div>
              <div><dt>阈值</dt><dd>{{ selected.threshold }}</dd></div>
              <div><dt>执行动作</dt><dd>{{ selected.action }}</dd></div>
            </dl>
          </template>
          <p v-else class="empty-cell">选择左侧记录查看详情</p>
        </section>

        <section class="card timeline-card">
          <h2 class="section-title">自动响应</h2>
          <div class="timeline" v-if="selected">
            <div>
              <time>{{ selected.time.slice(11) }}</time>
              <span class="red"></span>
              <strong>报警触发 · {{ selected.param }}{{ directionOf(selected.raw) === 'low' ? '偏低' : '偏高' }}</strong>
            </div>
            <div>
              <time>—</time>
              <span></span>
              <strong>执行动作 · {{ selected.action }}</strong>
            </div>
          </div>
          <p v-else class="empty-cell">—</p>
        </section>

        <section class="card advice-card">
          <h2 class="section-title">处理建议</h2>
          <ul>
            <li v-for="(tip, i) in advice" :key="i">{{ tip }}</li>
          </ul>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.alarm-page {
  max-width: 1320px;
  margin: 0 auto;
}

.topbar,
.summary-card div,
.filter-card,
.date-field,
.detail-head,
.detail-title,
.timeline div {
  display: flex;
  align-items: center;
}

.topbar {
  justify-content: space-between;
  margin-bottom: 18px;
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  height: 92px;
  padding: 16px;
}

.summary-card span {
  display: block;
  color: var(--text-muted);
  font-size: 13px;
}

.summary-card div {
  gap: 14px;
  margin-top: 10px;
}

.summary-card strong {
  font-size: 30px;
  line-height: 1;
}

.summary-card strong.param-strong {
  font-size: 20px;
}

.summary-card small {
  color: var(--text-secondary);
}

.summary-card .red { color: var(--red); }
.summary-card .orange { color: var(--orange); }
.summary-card .blue { color: #1683c7; }
.summary-card .green { color: var(--green); }

.filter-card {
  gap: 18px;
  min-height: 96px;
  padding: 18px;
}

.filter-group {
  display: grid;
  gap: 8px;
}

.filter-group label {
  color: var(--text-muted);
  font-size: 13px;
}

.filter-group.wide {
  flex: 1;
}

.range-tabs {
  display: flex;
  gap: 6px;
}

.range-tabs button {
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #fff;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
}

.range-tabs button.active {
  background: var(--green);
  border-color: var(--green);
  color: #fff;
}

.range-text {
  color: var(--text-muted);
  font-size: 11px;
  font-family: var(--font-mono);
}

.select-real {
  height: 36px;
  min-width: 130px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #fff;
  color: var(--text-primary);
  font-size: 13px;
}

.query-btn {
  margin-left: auto;
  align-self: end;
  width: 64px;
}

.alarm-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 16px;
  align-items: start;
}

.left-stack {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.event-card {
  padding: 18px;
  min-width: 0;
}

.event-card h2 {
  margin-bottom: 18px;
}

.event-card .data-table td {
  height: 51px;
}

.event-card tbody tr {
  cursor: pointer;
}

.event-card tr.hot td {
  background: #fff8f7;
  border-top: 1px solid #f2c7c4;
  border-bottom: 1px solid #f2c7c4;
}

.empty-cell {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 18px 0;
}

.right-stack {
  display: grid;
  gap: 0;
  align-content: start;
  min-width: 0;
}

.right-stack .card {
  padding: 14px 18px;
  border-radius: 0;
}

.right-stack .card:first-child {
  border-top-left-radius: var(--radius-card);
  border-top-right-radius: var(--radius-card);
}

.right-stack .card:last-child {
  border-bottom-left-radius: var(--radius-card);
  border-bottom-right-radius: var(--radius-card);
}

.detail-head {
  justify-content: space-between;
  margin-bottom: 12px;
}

.detail-title {
  gap: 12px;
  margin-bottom: 12px;
}

.detail-title strong {
  font-size: 17px;
}

.detail-card dl {
  display: grid;
  gap: 10px;
}

.detail-card dl div {
  display: grid;
  grid-template-columns: 86px 1fr;
  gap: 8px;
}

.detail-card dt,
.detail-card dd {
  font-size: 13px;
}

.detail-card dt {
  color: var(--text-muted);
}

.detail-card dd {
  color: var(--text-primary);
  font-weight: 500;
}

.timeline-card h2,
.advice-card h2 {
  margin-bottom: 10px;
}

.timeline {
  display: grid;
  gap: 9px;
}

.timeline div {
  gap: 10px;
  color: var(--text-primary);
}

.timeline time {
  width: 64px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
}

.timeline span {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 0 1px #fff, 0 0 0 3px #dbeee2;
}

.timeline span.red {
  background: var(--red);
  box-shadow: 0 0 0 1px #fff, 0 0 0 3px #f3d3d0;
}

.timeline strong {
  font-size: 13px;
}

.advice-card ul {
  padding-left: 16px;
  color: var(--text-secondary);
  line-height: 1.7;
  font-size: 13px;
}

@media (max-width: 1120px) {
  .summary-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .alarm-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .topbar,
  .filter-card {
    align-items: stretch;
    flex-direction: column;
  }

  .summary-row {
    grid-template-columns: 1fr;
  }

  .query-btn {
    align-self: stretch;
    width: 100%;
  }

  .detail-card dl div {
    grid-template-columns: 78px 1fr;
  }
}
</style>
