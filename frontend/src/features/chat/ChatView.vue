<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useChatStore } from '../../stores/chat'
import ChatInput from './ChatInput.vue'
import ChatMessage from './ChatMessage.vue'

const store = useChatStore()
const listEl = ref<HTMLElement | null>(null)

const suggestions = [
  '¿Qué puedo cocinar hoy con lo que tengo?',
  'Sugiere una cena rápida con pollo',
  '¿Qué merienda saludable puedo hacer?',
]

function scrollToBottom(): void {
  nextTick(() => {
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  })
}

watch(
  () => store.messages.map((m) => ({ len: m.content.length, recipe: !!m.recipe })),
  scrollToBottom,
  { deep: true },
)

async function send(content: string): Promise<void> {
  await store.send(content)
}
</script>

<template>
  <div class="mx-auto flex h-[calc(100dvh-11.5rem)] max-w-3xl flex-col gap-4">
    <div ref="listEl" class="flex-1 space-y-4 overflow-y-auto pr-1">
      <div v-if="store.messages.length === 0" class="flex h-full flex-col items-center justify-center text-center">
        <div class="animate-float relative mb-6">
          <div
            class="flex h-28 w-28 items-center justify-center rounded-full bg-basil-100 shadow-inner"
          >
            <svg viewBox="0 0 48 48" class="h-14 w-14" fill="none" aria-hidden="true">
              <path d="M8 14h32v3H8z" fill="#2e513c" opacity=".85" />
              <path d="M8 17h32c0 8-3 13-16 13S8 25 8 17z" fill="#3f6b4f" />
              <path
                d="M16 8c0-2 1.4-2.6 1.4-4.6M26 8c0-2 1.4-2.6 1.4-4.6"
                stroke="#e8a33d"
                stroke-width="2.4"
                stroke-linecap="round"
                class="chat-hero-steam"
              />
            </svg>
          </div>
          <span
            class="absolute -right-1 -top-1 flex h-8 w-8 animate-pop items-center justify-center rounded-full bg-saffron-500 text-oat-50 shadow-lg"
            aria-hidden="true"
          >
            <svg viewBox="0 0 20 20" class="h-4 w-4" fill="currentColor">
              <path
                d="M10 1.8 11.9 7l5.3 1.6-5.3 1.6L10 15.8 8.1 10.2 2.8 8.6 8.1 7z"
              />
            </svg>
          </span>
        </div>

        <p
          class="flex items-center justify-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-basil-600"
        >
          <span class="h-px w-5 bg-saffron-500" />
          Asistente IA
        </p>
        <h2 class="font-display mt-2 text-3xl font-semibold text-basil-950">
          ¿Qué cocinamos hoy?
        </h2>
        <p class="mt-2 max-w-md text-sm leading-relaxed text-ink-500">
          Pregúntale qué puedes cocinar con tu despensa. Valida tu stock en tiempo
          real, sugiere recetas con lo que tienes y descuenta los ingredientes al cocinar.
        </p>

        <div class="mt-6 flex flex-wrap justify-center gap-2">
          <button
            v-for="s in suggestions"
            :key="s"
            class="rounded-full border border-oat-200 bg-white/80 px-4 py-2 text-sm font-medium text-basil-700 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-saffron-400 hover:text-saffron-700 hover:shadow-md"
            @click="send(s)"
          >
            {{ s }}
          </button>
        </div>
      </div>

      <ChatMessage
        v-for="(entry, index) in store.messages"
        :key="entry.id"
        :entry="entry"
        :pending="
          store.streaming &&
          index === store.messages.length - 1 &&
          entry.role === 'assistant' &&
          !entry.content &&
          !entry.recipe &&
          !entry.error
        "
      />
    </div>
    <ChatInput :disabled="store.streaming" @send="send" />
  </div>
</template>

<style scoped>
.chat-hero-steam {
  transform-origin: center;
  animation: steam 1.4s ease-in-out infinite;
}
.chat-hero-steam + .chat-hero-steam {
  animation-delay: 0.5s;
}
</style>
