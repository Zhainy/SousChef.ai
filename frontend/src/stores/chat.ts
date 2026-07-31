import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { Recipe } from '../types'
import { postSseStream, type SseEvent } from '../lib/sse'

export interface ChatEntry {
  id: number
  role: 'user' | 'assistant'
  content: string
  recipe: Recipe | null
  imageUrl: string | null
  imagePending: boolean
  toolStatus: string | null
  error: string | null
}

let nextId = 1

function newEntry(role: ChatEntry['role'], content = ''): ChatEntry {
  return {
    id: nextId++,
    role,
    content,
    recipe: null,
    imageUrl: null,
    imagePending: false,
    toolStatus: null,
    error: null,
  }
}

function applyEvent(entry: ChatEntry, ev: SseEvent): void {
  switch (ev.event) {
    case 'token':
      entry.content += (ev.data as { delta: string }).delta
      break
    case 'tool_call':
      entry.toolStatus = `Consultando ${(ev.data as { name: string }).name}…`
      break
    case 'tool_result':
      entry.toolStatus = null
      break
    case 'recipe':
      entry.recipe = ev.data as Recipe
      entry.imagePending = true
      break
    case 'recipe_image':
      entry.imagePending = false
      entry.imageUrl = (ev.data as { image_url: string | null }).image_url
      break
    case 'error':
      entry.error = (ev.data as { message: string }).message
      break
  }
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatEntry[]>([])
  const streaming = ref(false)

  async function send(content: string): Promise<void> {
    const trimmed = content.trim()
    if (!trimmed || streaming.value) return
    messages.value.push(newEntry('user', trimmed))
    const entry = newEntry('assistant')
    messages.value.push(entry)
    streaming.value = true
    const history = messages.value
      .filter((m) => m.content.length > 0)
      .map((m) => ({ role: m.role, content: m.content }))
    try {
      for await (const ev of postSseStream('/api/chat', { messages: history })) {
        applyEvent(entry, ev)
      }
    } catch (e) {
      entry.error = e instanceof Error ? e.message : 'Error de conexión'
    } finally {
      streaming.value = false
    }
  }

  function clear(): void {
    messages.value = []
  }

  return { messages, streaming, send, clear }
})
