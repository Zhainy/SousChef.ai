import { ref } from 'vue'
import { defineStore } from 'pinia'

export type ToastType = 'success' | 'error' | 'info'

export interface ToastAction {
  label: string
  onClick: () => void
}

export interface Toast {
  id: number
  type: ToastType
  message: string
  action?: ToastAction
}

let nextId = 1

export const useToastsStore = defineStore('toasts', () => {
  const toasts = ref<Toast[]>([])

  function notify(
    message: string,
    type: ToastType = 'info',
    duration = 6000,
    action?: ToastAction,
  ): void {
    const id = nextId++
    toasts.value.push({ id, type, message, action })
    window.setTimeout(() => dismiss(id), duration)
  }

  function dismiss(id: number): void {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  return { toasts, notify, dismiss }
})
