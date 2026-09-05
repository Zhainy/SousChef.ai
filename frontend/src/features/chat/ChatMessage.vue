<script setup lang="ts">
import { computed } from 'vue'
import { useChatStore, type ChatEntry } from '../../stores/chat'
import AppLoader from '../../components/ui/AppLoader.vue'
import MarkdownText from '../../components/MarkdownText.vue'
import RecipeCard from './RecipeCard.vue'
import TypingIndicator from './TypingIndicator.vue'

const props = defineProps<{ entry: ChatEntry; pending?: boolean }>()

const store = useChatStore()

const isLast = computed(() => {
  const last = store.messages[store.messages.length - 1]
  return last?.id === props.entry.id
})

const canAskRecipe = computed(
  () =>
    isLast.value &&
    props.entry.role === 'assistant' &&
    !!props.entry.content &&
    !props.entry.recipe &&
    !props.entry.error,
)

const askingRecipe = computed(() => canAskRecipe.value && store.streaming)
</script>

<template>
  <div
    :class="entry.role === 'user' ? 'justify-end' : 'justify-start'"
    class="flex"
  >
    <div
      :class="
        entry.role === 'user'
          ? 'rounded-2xl rounded-br-md bg-gradient-to-br from-basil-700 to-basil-900 text-oat-50 shadow-md shadow-basil-900/25'
          : 'rounded-2xl rounded-bl-md border border-oat-200 bg-white/85 text-ink-900 shadow-sm backdrop-blur'
      "
      class="max-w-[85%] px-4 py-3"
    >
      <p
        v-if="entry.toolStatus"
        class="mb-1 flex items-center gap-2 text-sm font-medium italic text-basil-700"
      >
        <AppLoader size="sm" tone="saffron" role="progress" />
        {{ entry.toolStatus }}
      </p>
      <MarkdownText
        v-if="entry.content"
        :text="entry.content"
        class="text-sm leading-relaxed"
      />
      <TypingIndicator v-else-if="pending" class="py-1" />
      <RecipeCard
        v-if="entry.recipe"
        :recipe="entry.recipe"
        :image-url="entry.imageUrl"
        :image-pending="entry.imagePending"
        class="mt-2"
      />
      <button
        v-if="canAskRecipe && !askingRecipe"
        data-test="ask-recipe"
        class="mt-2 flex items-center gap-1.5 rounded-full border border-basil-200 bg-basil-50 px-3.5 py-1.5 text-sm font-semibold text-basil-700 transition hover:border-saffron-400 hover:text-saffron-700"
        @click="store.forceRecipe()"
      >
        <svg viewBox="0 0 20 20" class="h-4 w-4" fill="currentColor" aria-hidden="true">
          <path
            d="M8 1.5 9.4 6l4.6 1.5L9.4 9 8 13.5 6.6 9 2 7.5 6.6 6z"
          />
          <path
            d="M15.5 11.5l.7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7z"
          />
        </svg>
        Obtener la receta
      </button>
      <span
        v-else-if="askingRecipe"
        data-test="asking-recipe"
        class="mt-2 flex items-center gap-2 text-sm font-medium italic text-basil-700"
      >
        <AppLoader size="sm" tone="saffron" role="progress" />
        Obteniendo receta…
      </span>
      <p v-if="entry.error" class="mt-2 text-sm text-tomato-600">{{ entry.error }}</p>
    </div>
  </div>
</template>
