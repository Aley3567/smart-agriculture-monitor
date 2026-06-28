import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import api from '../utils/api'

const STORAGE_KEY = 'smart-agriculture-session'

function readSession() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
  } catch {
    return null
  }
}

export function hasStoredSession() {
  return Boolean(readSession()?.token)
}

export const useAuthStore = defineStore('auth', () => {
  const session = ref(readSession())
  const isAuthenticated = computed(() => Boolean(session.value?.token))
  const user = computed(() => session.value?.user || null)

  function saveSession(token, userData) {
    const next = {
      token,
      user: {
        id: userData.id,
        name: userData.display_name || userData.username,
        username: userData.username,
        role: userData.role,
      },
      createdAt: new Date().toISOString(),
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    session.value = next
  }

  async function login({ username, password }) {
    if (!username?.trim() || !password?.trim()) {
      throw new Error('请输入账号和密码')
    }
    const res = await api.post('/api/auth/login', {
      username: username.trim(),
      password,
    })
    saveSession(res.data.access_token, res.data.user)
    return session.value
  }

  async function register({ username, password, displayName }) {
    if (!username?.trim() || !password?.trim()) {
      throw new Error('请输入账号和密码')
    }
    const res = await api.post('/api/auth/register', {
      username: username.trim(),
      password,
      display_name: displayName?.trim() || '',
    })
    saveSession(res.data.access_token, res.data.user)
    return session.value
  }

  async function changePassword({ oldPassword, newPassword }) {
    await api.put('/api/auth/password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEY)
    session.value = null
  }

  return {
    session,
    isAuthenticated,
    user,
    login,
    register,
    changePassword,
    logout,
  }
})
