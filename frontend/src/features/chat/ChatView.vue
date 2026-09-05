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

const awaiting = computed(() => {
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

const thinking = computed(() => awaiting.value && store.messages.length <= 2)

const followUpSuggestions = computed(() => {
  if (store.streaming || store.messages.length === 0) return []
  const last = store.messages[store.messages.length - 1]
  if (!last || last.role !== 'assistant') return []

  if (last.recipe) {
    const mainIng = last.recipe.ingredientes[0]?.nombre || 'mis ingredientes'
    return [
      `¿Qué otra receta puedo hacer usando ${mainIng}?`,
      'Dame una opción más rápida o ligera',
      '¿Qué postre o merienda puedo preparar con lo que tengo?',
    ]
  }
  return [
    '¿Qué otra receta me sugieres con mis ingredientes?',
    'Dame una opción rápida de menos de 20 minutos',
    '¿Cómo puedo aprovechar lo que está por vencer?',
  ]
})

// Badge del proveedor de IA: muestra el último proveedor usado por un mensaje del asistente
const aiProviderBadge = computed(() => {
  const last = [...store.messages].reverse().find(
    (m) => m.role === 'assistant' && m.aiProvider !== null,
  )
  if (!last) return null
  return { provider: last.aiProvider, fallback: last.aiFallback }
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
  <div class="mx-auto flex h-[calc(100dvh-11.5rem)] w-full max-w-3xl flex-col gap-3">
    <!-- Barra superior: Limpiar chat y Badge de IA -->
    <div
      v-if="store.messages.length > 0"
      class="flex items-center justify-between px-1"
    >
      <button
        type="button"
        data-test="clear-chat"
        class="inline-flex items-center gap-1.5 rounded-full border border-oat-200 bg-white/80 px-3 py-1 text-xs font-medium text-ink-600 shadow-sm backdrop-blur transition hover:border-tomato-300 hover:bg-tomato-50 hover:text-tomato-700"
        title="Limpiar conversación"
        @click="store.clear()"
      >
        <svg viewBox="0 0 20 20" class="h-3.5 w-3.5" fill="currentColor" aria-hidden="true">
          <path
            fill-rule="evenodd"
            d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
            clip-rule="evenodd"
          />
        </svg>
        Limpiar chat
      </button>

      <span
        v-if="aiProviderBadge"
        :class="[
          'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-wide transition-colors duration-300',
          aiProviderBadge.fallback
            ? 'bg-amber-100 text-amber-700 ring-1 ring-amber-300'
            : aiProviderBadge.provider === 'oci'
              ? 'bg-basil-100 text-basil-700 ring-1 ring-basil-300'
              : 'bg-oat-100 text-ink-500 ring-1 ring-oat-300',
        ]"
      >
        <span aria-hidden="true">
          {{ aiProviderBadge.provider === 'oci' ? '✦' : '⚡' }}
        </span>
        <span>
          {{
            aiProviderBadge.provider === 'oci'
              ? 'OCI AI'
              : aiProviderBadge.fallback
                ? 'Local AI (fallback)'
                : 'Local AI'
          }}
        </span>
      </span>
    </div>

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
          :pending="index === store.messages.length - 1 && awaiting"
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

    <!-- Sugerencias de seguimiento (3 alternativas) -->
    <Transition name="fade">
      <div
        v-if="followUpSuggestions.length > 0"
        class="flex flex-wrap items-center gap-1.5 px-1"
      >
        <span class="text-[11px] font-medium uppercase tracking-wider text-ink-400">
          Sugerencias:
        </span>
        <button
          v-for="alt in followUpSuggestions"
          :key="alt"
          class="rounded-full border border-oat-200 bg-white/90 px-3 py-1 text-xs font-medium text-basil-800 shadow-sm transition hover:-translate-y-0.5 hover:border-saffron-400 hover:text-saffron-700 hover:shadow"
          @click="send(alt)"
        >
          💡 {{ alt }}
        </button>
      </div>
    </Transition>

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

.badge-enter-active,
.badge-leave-active {
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.34, 1.3, 0.64, 1);
}
.badge-enter-from,
.badge-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.95);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
