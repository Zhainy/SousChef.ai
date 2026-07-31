import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useRecipesStore } from './recipes'
import type { Recipe, SavedRecipe } from '../types'

const STORAGE_KEY = 'souschef.recipes.v1'

function recipe(hash: string, nombre = `Receta ${hash}`): Recipe {
  return { nombre, ingredientes: [{ nombre: 'tomate', cantidad: 1 }], hash }
}

function seed(saved: SavedRecipe[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(saved))
}

function daysAgo(days: number): string {
  return new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString()
}

function savedEntry(hash: string, overrides: Partial<SavedRecipe> = {}): SavedRecipe {
  return {
    hash,
    recipe: recipe(hash),
    imageUrl: null,
    favorited: false,
    createdAt: new Date().toISOString(),
    cookedAt: null,
    ...overrides,
  }
}

describe('useRecipesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('save agrega y persiste en localStorage', () => {
    const store = useRecipesStore()
    store.save(recipe('h1'), null)
    expect(store.saved).toHaveLength(1)
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    expect(raw[0].hash).toBe('h1')
  })

  it('upsert conserva favorited, cookedAt y createdAt', () => {
    const store = useRecipesStore()
    store.save(recipe('h1'), null)
    const createdAt = store.getByHash('h1')!.createdAt
    store.toggleFavorite('h1')
    store.markCooked('h1')
    store.save({ ...recipe('h1'), resumen: 'actualizado' }, '/static/h1.png')
    const s = store.getByHash('h1')!
    expect(s.favorited).toBe(true)
    expect(s.cookedAt).not.toBeNull()
    expect(s.createdAt).toBe(createdAt)
    expect(s.imageUrl).toBe('/static/h1.png')
    expect(s.recipe.resumen).toBe('actualizado')
    expect(store.saved).toHaveLength(1)
  })

  it('toggleFavorite invierte el estado', () => {
    const store = useRecipesStore()
    store.save(recipe('h1'), null)
    store.toggleFavorite('h1')
    expect(store.getByHash('h1')!.favorited).toBe(true)
    store.toggleFavorite('h1')
    expect(store.getByHash('h1')!.favorited).toBe(false)
  })

  it('delDia es null sin recetas cocinadas hoy y toma la más reciente del día', () => {
    const store = useRecipesStore()
    store.save(recipe('a'), null)
    store.save(recipe('b'), null)
    store.saved[0].cookedAt = daysAgo(1)
    expect(store.delDia).toBeNull()
    const now = Date.now()
    store.saved[0].cookedAt = new Date(now).toISOString()
    store.saved[1].cookedAt = new Date(now + 1000).toISOString()
    expect(store.delDia?.hash).toBe('b')
  })

  it('generadasHoy filtra por el día actual y ordena por fecha desc', () => {
    seed([
      savedEntry('ayer', { createdAt: daysAgo(1) }),
      savedEntry('hoy-1', { createdAt: new Date(Date.now() - 60_000).toISOString() }),
      savedEntry('hoy-2', { createdAt: new Date().toISOString() }),
    ])
    const store = useRecipesStore()
    expect(store.generadasHoy.map((r) => r.hash)).toEqual(['hoy-2', 'hoy-1'])
  })

  it('favoritas devuelve solo las marcadas', () => {
    seed([
      savedEntry('fav', { favorited: true }),
      savedEntry('no'),
    ])
    const store = useRecipesStore()
    expect(store.favoritas.map((r) => r.hash)).toEqual(['fav'])
  })

  it('hidrata desde localStorage al crear el store', () => {
    seed([savedEntry('h1', { imageUrl: '/static/h1.png', favorited: true })])
    const store = useRecipesStore()
    expect(store.getByHash('h1')?.favorited).toBe(true)
    expect(store.getByHash('h1')?.imageUrl).toBe('/static/h1.png')
  })

  it('prune elimina no favoritas de más de 7 días', () => {
    seed([
      savedEntry('vieja', { createdAt: daysAgo(8) }),
      savedEntry('fav-vieja', { createdAt: daysAgo(8), favorited: true }),
      savedEntry('reciente', { createdAt: daysAgo(2) }),
    ])
    const store = useRecipesStore()
    expect(store.saved.map((r) => r.hash)).toEqual(['fav-vieja', 'reciente'])
  })

  it('remove elimina, persiste y devuelve la entrada', () => {
    const store = useRecipesStore()
    store.save(recipe('h1'), null)
    const removed = store.remove('h1')
    expect(removed?.hash).toBe('h1')
    expect(store.getByHash('h1')).toBeUndefined()
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    expect(raw).toHaveLength(0)
  })

  it('remove devuelve undefined con hash inexistente', () => {
    const store = useRecipesStore()
    expect(store.remove('nope')).toBeUndefined()
  })

  it('restore re-inserta preservando favorited, cookedAt y createdAt', () => {
    const store = useRecipesStore()
    store.save(recipe('h1'), null)
    store.toggleFavorite('h1')
    store.markCooked('h1')
    const entry = store.remove('h1')!
    expect(entry.favorited).toBe(true)
    store.restore(entry)
    const s = store.getByHash('h1')!
    expect(s.favorited).toBe(true)
    expect(s.cookedAt).not.toBeNull()
    expect(s.createdAt).toBe(entry.createdAt)
    expect(store.saved).toHaveLength(1)
  })

  it('restore no duplica si el hash ya existe', () => {
    const store = useRecipesStore()
    store.save(recipe('h1'), null)
    store.restore(store.getByHash('h1')!)
    expect(store.saved).toHaveLength(1)
  })
})
