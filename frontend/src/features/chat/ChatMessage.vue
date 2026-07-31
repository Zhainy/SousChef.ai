<script setup lang="ts">
import type { ChatEntry } from '../../stores/chat'
import AppLoader from '../../components/ui/AppLoader.vue'
import RecipeCard from './RecipeCard.vue'
import TypingIndicator from './TypingIndicator.vue'

defineProps<{ entry: ChatEntry; pending?: boolean }>()
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
      <p v-if="entry.content" class="whitespace-pre-wrap">{{ entry.content }}</p>
      <TypingIndicator v-else-if="pending" class="py-1" />
      <RecipeCard
        v-if="entry.recipe"
        :recipe="entry.recipe"
        :image-url="entry.imageUrl"
        :image-pending="entry.imagePending"
        class="mt-2"
      />
      <p v-if="entry.error" class="mt-2 text-sm text-tomato-600">{{ entry.error }}</p>
    </div>
  </div>
</template>
