import { reactive } from 'vue'

export const toasts = reactive([])
let toastId = 0

export function showToast({ title = '', message = '', type = 'warn', duration = 4000 } = {}) {
  const id = ++toastId
  toasts.push({ id, title, message, type })
  setTimeout(() => {
    const idx = toasts.findIndex(t => t.id === id)
    if (idx !== -1) toasts.splice(idx, 1)
  }, duration)
}
