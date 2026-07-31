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
    <div
      class="fixed inset-0 z-40 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      :aria-label="title ?? 'Diálogo'"
    >
      <div class="absolute inset-0 bg-black/40" @click="emit('close')" />
      <div class="relative w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div
          v-if="title"
          class="flex items-center justify-between border-b border-stone-200 px-5 py-3"
        >
          <h2 class="text-lg font-bold">{{ title }}</h2>
          <button
            aria-label="Cerrar"
            class="rounded-lg px-2 py-1 text-stone-500 transition hover:bg-stone-100"
            @click="emit('close')"
          >
            ✕
          </button>
        </div>
        <div class="max-h-[80vh] overflow-y-auto p-5">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>
