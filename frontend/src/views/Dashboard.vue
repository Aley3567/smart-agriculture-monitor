<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useSensorStore } from '../stores/sensor'
import { useSystemStore } from '../stores/system'
import { DASHBOARD_FALLBACK } from '../utils/fallbackData'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const sensorStore = useSensorStore()
const systemStore = useSystemStore()

const colors = {
  temp: '#df463f',
  humi: '#3c98f0',
  light: '#fb8b12',
  soil: '#37a85b',
}

const realHistoryReady = computed(() => sensorStore.history.timestamps.length > 6)

const metricCards = computed(() => DASHBOARD_FALLBACK.metrics.map(item => {
  const current = Number(sensorStore.current[item.key])
  const value = realHistoryReady.value && Number.isFinite(current) && current > 0 ? current : item.value
  return {
    ...item,
    value: item.key === 'light' ? Math.round(value) : value.toFixed(1),
    sparkline: DASHBOARD_FALLBACK.sparkline[item.key],
  }
}))

const chartOption = computed(() => {
  const useReal = realHistoryReady.value
  const labels = useReal ? sensorStore.history.timestamps.map(ts => new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })) : DASHBOARD_FALLBACK.times
  const seriesData = key => useReal ? sensorStore.history[key] : DASHBOARD_FALLBACK.chart[key]

  return {
    animation: false,
    color: [colors.temp, colors.humi, colors.light, colors.soil],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#e6e0d8',
      borderWidth: 1,
      textStyle: { color: '#24292f', fontSize: 12 },
    },
    legend: {
      top: 6,
      left: 0,
      itemWidth: 13,
      itemHeight: 3,
      itemGap: 24,
      textStyle: { color: '#4f565f', fontSize: 12 },
      data: ['空气温度(°C)', '空气湿度(%)', '光照强度(lux)', '土壤湿度(%)'],
    },
    grid: { top: 76, left: 50, right: 64, bottom: 42 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#dedbd5' } },
      axisLabel: { color: '#7d848d', fontSize: 12 },
    },
    yAxis: [
      {
        type: 'value',
        min: 0,
        max: 40,
        splitNumber: 4,
        axisLabel: { color: '#7d848d', fontSize: 12 },
        splitLine: { lineStyle: { color: '#eeeae4', type: 'dashed' } },
      },
      {
        type: 'value',
        min: 0,
        max: 100,
        splitNumber: 4,
        axisLabel: { color: '#7d848d', fontSize: 12 },
        splitLine: { show: false },
      },
    ],
    series: [
      { name: '空气温度(°C)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 0, lineStyle: { width: 2 }, data: seriesData('temp') },
      { name: '空气湿度(%)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 1, lineStyle: { width: 2 }, data: seriesData('humi') },
      { name: '光照强度(lux)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 1, lineStyle: { width: 2 }, data: seriesData('light').map(v => Math.round(v / 20)) },
      { name: '土壤湿度(%)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 1, lineStyle: { width: 2 }, data: seriesData('soil') },
    ],
  }
})

const devices = DASHBOARD_FALLBACK.devices
const alarms = DASHBOARD_FALLBACK.alarms
</script>

<template>
  <div class="monitor-page">
    <header class="topbar">
      <h1 class="page-title">环境监测</h1>
      <div class="top-actions">
        <button class="select-like" type="button">温室A-1号 <span>⌄</span></button>
        <span class="online-pill"><span class="status-dot green"></span>在线</span>
        <span class="refresh-text">刷新 {{ DASHBOARD_FALLBACK.refreshTime }}</span>
        <button class="icon-btn" title="刷新" type="button">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M16.2 10a6.2 6.2 0 1 1-1.8-4.4"/><path d="M16.2 4v4h-4"/></svg>
        </button>
        <button class="icon-btn" title="设置" type="button">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="10" cy="10" r="2.6"/><path d="M16 10a6.2 6.2 0 0 0-.1-.9l1.5-1.2-1.7-3-1.9.7a6.7 6.7 0 0 0-1.6-.9L12 2.7H8l-.3 2a6.7 6.7 0 0 0-1.6.9l-1.9-.7-1.7 3 1.5 1.2a6.2 6.2 0 0 0 0 1.8l-1.5 1.2 1.7 3 1.9-.7a6.7 6.7 0 0 0 1.6.9l.3 2h4l.3-2a6.7 6.7 0 0 0 1.6-.9l1.9.7 1.7-3-1.5-1.2c.1-.3.1-.6.1-.9z"/></svg>
        </button>
      </div>
    </header>

    <section class="metric-row">
      <article v-for="metric in metricCards" :key="metric.key" class="metric-card card">
        <div class="metric-head">
          <span class="metric-icon" :class="metric.key">
            <svg v-if="metric.icon === 'thermo'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M8 11.4V4.5a2 2 0 0 1 4 0v6.9a4 4 0 1 1-4 0z"/><path d="M10 7v6"/></svg>
            <svg v-else-if="metric.icon === 'drop'" viewBox="0 0 20 20" fill="currentColor"><path d="M10 2.5c3.7 4.2 5.6 7.2 5.6 9.4A5.6 5.6 0 0 1 4.4 12c0-2.2 1.9-5.2 5.6-9.5z"/></svg>
            <svg v-else-if="metric.icon === 'sun'" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="10" cy="10" r="3.2"/><path d="M10 1.8v2.3M10 15.9v2.3M1.8 10h2.3M15.9 10h2.3M4.2 4.2l1.6 1.6M14.2 14.2l1.6 1.6M15.8 4.2l-1.6 1.6M5.8 14.2l-1.6 1.6"/></svg>
            <svg v-else viewBox="0 0 20 20" fill="currentColor"><path d="M6.4 10.6C3.5 9 3 5.7 3.2 3.2c2.9.2 5.8 1.5 6.4 4.6 1.2-2.9 4-4.2 7.1-4.4.3 3.9-1.6 6.6-5.4 7.7v5.7H9.6v-5.5a9 9 0 0 1-3.2-.7z"/></svg>
          </span>
          <strong>{{ metric.label }}</strong>
        </div>
        <div class="metric-value"><span>{{ metric.value }}</span><small>{{ metric.unit }}</small></div>
        <svg class="sparkline" viewBox="0 0 180 54" preserveAspectRatio="none">
          <path :d="`M0 ${metric.sparkline[0]} ${metric.sparkline.map((v, i) => `L${i * 15} ${v}`).join(' ')}`" fill="none" :stroke="metric.color" stroke-width="2" />
        </svg>
        <div class="metric-minmax">
          <span>最低 {{ metric.min }}</span>
          <span>最高 {{ metric.max }}</span>
        </div>
      </article>
    </section>

    <div class="dashboard-grid">
      <main class="left-stack">
        <section class="card trend-card">
          <div class="panel-head">
            <h2 class="section-title">实时趋势</h2>
            <div class="range-tabs">
              <button class="active" type="button">1小时</button>
              <button type="button">6小时</button>
              <button type="button">24小时</button>
              <button type="button">7天</button>
              <button class="calendar" type="button">
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="4" y="4.5" width="12" height="12" rx="2"/><path d="M7 2.8v3.5M13 2.8v3.5M4 8h12"/></svg>
              </button>
            </div>
          </div>
          <v-chart :option="chartOption" autoresize class="trend-chart" />
        </section>

        <section class="card device-card">
          <h2 class="section-title">设备列表</h2>
          <div class="table-scroll">
            <table class="data-table">
              <thead>
                <tr>
                  <th>设备名称</th>
                  <th>设备类型</th>
                  <th>位置</th>
                  <th>连接状态</th>
                  <th>最后上报</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in devices" :key="row[0]">
                  <td>{{ row[0] }}</td>
                  <td>{{ row[1] }}</td>
                  <td>{{ row[2] }}</td>
                  <td><span class="status-dot green"></span> {{ row[3] }}</td>
                  <td>{{ row[4] }}</td>
                  <td><a>详情</a></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>

      <aside class="right-stack">
        <section class="card side-card">
          <h2 class="section-title">运行状态</h2>
          <div class="state-list">
            <div><span class="side-icon green">▣</span><span>服务器连接</span><strong>正常</strong></div>
            <div><span class="side-icon green">▢</span><span>终端设备</span><strong>{{ DASHBOARD_FALLBACK.terminalStatus }}</strong></div>
            <div><span class="side-icon orange">▣</span><span>告警状态</span><strong class="danger">2 条告警</strong></div>
          </div>
        </section>

        <section class="card side-card alarm-card">
          <h2 class="section-title">告警摘要</h2>
          <div v-for="alarm in alarms" :key="alarm.title" class="alarm-item">
            <span class="alarm-mark" :class="alarm.tone">!</span>
            <div>
              <strong>{{ alarm.title }}</strong>
              <small>{{ alarm.place }}</small>
            </div>
            <time>{{ alarm.time }}</time>
          </div>
          <button class="view-all" type="button">查看全部</button>
        </section>

        <section class="card side-card">
          <h2 class="section-title">执行器控制</h2>
          <div class="actuator-list">
            <div>
              <span class="act-icon blue">⌁</span>
              <div><strong>灌溉系统</strong><small>自动 | 今日已灌溉 1 次</small></div>
              <button class="toggle active" type="button"></button>
            </div>
            <div>
              <span class="act-icon green">⌁</span>
              <div><strong>施肥系统</strong><small>自动 | 今日已施肥 0 次</small></div>
              <button class="toggle active" type="button"></button>
            </div>
            <div>
              <span class="act-icon green">□</span>
              <div><strong>天窗通风</strong><small>自动 | 当前开度 30%</small></div>
              <button class="toggle active" type="button"></button>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.monitor-page {
  max-width: 1320px;
  margin: 0 auto;
}

.topbar,
.top-actions,
.metric-head,
.panel-head,
.range-tabs,
.state-list div,
.alarm-item,
.actuator-list > div {
  display: flex;
  align-items: center;
}

.topbar {
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.top-actions {
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.online-pill {
  height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 12px;
  border: 1px solid #d7eadc;
  border-radius: 6px;
  background: #f2fbf4;
  color: var(--green-deep);
  font-weight: 650;
}

.refresh-text {
  color: var(--text-secondary);
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.metric-card {
  min-height: 178px;
  padding: 20px 18px;
}

.metric-head {
  gap: 10px;
  font-size: 15px;
}

.metric-icon {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.metric-icon svg {
  width: 21px;
  height: 21px;
}

.metric-icon.temp { color: var(--red); }
.metric-icon.humi { color: var(--blue); }
.metric-icon.light { color: var(--orange); }
.metric-icon.soil { color: var(--green); }

.metric-value {
  margin: 10px 0 4px 44px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.metric-value span {
  font-size: 33px;
  line-height: 1;
  font-weight: 780;
}

.metric-value small {
  color: var(--text-secondary);
  font-size: 15px;
  font-weight: 650;
}

.sparkline {
  width: 100%;
  height: 48px;
  margin-top: 8px;
}

.metric-minmax {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: 12px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 382px;
  gap: 12px;
}

.left-stack,
.right-stack {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.trend-card,
.device-card,
.side-card {
  padding: 18px;
}

.panel-head {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}

.range-tabs {
  height: 36px;
  border: 1px solid var(--border-light);
  border-radius: 7px;
  overflow: hidden;
}

.range-tabs button {
  min-width: 64px;
  height: 34px;
  border: 0;
  border-right: 1px solid var(--border-light);
  background: #fff;
  color: #4d545d;
  font-size: 13px;
}

.range-tabs button.active {
  background: #eef8f1;
  color: #1f6d39;
  font-weight: 700;
}

.range-tabs .calendar {
  min-width: 38px;
  border-right: 0;
}

.range-tabs svg {
  width: 16px;
  height: 16px;
}

.trend-chart {
  width: 100%;
  height: 372px;
}

.device-card {
  min-height: 236px;
}

.device-card h2 {
  margin-bottom: 14px;
}

.device-card a {
  color: #1d703b;
  font-weight: 700;
}

.right-stack {
  align-content: start;
}

.side-card {
  min-height: 142px;
}

.side-card h2 {
  margin-bottom: 17px;
}

.state-list {
  display: grid;
  gap: 18px;
}

.state-list div {
  gap: 10px;
}

.state-list strong {
  margin-left: auto;
  color: var(--green);
}

.state-list .danger {
  color: #f04b21;
}

.side-icon {
  width: 18px;
  color: var(--green);
}

.side-icon.orange {
  color: var(--orange);
}

.alarm-card {
  min-height: 202px;
}

.alarm-item {
  gap: 10px;
  padding: 4px 0 14px;
}

.alarm-item + .alarm-item {
  border-top: 1px solid var(--border-light);
  padding-top: 14px;
}

.alarm-mark {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  font-weight: 800;
  font-size: 12px;
}

.alarm-mark.red { background: var(--red); }
.alarm-mark.orange { background: var(--orange); }

.alarm-item div {
  display: grid;
  gap: 2px;
}

.alarm-item small {
  color: var(--text-muted);
}

.alarm-item time {
  margin-left: auto;
  color: var(--text-secondary);
}

.view-all {
  width: 100%;
  height: 36px;
  margin-top: 6px;
  border: 0;
  border-top: 1px solid var(--border-light);
  background: #fff;
  color: var(--text-secondary);
}

.actuator-list {
  display: grid;
  gap: 18px;
}

.actuator-list > div {
  gap: 12px;
}

.act-icon {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--green);
  font-weight: 800;
}

.act-icon.blue {
  color: var(--blue);
}

.actuator-list div div {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.actuator-list small {
  color: var(--text-muted);
}

.actuator-list .toggle {
  margin-left: auto;
}

@media (max-width: 1100px) {
  .metric-row,
  .dashboard-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .right-stack {
    grid-column: 1 / -1;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .top-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .metric-row,
  .dashboard-grid,
  .right-stack {
    grid-template-columns: 1fr;
  }

  .metric-card {
    min-height: 160px;
  }

  .trend-chart {
    height: 300px;
  }

  .range-tabs {
    width: 100%;
    overflow-x: auto;
  }
}
</style>
