<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const displayName = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

function validate() {
  if (!/^[a-zA-Z0-9_]{3,20}$/.test(username.value)) {
    return '账号需为3-20位字母、数字或下划线'
  }
  if (password.value.length < 6) {
    return '密码至少6位'
  }
  if (password.value !== confirmPassword.value) {
    return '两次密码不一致'
  }
  return ''
}

async function submitRegister() {
  error.value = validate()
  if (error.value) return

  loading.value = true
  try {
    await authStore.register({
      username: username.value,
      password: password.value,
      displayName: displayName.value,
    })
    router.replace('/dashboard')
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-panel card">
      <div class="login-brand">
        <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M15.7 3.8c-6.7.3-12 5.8-12 12.5 0 6.5 5 11.8 11.3 12.4" />
          <path d="M14.8 4.3c3.4 4 5 8.5 4.8 13.6" />
          <path d="M22 9.4c-3.5.5-6.2 2.2-8 5.1" />
          <path d="M26.8 16.2c-3.1-1.2-6.4-.6-9.8 1.8" />
          <path d="M23.8 5.5c-1.1 2.6-.8 5 .8 7.3" />
        </svg>
        <div>
          <h1>创建账号</h1>
          <p>智慧农业环境监测系统</p>
        </div>
      </div>

      <form class="login-form" @submit.prevent="submitRegister">
        <label>
          <span>账号</span>
          <input v-model.trim="username" autocomplete="username" placeholder="3-20位字母、数字或下划线">
        </label>
        <label>
          <span>显示名称 <small>(选填)</small></span>
          <input v-model.trim="displayName" autocomplete="name" placeholder="用于界面显示">
        </label>
        <label>
          <span>密码</span>
          <input v-model="password" type="password" autocomplete="new-password" placeholder="至少6位">
        </label>
        <label>
          <span>确认密码</span>
          <input v-model="confirmPassword" type="password" autocomplete="new-password" placeholder="再次输入密码">
        </label>
        <p v-if="error" class="login-error">{{ error }}</p>
        <button class="btn btn-primary" type="submit" :disabled="loading">
          {{ loading ? '注册中' : '注册' }}
        </button>
        <p class="login-link">已有账号? <router-link to="/login">登录</router-link></p>
      </form>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 20% 20%, rgba(47, 141, 78, 0.12), transparent 28%),
    linear-gradient(135deg, #f6f4ef, #edf3ed);
}

.login-panel {
  width: min(420px, 100%);
  padding: 28px;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 26px;
}

.login-brand svg {
  width: 42px;
  height: 42px;
  color: var(--green-deep);
}

.login-brand h1 {
  font-size: 24px;
  line-height: 1.15;
}

.login-brand p {
  margin-top: 4px;
  color: var(--text-secondary);
}

.login-form {
  display: grid;
  gap: 16px;
}

.login-form label {
  display: grid;
  gap: 7px;
  color: var(--text-secondary);
  font-weight: 650;
}

.login-form label small {
  font-weight: 400;
  color: var(--text-muted);
}

.login-form input {
  height: 42px;
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  padding: 0 12px;
  background: #fff;
  color: var(--text-primary);
  outline: none;
}

.login-form input:focus {
  border-color: var(--green-deep);
  box-shadow: 0 0 0 3px rgba(36, 113, 61, 0.1);
}

.login-error {
  color: var(--red);
  font-size: 13px;
}

.login-form .btn {
  width: 100%;
  height: 42px;
}

.login-link {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}
.login-link a {
  color: var(--green-deep);
  font-weight: 650;
  text-decoration: none;
}
.login-link a:hover {
  text-decoration: underline;
}
</style>
