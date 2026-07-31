<script setup lang="ts">
import { useToastsStore } from '../stores/toasts'

const store = useToastsStore()

const classes: Record<string, string> = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  error: 'border-tomato-100 bg-tomato-50 text-tomato-700',
  info: 'border-oat-200 bg-oat-50 text-ink-700',
}

const dot: Record<string, string> = {
  success: 'bg-emerald-500',
  error: 'bg-tomato-500',
  info: 'bg-saffron-500',
}
</script>

<template>
  <div
    class="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex flex-col items-center gap-2 px-4"
    aria-live="polite"
  >
    <transition-group name="toast">
      <div
        v-for="toast in store.toasts"
        :key="toast.id"
        :class="classes[toast.type]"
        data-test="toast"
        class="pointer-events-auto flex items-center gap-3 rounded-full border px-4 py-2.5 text-sm font-medium shadow-lg"
      >
        <span :class="dot[toast.type]" class="h-2 w-2 shrink-0 rounded-full" />
        <span>{{ toast.message }}</span>
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
          class="rounded p-1 leading-none opacity-60 transition hover:opacity-100"
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
  transition:
    opacity 0.25s ease,
    transform 0.25s cubic-bezier(0.34, 1.3, 0.64, 1);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.96);
}
</style>
