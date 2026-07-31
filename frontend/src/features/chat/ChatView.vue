<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useChatStore } from '../../stores/chat'
import ChatInput from './ChatInput.vue'
import ChatMessage from './ChatMessage.vue'

const store = useChatStore()
const listEl = ref<HTMLElement | null>(null)

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
  <div class="flex h-[calc(100vh-10rem)] flex-col gap-4">
    <div ref="listEl" class="flex-1 space-y-4 overflow-y-auto pr-1">
      <ChatMessage
        v-for="entry in store.messages"
        :key="entry.id"
        :entry="entry"
      />
      <p
        v-if="store.messages.length === 0"
        class="mt-16 text-center text-stone-400"
      >
        Pregúntale al asistente qué puedes cocinar con tu despensa.
      </p>
    </div>
    <ChatInput :disabled="store.streaming" @send="send" />
  </div>
</template>
