export const DASHBOARD_FALLBACK = {
  refreshTime: '10:30:45',
  terminalStatus: '23/23 在线',
  times: ['09:30', '09:35', '09:40', '09:45', '09:50', '09:55', '10:00', '10:05', '10:10', '10:15', '10:20', '10:25', '10:30'],
  metrics: [
    { key: 'temp', label: '空气温度', icon: 'thermo', value: 24.6, unit: '°C', min: '18.2°C', max: '28.7°C', color: '#df463f' },
    { key: 'humi', label: '空气湿度', icon: 'drop', value: 68.3, unit: '%', min: '45%', max: '82%', color: '#3c98f0' },
    { key: 'light', label: '光照强度', icon: 'sun', value: 856, unit: 'lux', min: '120 lux', max: '1620 lux', color: '#fb8b12' },
    { key: 'soil', label: '土壤湿度', icon: 'sprout', value: 32.7, unit: '%', min: '21.4%', max: '48.6%', color: '#37a85b' },
  ],
  chart: {
    temp: [22.1, 22.9, 22.6, 21.3, 22.2, 23.1, 22.8, 23.4, 22.9, 22.1, 21.8, 22.5, 21.9],
    humi: [76, 75, 71, 72, 69, 70, 68, 66, 63, 61, 58, 47, 52],
    light: [430, 560, 690, 760, 820, 840, 900, 940, 980, 1010, 1030, 1045, 1080],
    soil: [48, 47, 45, 44, 43, 42, 40, 39, 38, 37, 36, 36, 35],
  },
  sparkline: {
    temp: [45, 42, 40, 38, 37, 35, 39, 37, 36, 40, 45, 46, 49],
    humi: [48, 53, 51, 49, 45, 47, 42, 40, 43, 47, 55, 49, 57],
    light: [46, 44, 50, 45, 36, 32, 41, 44, 47, 52, 53, 48, 51],
    soil: [51, 49, 54, 53, 48, 47, 50, 42, 39, 40, 42, 47, 46],
  },
  devices: [
    ['温湿度传感器-1', '温湿度传感器', 'A区-1排', '在线', '10:30:41'],
    ['光照传感器-1', '光照传感器', 'A区-1排', '在线', '10:30:42'],
    ['土壤墒情传感器-1', '土壤墒情传感器', 'A区-2排', '在线', '10:30:40'],
    ['气象站-1', '气象站', '温室外', '在线', '10:30:39'],
  ],
  alarms: [
    { title: '土壤湿度过低', place: 'A区-2排  传感器-1', time: '10:28', tone: 'red' },
    { title: '光照强度偏低', place: 'A区-3排  传感器-2', time: '10:22', tone: 'orange' },
  ],
}

export const HISTORY_FALLBACK = {
  range: {
    startDate: '2026/06/21',
    startTime: '00:00',
    endDate: '2026/06/28',
    endTime: '23:59',
  },
  latest: {
    time: '06/28 23:55',
    temp: '24.3',
    humi: '67.8',
    light: '850',
    soil: '31.9',
  },
  health: {
    successRate: '99.6%',
    missing: '12 条',
    deviceStatus: '在线',
  },
  rows: [
    { id: 1, timestamp: '2026/06/28 23:55', temp: 24.3, humi: 67.8, light: 850, soil: 31.9, status: '正常' },
    { id: 2, timestamp: '2026/06/28 23:50', temp: 24.2, humi: 67.5, light: 840, soil: 31.8, status: '正常' },
    { id: 3, timestamp: '2026/06/28 23:45', temp: 24.1, humi: 67.7, light: 830, soil: 31.7, status: '正常' },
    { id: 4, timestamp: '2026/06/28 23:40', temp: 24.0, humi: 68.1, light: 815, soil: 31.6, status: '正常' },
    { id: 5, timestamp: '2026/06/28 23:35', temp: 23.9, humi: 68.3, light: 805, soil: 31.5, status: '正常' },
  ],
  chart: {
    temp: [24, 25, 23.5, 25.1, 24.2, 24.8, 23.2, 24.4, 25.3, 23.7, 24.9, 24.1, 23.5, 24.2, 24.6, 23.4, 23.8],
    humi: [72, 75, 84, 68, 78, 84, 72, 80, 86, 70, 83, 76, 86, 74, 82, 79, 72],
    light: [120, 940, 90, 70, 980, 120, 70, 1050, 80, 70, 1010, 100, 70, 1080, 85, 70, 980],
    soil: [41, 40, 39, 38, 39, 40, 39, 38, 39, 40, 38, 39, 41, 39, 38, 40, 44],
  },
}

export const ALARM_FALLBACK = {
  filterRange: {
    start: '2026/06/27 00:00',
    end: '2026/06/27 23:59',
  },
  selected: {
    title: '空气温度超限',
    level: '高危',
    occurredAt: '2026/06/27 16:03:24',
    param: '空气温度',
    value: '42.6°C',
    threshold: '> 40.0°C',
    device: '温室A-1号 / 温湿度传感器-1',
    position: 'A区-1排',
    status: '待复核',
    handler: '张工',
    handledAt: '-',
    remark: '-',
  },
  timeline: [
    ['16:03:24', '报警触发', 'red'],
    ['16:03:25', '启动天窗通风', 'green'],
    ['16:03:26', '启动水帘降温', 'green'],
    ['16:03:27', '发送通知到管理员', 'green'],
  ],
  rows: [
    { id: 1, time: '2026/06/27 16:03:24', param: '空气温度', value: '42.6°C', threshold: '> 40.0°C', level: '高危', status: '待复核', person: '张工', action: '查看', hot: true },
    { id: 2, time: '2026/06/27 15:47:11', param: '土壤湿度', value: '12.3%', threshold: '< 15.0%', level: '中危', status: '已处理', person: '李工', action: '查看' },
    { id: 3, time: '2026/06/27 14:31:08', param: '光照强度', value: '1860 lux', threshold: '> 1600 lux', level: '中危', status: '已处理', person: '王工', action: '查看' },
    { id: 4, time: '2026/06/27 12:18:52', param: '空气湿度', value: '92.1%', threshold: '> 90.0%', level: '中危', status: '待复核', person: '-', action: '查看' },
    { id: 5, time: '2026/06/27 11:06:33', param: '土壤湿度', value: '11.2%', threshold: '< 15.0%', level: '中危', status: '已处理', person: '李工', action: '查看' },
    { id: 6, time: '2026/06/27 09:22:10', param: '二氧化碳浓度', value: '1280 ppm', threshold: '> 1200 ppm', level: '中危', status: '已处理', person: '赵工', action: '查看' },
    { id: 7, time: '2026/06/27 08:15:45', param: '空气温度', value: '-2.1°C', threshold: '< 0.0°C', level: '低危', status: '已处理', person: '张工', action: '查看' },
    { id: 8, time: '2026/06/27 07:48:02', param: '光照强度', value: '280 lux', threshold: '< 300 lux', level: '低危', status: '已处理', person: '王工', action: '查看' },
    { id: 9, time: '2026/06/27 07:12:37', param: '土壤EC值', value: '3.6 mS/cm', threshold: '> 3.5 mS/cm', level: '低危', status: '已处理', person: '李工', action: '查看' },
    { id: 10, time: '2026/06/27 06:35:18', param: '空气湿度', value: '88.7%', threshold: '> 85.0%', level: '低危', status: '已处理', person: '赵工', action: '查看' },
  ],
  summary: [
    { label: '今日报警', value: 7, sub: '较昨日 +3', tone: 'red' },
    { label: '高危事件', value: 2, tone: 'red' },
    { label: '中危事件', value: 3, tone: 'orange' },
    { label: '低危事件', value: 2, tone: 'blue' },
    { label: '已处理', value: 5, tone: 'green' },
  ],
}

export const SETTINGS_FALLBACK = {
  connection: [
    ['服务器连接', '已连接', 'green'],
    ['终端设备', '在线 8/10', 'green'],
    ['传感器采集', '正常', 'green'],
    ['执行器设备', '离线 2', 'orange'],
  ],
  policies: [
    ['温度过高', '天窗', '打开通风'],
    ['温度过低', '补光灯', '开启补光'],
    ['湿度过高', '通风机', '加强通风'],
    ['湿度过低', '喷淋系统', '启动喷淋'],
    ['光照过强', '遮阳帘', '放下遮阳'],
    ['光照过弱', '补光灯', '开启补光'],
    ['土壤湿度过低', '灌溉水泵', '启动灌溉'],
  ],
  changes: [
    ['2026/06/28 10:30', '更新空气温度阈值：18-32°C', '张工', '已应用'],
    ['2026/06/28 09:15', '修改湿度联动策略', '张工', '已应用'],
    ['2026/06/27 16:45', '调整光照强度阈值：500-1600lux', '张工', '已应用'],
    ['2026/06/27 14:20', '更新土壤湿度阈值：35-70%', '张工', '已应用'],
    ['2026/06/26 11:05', '切换运行模式为自动控制', '张工', '已应用'],
  ],
}
