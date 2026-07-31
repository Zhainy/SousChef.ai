<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ disabled: boolean }>()

const emit = defineEmits<{ send: [content: string] }>()

const text = ref('')

function submit(): void {
  const value = text.value.trim()
  if (!value || props.disabled) return
  emit('send', value)
  text.value = ''
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}
</script>

<template>
  <div class="flex items-end gap-2">
    <textarea
      v-model="text"
      rows="1"
      :disabled="disabled"
      placeholder="Ej: ¿qué puedo cocinar hoy con pollo?"
      class="flex-1 resize-none rounded-2xl border border-stone-300 bg-white px-4 py-3 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200 disabled:opacity-60"
      @keydown="onKeydown"
    />
    <button
      :disabled="disabled || !text.trim()"
      class="flex items-center gap-2 rounded-2xl bg-amber-600 px-5 py-3 font-medium text-white transition hover:bg-amber-700 disabled:opacity-50"
      @click="submit"
    >
      <span
        v-if="disabled"
        class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
      />
      {{ disabled ? 'Generando…' : 'Enviar' }}
    </button>
  </div>
</template>
