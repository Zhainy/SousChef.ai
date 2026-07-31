<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useChatStore } from '../../stores/chat'
import AppLoader from '../../components/ui/AppLoader.vue'
import ChatInput from './ChatInput.vue'
import ChatMessage from './ChatMessage.vue'

const store = useChatStore()
const listEl = ref<HTMLElement | null>(null)

const suggestions = [
  '¿Qué puedo cocinar hoy con lo que tengo?',
  'Sugiere una cena rápida con pollo',
  '¿Qué merienda saludable puedo hacer?',
]

const thinking = computed(() => {
  const last = store.messages[store.messages.length - 1]
  return (
    store.streaming &&
    !!last &&
    last.role === 'assistant' &&
    !last.content &&
    !last.recipe &&
    !last.error
  )
})

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
  <div class="mx-auto flex h-[calc(100dvh-11.5rem)] w-full max-w-3xl flex-col gap-4">
    <div ref="listEl" class="chat-scroll relative flex-1 overflow-y-auto pr-1">
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

      <TransitionGroup v-else name="message" tag="div" class="space-y-4">
        <ChatMessage
          v-for="(entry, index) in store.messages"
          :key="entry.id"
          :entry="entry"
          :pending="index === store.messages.length - 1 && thinking"
        />
      </TransitionGroup>

      <Transition name="thinking">
        <div
          v-if="thinking"
          class="pointer-events-none absolute inset-0 z-10 flex items-center justify-center"
        >
          <AppLoader size="lg" tone="saffron" :role="null" />
        </div>
      </Transition>
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

.message-enter-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s cubic-bezier(0.34, 1.3, 0.64, 1);
}
.message-enter-from {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}
.message-move {
  transition: transform 0.3s ease;
}

.chat-scroll {
  scrollbar-width: thin;
  scrollbar-color: var(--color-basil-300) transparent;
}
.chat-scroll::-webkit-scrollbar {
  width: 8px;
}
.chat-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.chat-scroll::-webkit-scrollbar-thumb {
  background-color: var(--color-basil-300);
  border-radius: 9999px;
}
.chat-scroll::-webkit-scrollbar-thumb:hover {
  background-color: var(--color-basil-500);
}

.thinking-enter-active,
.thinking-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s cubic-bezier(0.34, 1.3, 0.64, 1);
}
.thinking-enter-from,
.thinking-leave-to {
  opacity: 0;
  transform: scale(0.92);
}
</style>
