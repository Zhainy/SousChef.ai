import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { Ingredient, Recipe, StockResult } from '../types'
import * as api from '../lib/api'

export const usePantryStore = defineStore('pantry', () => {
  const items = ref<Ingredient[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const categorias = computed(() =>
    [...new Set(items.value.map((i) => i.categoria))].sort(),
  )

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      items.value = await api.fetchIngredients()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Error al cargar la despensa'
    } finally {
      loading.value = false
    }
  }

  async function create(body: Omit<Ingredient, 'id' | 'created_at'>): Promise<void> {
    const created = await api.createIngredient(body)
    items.value.push(created)
  }

  async function update(id: number, body: Partial<Ingredient>): Promise<void> {
    const updated = await api.updateIngredient(id, body)
    const idx = items.value.findIndex((i) => i.id === id)
    if (idx !== -1) items.value[idx] = updated
  }

  async function remove(id: number): Promise<void> {
    await api.deleteIngredient(id)
    items.value = items.value.filter((i) => i.id !== id)
  }

  async function cook(recipe: Recipe): Promise<StockResult> {
    const result = await api.cookRecipe(recipe)
    await load()
    return result
  }

  return { items, loading, error, categorias, load, create, update, remove, cook }
})
