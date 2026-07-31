import type { Ingredient, Recipe, StockResult } from '../types'

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(ApiError.messageFromDetail(status, detail))
    this.status = status
    this.detail = detail
  }

  private static messageFromDetail(status: number, detail: unknown): string {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string; loc?: unknown } | undefined
      const loc = Array.isArray(first?.loc)
        ? String(first.loc[first.loc.length - 1])
        : ''
      return first?.msg ? `Datos inválidos${loc ? `: ${loc}` : ''}` : `Error ${status}`
    }
    if (detail && typeof detail === 'object') {
      const inner = (detail as { detail?: unknown }).detail
      if (typeof inner === 'string') return inner
    }
    return `Error ${status}`
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let body: unknown
    try {
      body = await res.json()
    } catch {
      body = null
    }
    throw new ApiError(res.status, body)
  }
  return res.json() as Promise<T>
}

const jsonHeaders = { 'Content-Type': 'application/json' }

export function fetchIngredients(): Promise<Ingredient[]> {
  return fetch('/api/ingredients').then(handle<Ingredient[]>)
}

export function createIngredient(
  body: Omit<Ingredient, 'id' | 'created_at'>,
): Promise<Ingredient> {
  return fetch('/api/ingredients', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(body),
  }).then(handle<Ingredient>)
}

export function updateIngredient(
  id: number,
  body: Partial<Ingredient>,
): Promise<Ingredient> {
  return fetch(`/api/ingredients/${id}`, {
    method: 'PATCH',
    headers: jsonHeaders,
    body: JSON.stringify(body),
  }).then(handle<Ingredient>)
}

export function deleteIngredient(id: number): Promise<void> {
  return fetch(`/api/ingredients/${id}`, { method: 'DELETE' }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, null)
  })
}

export function cookRecipe(recipe: Recipe): Promise<StockResult> {
  return fetch('/api/recipes/cook', {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(recipe),
  }).then(handle<StockResult>)
}

export interface Faltante {
  nombre: string
  motivo: string
  detalle?: string | null
}

export function faltantesFromError(error: unknown): Faltante[] {
  if (!(error instanceof ApiError) || error.status !== 409) return []
  const body = error.detail as { detail?: { faltantes?: Faltante[] } } | null
  const faltantes = body?.detail?.faltantes
  return Array.isArray(faltantes) ? faltantes : []
}
