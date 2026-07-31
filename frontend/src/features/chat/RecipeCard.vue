<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { Recipe } from '../../types'
import { usePantryStore } from '../../stores/pantry'
import { useRecipesStore } from '../../stores/recipes'
import { faltantesFromError, type Faltante } from '../../lib/api'

const props = withDefaults(
  defineProps<{
    recipe: Recipe
    imageUrl: string | null
    imagePending: boolean
    showCook?: boolean
    showView?: boolean
  }>(),
  {
    showCook: false,
    showView: true,
  },
)

const router = useRouter()
const store = usePantryStore()
const recipesStore = useRecipesStore()
const cooking = ref(false)
const cooked = ref(false)
const error = ref<string | null>(null)
const faltantes = ref<Faltante[]>([])
const showInstructions = ref(false)

const favorited = computed(() => {
  const hash = props.recipe.hash
  return hash ? (recipesStore.getByHash(hash)?.favorited ?? false) : false
})

function formatAmount(cantidad: number): string {
  return Number.isInteger(cantidad) ? String(cantidad) : String(Math.round(cantidad * 100) / 100)
}

function formatIngredient(ing: { cantidad: number; unidad?: string | null }): string {
  const cantidad = formatAmount(ing.cantidad)
  return ing.unidad ? `${cantidad} ${ing.unidad}` : cantidad
}

const instructionSteps = computed<string[] | null>(() => {
  const raw = props.recipe.instrucciones ?? ''
  const lines = raw
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  if (lines.length === 0) return null
  const numbered = lines.filter((line) => /^\d+[.)]/.test(line)).length
  if (numbered < Math.max(2, Math.ceil(lines.length / 2))) return null
  return lines.map((line) => line.replace(/^\d+[.)]\s*/, ''))
})

onMounted(() => {
  const hash = props.recipe.hash
  if (hash) recipesStore.save(props.recipe, props.imageUrl)
})

watch(
  () => props.imageUrl,
  (url) => {
    const hash = props.recipe.hash
    if (hash) recipesStore.save(props.recipe, url)
  },
)

function goToDetail(): void {
  const hash = props.recipe.hash
  if (!hash) return
  router.push({ name: 'receta-detalle', params: { hash } })
}

function toggleFavorite(): void {
  const hash = props.recipe.hash
  if (hash) recipesStore.toggleFavorite(hash)
}

async function cook(): Promise<void> {
  if (cooking.value || cooked.value) return
  cooking.value = true
  error.value = null
  faltantes.value = []
  try {
    const result = await store.cook({ ...props.recipe })
    if (result.ok) {
      cooked.value = true
      const hash = props.recipe.hash
      if (hash) recipesStore.markCooked(hash)
    }
  } catch (e) {
    const missing = faltantesFromError(e)
    if (missing.length > 0) faltantes.value = missing
    else error.value = e instanceof Error ? e.message : 'No se pudo cocinar'
  } finally {
    cooking.value = false
  }
}
</script>

<template>
  <div
    data-test="card"
    class="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm transition hover:border-stone-300"
    @click="goToDetail"
  >
    <div class="relative aspect-[16/9] w-full bg-stone-100">
      <div
        v-if="imagePending && !imageUrl"
        class="absolute inset-0 flex items-center justify-center gap-2 text-stone-400"
      >
        <span
          class="h-6 w-6 animate-spin rounded-full border-2 border-amber-500 border-t-transparent"
        />
        <span class="text-sm">Generando imagen…</span>
      </div>
      <div
        v-else-if="imageUrl"
        class="absolute inset-0 flex items-center justify-center"
      >
        <img
          :src="imageUrl"
          :alt="`Imagen de ${recipe.nombre}`"
          class="h-full w-full object-cover"
        />
      </div>
      <div v-else class="absolute inset-0 flex items-center justify-center">
        <span class="text-4xl">&#127858;</span>
      </div>
    </div>

    <div class="p-4">
      <div class="flex items-start justify-between gap-2">
        <div>
          <h3 class="text-lg font-bold">{{ recipe.nombre }}</h3>
          <p v-if="recipe.tiempo_minutos" class="text-sm text-stone-500">
            ~{{ recipe.tiempo_minutos }} min
          </p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <span
            class="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800"
          >
            {{ recipe.ingredientes.length }} ingredientes
          </span>
          <button
            data-test="favorite"
            :aria-label="favorited ? 'Quitar de favoritas' : 'Marcar como favorita'"
            class="rounded-full p-1.5 transition hover:bg-stone-100"
            @click.stop="toggleFavorite"
          >
            <svg
              :class="favorited ? 'text-red-500' : 'text-stone-300 hover:text-red-400'"
              class="h-5 w-5 transition"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path
                d="M12 21s-7.5-4.7-10-9C.6 8.6 2.3 5 5.6 5c2 0 3.2 1.1 4.4 3 1.2-1.9 2.4-3 4.4-3 3.3 0 5 3.6 3.6 7-2.5 4.3-10 9-10 9z"
              />
            </svg>
          </button>
        </div>
      </div>

      <p v-if="recipe.resumen" class="mt-1 text-sm text-stone-600">
        {{ recipe.resumen }}
      </p>

      <ul class="mt-3 space-y-1">
        <li
          v-for="ing in recipe.ingredientes"
          :key="ing.nombre"
          class="flex justify-between gap-3 rounded-lg bg-stone-50 px-2 py-1 text-sm"
        >
          <span>{{ ing.nombre }}</span>
          <span class="shrink-0 font-medium text-stone-700">
            {{ formatIngredient(ing) }}
          </span>
        </li>
      </ul>

      <div v-if="recipe.instrucciones" class="mt-3">
        <button
          data-test="toggle-instructions"
          class="text-sm font-medium text-amber-700 hover:text-amber-800"
          @click.stop="showInstructions = !showInstructions"
        >
          {{ showInstructions ? 'Ocultar instrucciones' : 'Ver instrucciones' }}
        </button>
        <ol
          v-if="showInstructions && instructionSteps"
          class="mt-2 list-decimal space-y-1 pl-5 text-sm text-stone-600"
        >
          <li v-for="(step, index) in instructionSteps" :key="index">{{ step }}</li>
        </ol>
        <p v-else-if="showInstructions" class="mt-2 whitespace-pre-wrap text-sm text-stone-600">
          {{ recipe.instrucciones }}
        </p>
      </div>

      <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>
      <div
        v-if="faltantes.length > 0"
        class="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700"
      >
        <p class="font-medium">No hay suficiente stock:</p>
        <ul class="mt-1 list-disc pl-5">
          <li v-for="f in faltantes" :key="f.nombre">
            {{ f.nombre }} — {{ f.motivo
            }}{{ f.detalle ? ` (${f.detalle})` : '' }}
          </li>
        </ul>
      </div>

      <button
        v-if="showView && !showCook"
        data-test="view"
        class="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-amber-600 px-4 py-2.5 font-medium text-white transition hover:bg-amber-700"
        @click.stop="goToDetail"
      >
        Ver receta
      </button>
      <button
        v-else-if="showCook"
        data-test="cook"
        :disabled="cooking || cooked"
        class="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-amber-600 px-4 py-2.5 font-medium text-white transition hover:bg-amber-700 disabled:opacity-60"
        @click.stop="cook"
      >
        <span
          v-if="cooking"
          class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
        />
        <span v-if="cooking">Cocinando…</span>
        <span v-else-if="cooked">¡Cocinada!</span>
        <span v-else>Cocinar receta</span>
      </button>
    </div>
  </div>
</template>
