import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import History from '../views/History.vue'
import Settings from '../views/Settings.vue'
import AlarmLog from '../views/AlarmLog.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'Dashboard', component: Dashboard },
  { path: '/history', name: 'History', component: History },
  { path: '/settings', name: 'Settings', component: Settings },
  { path: '/alarm-log', name: 'AlarmLog', component: AlarmLog },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
