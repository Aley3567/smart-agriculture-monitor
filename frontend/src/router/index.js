import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import History from '../views/History.vue'
import Settings from '../views/Settings.vue'
import AlarmLog from '../views/AlarmLog.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import { hasStoredSession } from '../stores/auth'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', name: 'Login', component: Login, meta: { public: true } },
  { path: '/register', name: 'Register', component: Register, meta: { public: true } },
  { path: '/dashboard', name: 'Dashboard', component: Dashboard },
  { path: '/history', name: 'History', component: History },
  { path: '/settings', name: 'Settings', component: Settings },
  { path: '/alarm-log', name: 'AlarmLog', component: AlarmLog },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.public) {
    if (hasStoredSession() && (to.path === '/login' || to.path === '/register')) {
      return '/dashboard'
    }
    return true
  }

  if (!hasStoredSession()) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  return true
})

export default router
