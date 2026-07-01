import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import api from '../utils/api'

const STORAGE_KEY = 'smart-agriculture-session'
const PROFILE_KEY = 'smart-agriculture-profile'
const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000

function parseStored(raw) {
  try {
    return JSON.parse(raw || 'null')
  } catch {
    return null
  }
}

function isExpired(session) {
  return Boolean(session?.expiresAt && Date.now() > Number(session.expiresAt))
}

function readSession() {
  const persistent = parseStored(localStorage.getItem(STORAGE_KEY))
  if (persistent?.token) {
    if (!isExpired(persistent)) return persistent
    localStorage.removeItem(STORAGE_KEY)
  }

  const browserSession = parseStored(sessionStorage.getItem(STORAGE_KEY))
  if (browserSession?.token) return browserSession
  return null
}

function readProfile() {
  return parseStored(localStorage.getItem(PROFILE_KEY)) || {}
}

export function hasStoredSession() {
  return Boolean(readSession()?.token)
}

export const useAuthStore = defineStore('auth', () => {
  const session = ref(readSession())
  const localProfile = ref(readProfile())
  const isAuthenticated = computed(() => Boolean(session.value?.token))
  const user = computed(() => {
    if (!session.value?.user) return null
    return {
      ...session.value.user,
      name: localProfile.value.name || session.value.user.name,
      avatar: localProfile.value.avatar || '',
    }
  })

  function saveSession(token, userData, remember = true) {
    const next = {
      token,
      remember,
      user: {
        id: userData.id,
        name: userData.display_name || userData.username,
        username: userData.username,
        role: userData.role,
      },
      createdAt: new Date().toISOString(),
      expiresAt: remember ? Date.now() + SEVEN_DAYS_MS : null,
    }
    const storage = remember ? localStorage : sessionStorage
    localStorage.removeItem(STORAGE_KEY)
    sessionStorage.removeItem(STORAGE_KEY)
    storage.setItem(STORAGE_KEY, JSON.stringify(next))
    session.value = next
  }

  async function login({ username, password, remember = true }) {
    if (!username?.trim() || !password?.trim()) {
      throw new Error('请输入账号和密码')
    }
    const res = await api.post('/api/auth/login', {
      username: username.trim(),
      password,
    })
    saveSession(res.data.access_token, res.data.user, remember)
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
    saveSession(res.data.access_token, res.data.user, true)
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
    sessionStorage.removeItem(STORAGE_KEY)
    session.value = null
  }

  function updateLocalProfile(profile) {
    localProfile.value = {
      ...localProfile.value,
      ...profile,
    }
    localStorage.setItem(PROFILE_KEY, JSON.stringify(localProfile.value))
  }

  return {
    session,
    isAuthenticated,
    user,
    login,
    register,
    changePassword,
    updateLocalProfile,
    logout,
  }
})
