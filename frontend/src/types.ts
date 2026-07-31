export interface Ingredient {
  id: number
  nombre: string
  cantidad: number
  unidad: string
  categoria: string
  created_at?: string
}

export interface RecipeIngredient {
  nombre: string
  cantidad: number
}

export interface Recipe {
  nombre: string
  resumen?: string | null
  tiempo_minutos?: number | null
  ingredientes: RecipeIngredient[]
  instrucciones?: string | null
  hash?: string | null
  image_url?: string | null
}

export interface StockResult {
  ok: boolean
  descontados: { nombre: string; cantidad: number; unidad: string }[]
  faltantes: { nombre: string; pedido: number; disponible: number; motivo: string }[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}
