<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import AppLoader from '../../components/ui/AppLoader.vue'

const props = defineProps<{ disabled: boolean }>()

const emit = defineEmits<{ send: [content: string] }>()

const text = ref('')
const textarea = ref<HTMLTextAreaElement | null>(null)

function autoResize(): void {
  const el = textarea.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 160)}px`
}

function submit(): void {
  const value = text.value.trim()
  if (!value || props.disabled) return
  emit('send', value)
  text.value = ''
  nextTick(() => {
    if (textarea.value) textarea.value.style.height = 'auto'
  })
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}

onMounted(autoResize)
</script>

<template>
  <div class="flex items-end gap-2">
    <div
      class="flex flex-1 items-end rounded-3xl border border-oat-200 bg-white/90 p-2 shadow-md shadow-basil-900/5 backdrop-blur transition focus-within:border-basil-500 focus-within:ring-4 focus-within:ring-basil-100"
    >
      <textarea
        id="chat-message-input"
        name="chat-message-input"
        ref="textarea"
        v-model="text"
        rows="1"
        :disabled="disabled"
        placeholder="Ej: ¿qué puedo cocinar hoy con pollo?"
        class="scrollbar-none max-h-40 flex-1 resize-none overflow-y-auto bg-transparent px-2 py-2 text-sm leading-relaxed focus:outline-none disabled:opacity-60"
        @input="autoResize"
        @keydown="onKeydown"
      />
      <button
        :disabled="disabled || !text.trim()"
        class="flex shrink-0 items-center justify-center gap-2 rounded-2xl bg-basil-800 px-4 py-2.5 text-sm font-semibold text-oat-50 shadow-md shadow-basil-900/25 transition-all duration-200 hover:-translate-y-0.5 hover:bg-basil-700 disabled:translate-y-0 disabled:opacity-50"
        @click="submit"
      >
        <AppLoader v-if="disabled" size="sm" tone="light" label="" :role="null" />
        <svg
          v-else
          viewBox="0 0 20 20"
          class="h-4 w-4"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M10 3v11m0 0 4-4m-4 4-4-4"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        {{ disabled ? 'Generando…' : 'Enviar' }}
      </button>
    </div>
  </div>
</template>
