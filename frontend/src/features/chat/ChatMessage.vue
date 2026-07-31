<script setup lang="ts">
import type { ChatEntry } from '../../stores/chat'
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
          ? 'rounded-2xl bg-amber-600 text-white'
          : 'rounded-2xl border border-stone-200 bg-white text-stone-900'
      "
      class="max-w-[85%] px-4 py-3 shadow-sm"
    >
      <p
        v-if="entry.toolStatus"
        class="mb-1 flex items-center gap-2 text-sm italic opacity-80"
      >
        <span
          class="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
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
      <p v-if="entry.error" class="mt-2 text-sm text-red-600">{{ entry.error }}</p>
    </div>
  </div>
</template>
