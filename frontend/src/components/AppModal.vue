<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

defineProps<{ title?: string }>()
const emit = defineEmits<{ close: [] }>()

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition name="modal" appear>
      <div
        class="fixed inset-0 z-40 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        :aria-label="title ?? 'Diálogo'"
      >
        <div class="absolute inset-0 bg-basil-950/50 backdrop-blur-sm" @click="emit('close')" />
        <div
          class="relative w-full max-w-lg overflow-hidden rounded-2xl border border-oat-200 bg-oat-50 shadow-2xl"
        >
          <div
            v-if="title"
            class="flex items-center justify-between border-b border-oat-200 bg-white/60 px-5 py-3"
          >
            <h2 class="font-display text-lg font-semibold text-basil-900">
              {{ title }}
            </h2>
            <button
              aria-label="Cerrar"
              class="rounded-lg px-2 py-1 text-ink-400 transition hover:bg-oat-100 hover:text-ink-700"
              @click="emit('close')"
            >
              <svg viewBox="0 0 20 20" class="h-5 w-5" fill="none" aria-hidden="true">
                <path
                  d="M6 6l8 8M14 6l-8 8"
                  stroke="currentColor"
                  stroke-width="1.8"
                  stroke-linecap="round"
                />
              </svg>
            </button>
          </div>
          <div class="max-h-[80vh] overflow-y-auto p-5">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-active .rounded-2xl,
.modal-leave-active .rounded-2xl {
  transition:
    transform 0.22s cubic-bezier(0.34, 1.3, 0.64, 1),
    opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .rounded-2xl {
  transform: scale(0.95) translateY(8px);
  opacity: 0;
}
.modal-leave-to .rounded-2xl {
  transform: scale(0.97);
  opacity: 0;
}
</style>
