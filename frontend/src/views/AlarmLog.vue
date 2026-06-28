<script setup>
import { computed, onMounted } from 'vue'
import { usePaginatedFetch } from '../composables/usePaginatedFetch'
import { ALARM_FALLBACK } from '../utils/fallbackData'

const { dateRange, tableData, total, currentPage, pageSize, fetch: fetchAlarms, handlePageChange } =
  usePaginatedFetch('/api/alarms')

const displayRows = computed(() => tableData.value.length ? tableData.value.map((row, index) => ({
  id: row.id || index,
  time: row.timestamp || row.time,
  param: row.param_name || row.param || '空气温度',
  value: row.value || row.trigger_value || ALARM_FALLBACK.selected.value,
  threshold: row.threshold || ALARM_FALLBACK.selected.threshold,
  level: row.level || (index === 0 ? '高危' : index > 5 ? '低危' : '中危'),
  status: row.status || (index % 3 === 0 ? '待复核' : '已处理'),
  person: row.person || '-',
  action: '查看',
  hot: index === 0,
})) : ALARM_FALLBACK.rows)

const summary = ALARM_FALLBACK.summary

const selected = computed(() => displayRows.value[0])

onMounted(() => {
  dateRange.value = [new Date('2026-06-27T00:00:00'), new Date('2026-06-27T23:59:00')]
  fetchAlarms()
})

function levelClass(level) {
  if (level === '高危') return 'danger'
  if (level === '中危') return 'warn'
  return 'info'
}

function statusClass(status) {
  return status === '已处理' ? 'success' : 'danger'
}
</script>

<template>
  <div class="alarm-page">
    <header class="topbar">
      <h1 class="page-title">报警日志</h1>
      <button class="btn btn-primary" type="button" @click="fetchAlarms">刷新日志</button>
    </header>

    <div class="alarm-grid">
      <main class="left-stack">
        <section class="summary-row">
          <article v-for="item in summary" :key="item.label" class="card summary-card">
            <span>{{ item.label }}</span>
            <div><strong :class="item.tone">{{ item.value }}</strong><small v-if="item.sub">{{ item.sub }}</small></div>
          </article>
        </section>

        <section class="card filter-card">
          <div class="filter-group wide">
            <label>时间范围</label>
            <div class="date-field">
              <span>{{ ALARM_FALLBACK.filterRange.start }}</span>
              <span>→</span>
              <span>{{ ALARM_FALLBACK.filterRange.end }}</span>
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="4" y="4.5" width="12" height="12" rx="2"/><path d="M7 2.8v3.5M13 2.8v3.5M4 8h12"/></svg>
            </div>
          </div>
          <div class="filter-group">
            <label>参数类型</label>
            <button class="select-like" type="button">全部 <span>⌄</span></button>
          </div>
          <div class="filter-group">
            <label>处理状态</label>
            <button class="select-like" type="button">全部 <span>⌄</span></button>
          </div>
          <button class="btn btn-soft query-btn" type="button">查询</button>
          <button class="btn btn-ghost" type="button">重置</button>
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
                <th>严重等级</th>
                <th>处理状态</th>
                <th>处理人</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in displayRows" :key="row.id" :class="{ hot: row.hot }">
                <td>{{ row.time }}</td>
                <td>{{ row.param }}</td>
                <td class="col-number">{{ row.value }}</td>
                <td class="col-number">{{ row.threshold }}</td>
                <td><span class="badge" :class="`badge-${levelClass(row.level)}`">{{ row.level }}</span></td>
                <td><span class="badge" :class="`badge-${statusClass(row.status)}`">{{ row.status }}</span></td>
                <td>{{ row.person }}</td>
                <td><a>{{ row.action }}</a></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination">
          <span>共 {{ total || 24 }} 条</span>
          <button type="button" @click="handlePageChange(Math.max(1, currentPage - 1))">‹</button>
          <button type="button" disabled></button>
          <button class="active" type="button">1</button>
          <button type="button" @click="handlePageChange(2)">2</button>
          <button type="button" @click="handlePageChange(3)">3</button>
          <button type="button"></button>
          <button type="button" @click="handlePageChange(currentPage + 1)">›</button>
          <span>前往</span>
          <button class="page-input" type="button">{{ pageSize > 0 ? 1 : 1 }}</button>
          <span>页</span>
        </div>
        </section>
      </main>

      <aside class="right-stack">
        <section class="card detail-card">
          <div class="detail-head">
            <h2 class="section-title">报警详情</h2>
            <button class="close-btn" type="button">×</button>
          </div>
          <div class="detail-title">
            <span class="badge badge-danger">{{ ALARM_FALLBACK.selected.level }}</span>
            <strong>{{ ALARM_FALLBACK.selected.title }}</strong>
          </div>
          <dl>
            <div><dt>发生时间</dt><dd>{{ ALARM_FALLBACK.selected.occurredAt }}</dd></div>
            <div><dt>参数类型</dt><dd>{{ ALARM_FALLBACK.selected.param }}</dd></div>
            <div><dt>触发值</dt><dd>{{ ALARM_FALLBACK.selected.value }}</dd></div>
            <div><dt>阈值</dt><dd>{{ ALARM_FALLBACK.selected.threshold }}</dd></div>
            <div><dt>所属设备</dt><dd>{{ ALARM_FALLBACK.selected.device }}</dd></div>
            <div><dt>位置</dt><dd>{{ ALARM_FALLBACK.selected.position }}</dd></div>
            <div><dt>处理状态</dt><dd><span class="badge badge-danger">{{ ALARM_FALLBACK.selected.status }}</span></dd></div>
            <div><dt>处理人</dt><dd>{{ ALARM_FALLBACK.selected.handler }}</dd></div>
            <div><dt>处理时间</dt><dd>{{ ALARM_FALLBACK.selected.handledAt }}</dd></div>
            <div><dt>备注</dt><dd>{{ ALARM_FALLBACK.selected.remark }}</dd></div>
          </dl>
        </section>

        <section class="card timeline-card">
          <h2 class="section-title">自动动作</h2>
          <div class="timeline">
            <div v-for="item in ALARM_FALLBACK.timeline" :key="item[0] + item[1]">
              <time>{{ item[0] }}</time>
              <span :class="{ red: item[2] === 'red' }"></span>
              <strong>{{ item[1] }}</strong>
            </div>
          </div>
        </section>

        <section class="card advice-card">
          <h2 class="section-title">处理建议</h2>
          <ul>
            <li>检查通风系统是否正常运行</li>
            <li>确认外部遮阳是否开启</li>
            <li>必要时启动强制降温模式</li>
            <li>持续监测温度变化趋势</li>
          </ul>
        </section>

        <section class="card review-card">
          <h2 class="section-title">复核记录</h2>
          <table class="mini-table">
            <thead><tr><th>时间</th><th>复核人</th><th>处理结果</th><th>备注</th></tr></thead>
            <tbody><tr><td>-</td><td>-</td><td>-</td><td>-</td></tr></tbody>
          </table>
          <div class="review-actions">
            <button class="btn btn-primary" type="button">标记为已处理</button>
            <button class="btn btn-ghost" type="button">添加复核记录</button>
          </div>
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
.timeline div,
.review-actions {
  display: flex;
  align-items: center;
}

.topbar {
  justify-content: space-between;
  margin-bottom: 18px;
}

.summary-row {
  display: grid;
  grid-template-columns: 1.25fr .86fr .86fr .86fr .86fr;
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

.date-field {
  height: 36px;
  min-width: 330px;
  gap: 20px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #fff;
}

.date-field svg {
  width: 16px;
  height: 16px;
  margin-left: auto;
}

.query-btn {
  margin-left: auto;
  align-self: end;
  width: 64px;
}

.filter-card > .btn-ghost {
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

.event-card tr.hot td {
  background: #fff8f7;
  border-top: 1px solid #f2c7c4;
  border-bottom: 1px solid #f2c7c4;
}

.event-card a {
  color: var(--green-deep);
  font-weight: 700;
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

.close-btn {
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  font-size: 24px;
  line-height: 1;
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
.advice-card h2,
.review-card h2 {
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

.mini-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 14px;
  font-size: 12px;
}

.mini-table th,
.mini-table td {
  height: 28px;
  border: 1px solid var(--border-light);
  text-align: center;
  color: var(--text-secondary);
}

.review-actions {
  gap: 8px;
}

.review-actions .btn {
  flex: 1;
  padding: 0 10px;
}

.page-input {
  width: 44px;
}

@media (max-width: 1120px) {
  .summary-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
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

  .date-field {
    min-width: 0;
    width: 100%;
    gap: 8px;
    font-size: 12px;
  }

  .query-btn,
  .filter-card > .btn-ghost {
    align-self: stretch;
    width: 100%;
  }

  .detail-card dl div {
    grid-template-columns: 78px 1fr;
  }
}
</style>
