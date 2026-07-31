import { computed, ref } from 'vue'
import { acceptHMRUpdate, defineStore } from 'pinia'
import type { Recipe, SavedRecipe } from '../types'

const STORAGE_KEY = 'souschef.recipes.v1'
const PRUNE_DAYS = 7
const DAY_MS = 24 * 60 * 60 * 1000

function dayKey(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function todayKey(): string {
  return dayKey(new Date())
}

function isSavedRecipe(r: unknown): r is SavedRecipe {
  return (
    !!r &&
    typeof r === 'object' &&
    typeof (r as SavedRecipe).hash === 'string' &&
    !!(r as SavedRecipe).recipe
  )
}

function loadSaved(): SavedRecipe[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter(isSavedRecipe) : []
  } catch {
    return []
  }
}

function prune(saved: SavedRecipe[]): SavedRecipe[] {
  const cutoff = Date.now() - PRUNE_DAYS * DAY_MS
  return saved.filter((r) => r.favorited || new Date(r.createdAt).getTime() >= cutoff)
}

export const useRecipesStore = defineStore('recipes', () => {
  const saved = ref<SavedRecipe[]>(prune(loadSaved()))

  function persist(): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved.value))
  }

  function findIndex(hash: string): number {
    return saved.value.findIndex((r) => r.hash === hash)
  }

  function save(recipe: Recipe, imageUrl: string | null): void {
    const hash = recipe.hash
    if (!hash) return
    const idx = findIndex(hash)
    if (idx !== -1) {
      const entry = saved.value[idx]
      entry.recipe = recipe
      entry.imageUrl = imageUrl ?? entry.imageUrl
    } else {
      saved.value.push({
        hash,
        recipe,
        imageUrl,
        favorited: false,
        createdAt: new Date().toISOString(),
        cookedAt: null,
      })
    }
    persist()
  }

  function updateImage(hash: string, url: string | null): void {
    const idx = findIndex(hash)
    if (idx === -1) return
    saved.value[idx].imageUrl = url
    persist()
  }

  function toggleFavorite(hash: string): void {
    const idx = findIndex(hash)
    if (idx === -1) return
    saved.value[idx].favorited = !saved.value[idx].favorited
    persist()
  }

  function markCooked(hash: string): void {
    const idx = findIndex(hash)
    if (idx === -1) return
    saved.value[idx].cookedAt = new Date().toISOString()
    persist()
  }

  function remove(hash: string): SavedRecipe | undefined {
    const idx = findIndex(hash)
    if (idx === -1) return undefined
    const [removed] = saved.value.splice(idx, 1)
    persist()
    return removed
  }

  function restore(entry: SavedRecipe): void {
    if (findIndex(entry.hash) !== -1) return
    saved.value.push(entry)
    persist()
  }

  function getByHash(hash: string): SavedRecipe | undefined {
    return saved.value.find((r) => r.hash === hash)
  }

  const generadasHoy = computed<SavedRecipe[]>(() => {
    const today = todayKey()
    return [...saved.value]
      .filter((r) => dayKey(new Date(r.createdAt)) === today)
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  })

  const favoritas = computed<SavedRecipe[]>(() => saved.value.filter((r) => r.favorited))

  const delDia = computed<SavedRecipe | null>(() => {
    const today = todayKey()
    const cookedToday = saved.value
      .filter((r) => r.cookedAt && dayKey(new Date(r.cookedAt)) === today)
      .sort((a, b) => (b.cookedAt as string).localeCompare(a.cookedAt as string))
    return cookedToday[0] ?? null
  })

  return {
    saved,
    save,
    updateImage,
    toggleFavorite,
    markCooked,
    remove,
    restore,
    getByHash,
    generadasHoy,
    favoritas,
    delDia,
  }
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useRecipesStore, import.meta.hot))
}
