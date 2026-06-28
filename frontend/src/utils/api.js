import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://localhost:8000',
})

api.interceptors.request.use((config) => {
  const raw = localStorage.getItem('smart-agriculture-session')
  if (raw) {
    try {
      const session = JSON.parse(raw)
      if (session?.token) {
        config.headers.Authorization = `Bearer ${session.token}`
      }
    } catch { /* ignore */ }
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('smart-agriculture-session')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
