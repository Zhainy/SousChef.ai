export interface Ingredient {
  id: number
  nombre: string
  cantidad: number
  unidad: string
  categoria: string
  gramos_por_unidad?: number | null
  created_at?: string
}

export interface RecipeIngredient {
  nombre: string
  cantidad: number
  unidad?: string | null
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
  faltantes: {
    nombre: string
    pedido: number
    disponible: number
    unidad?: string | null
    gramos_por_unidad?: number | null
    motivo: string
    detalle?: string | null
  }[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface SavedRecipe {
  hash: string
  recipe: Recipe
  imageUrl: string | null
  favorited: boolean
  createdAt: string
  cookedAt: string | null
}
