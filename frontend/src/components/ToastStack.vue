<script setup lang="ts">
import { useToastsStore } from '../stores/toasts'

const store = useToastsStore()

const classes: Record<string, string> = {
  success: 'border-emerald-200 bg-emerald-50/95 text-emerald-900 shadow-emerald-950/10',
  error: 'border-tomato-200 bg-tomato-50/95 text-tomato-800 shadow-tomato-950/10',
  info: 'border-oat-300 bg-white/95 text-ink-800 shadow-basil-950/10',
}

const dot: Record<string, string> = {
  success: 'bg-emerald-500',
  error: 'bg-tomato-500',
  info: 'bg-saffron-500',
}
</script>

<template>
  <div
    class="pointer-events-none fixed top-20 right-4 sm:right-6 z-50 flex flex-col items-end gap-2.5 max-w-sm w-full px-4 sm:px-0"
    aria-live="polite"
  >
    <transition-group name="toast">
      <div
        v-for="toast in store.toasts"
        :key="toast.id"
        :class="classes[toast.type]"
        data-test="toast"
        class="pointer-events-auto flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm font-medium shadow-xl backdrop-blur transition-all"
      >
        <span :class="dot[toast.type]" class="h-2.5 w-2.5 shrink-0 rounded-full" />
        <span class="flex-1 leading-snug">{{ toast.message }}</span>
        <button
          v-if="toast.action"
          data-test="toast-action"
          class="rounded-full bg-basil-800 px-3 py-1 text-xs font-semibold text-oat-50 transition hover:bg-basil-700"
          @click="() => { toast.action?.onClick(); store.dismiss(toast.id) }"
        >
          {{ toast.action.label }}
        </button>
        <button
          aria-label="Cerrar notificación"
          class="rounded p-1 leading-none text-ink-400 opacity-70 transition hover:opacity-100 hover:text-ink-700"
          @click="store.dismiss(toast.id)"
        >
          <svg viewBox="0 0 16 16" class="h-3.5 w-3.5" fill="none" aria-hidden="true">
            <path
              d="M4 4l8 8M12 4l-8 8"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
            />
          </svg>
        </button>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(40px) scale(0.95);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(40px) scale(0.95);
}
</style>
