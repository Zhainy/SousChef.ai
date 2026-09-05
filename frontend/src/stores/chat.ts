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
  aiProvider: 'oci' | 'local' | null
  aiFallback: boolean
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
    aiProvider: null,
    aiFallback: false,
  }
}

function stripRecipeFence(text: string): string {
  return text.replace(/```[\s\S]*?```/g, '').trim()
}

function trimRecipeNarrative(text: string): string {
  const idx = text.search(/Ingredientes:|Ingredients:/i)
  return idx === -1 ? text : text.slice(0, idx).trim()
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function highlightRecipeName(text: string, name: string): string {
  const words = name.split(/\s+/).filter(Boolean)
  for (let len = words.length; len >= 1; len--) {
    const candidate = words.slice(0, len).join(' ')
    const re = new RegExp(
      `(\\s|^)\\*{0,2}\\s*(${escapeRegExp(candidate)})(\\s*)\\*{0,2}(?=[\\s.,;:!?¿¡]|$)`,
      'i',
    )
    const match = text.match(re)
    if (match) return text.replace(re, `$1**${match[2]}**$3`)
  }
  return text
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
      entry.content = highlightRecipeName(
        trimRecipeNarrative(stripRecipeFence(entry.content)),
        entry.recipe.nombre,
      )
      entry.imagePending = true
      break
    case 'recipe_image':
      entry.imagePending = false
      entry.imageUrl = (ev.data as { image_url: string | null }).image_url
      break
    case 'provider_info': {
      const info = ev.data as { provider: 'oci' | 'local'; fallback: boolean }
      entry.aiProvider = info.provider
      entry.aiFallback = info.fallback
      break
    }
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

  async function forceRecipe(): Promise<void> {
    const last = messages.value[messages.value.length - 1]
    if (
      !last ||
      last.role !== 'assistant' ||
      !last.content ||
      last.recipe ||
      last.error ||
      streaming.value
    )
      return
    streaming.value = true
    const history = messages.value
      .filter((m) => m.content.length > 0)
      .map((m) => ({ role: m.role, content: m.content }))
    try {
      for await (const ev of postSseStream('/api/chat', { messages: history, force_recipe: true })) {
        if (ev.event === 'recipe') {
          last.recipe = ev.data as Recipe
          last.imagePending = true
        } else if (ev.event === 'recipe_image') {
          last.imagePending = false
          last.imageUrl = (ev.data as { image_url: string | null }).image_url
        } else if (ev.event === 'error') {
          last.error = (ev.data as { message: string }).message
        }
      }
      if (!last.recipe && !last.error) {
        last.error = 'No pude convertir la respuesta en una receta. Inténtalo de nuevo.'
      }
    } catch (e) {
      last.error = e instanceof Error ? e.message : 'Error de conexión'
    } finally {
      streaming.value = false
    }
  }

  function clear(): void {
    messages.value = []
  }

  return { messages, streaming, send, forceRecipe, clear }
})
