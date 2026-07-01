import axios from 'axios'

const SESSION_KEY = 'smart-agriculture-session'

function readSession() {
  const stores = [localStorage, sessionStorage]
  for (const storage of stores) {
    try {
      const session = JSON.parse(storage.getItem(SESSION_KEY) || 'null')
      if (!session?.token) continue
      if (session.expiresAt && Date.now() > Number(session.expiresAt)) {
        storage.removeItem(SESSION_KEY)
        continue
      }
      return session
    } catch { /* ignore malformed session */ }
  }
  return null
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY)
  sessionStorage.removeItem(SESSION_KEY)
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000',
})

api.interceptors.request.use((config) => {
  const session = readSession()
  if (session?.token) {
    config.headers.Authorization = `Bearer ${session.token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearSession()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
