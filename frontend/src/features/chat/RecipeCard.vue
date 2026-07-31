<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { Recipe } from '../../types'
import { usePantryStore } from '../../stores/pantry'
import { useRecipesStore } from '../../stores/recipes'
import { useToastsStore } from '../../stores/toasts'
import { ApiError, faltantesFromError, type Faltante } from '../../lib/api'
import AppLoader from '../../components/ui/AppLoader.vue'
import MarkdownText from '../../components/MarkdownText.vue'

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

const emit = defineEmits<{ discard: [hash: string] }>()

const router = useRouter()
const store = usePantryStore()
const recipesStore = useRecipesStore()
const toasts = useToastsStore()
const cooking = ref(false)
const cooked = ref(false)
const discarded = ref(false)
const error = ref<string | null>(null)
const faltantes = ref<Faltante[]>([])
const showInstructions = ref(false)
const heartPop = ref(0)

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
  if (hash) {
    recipesStore.toggleFavorite(hash)
    heartPop.value++
  }
}

function discard(): void {
  const hash = props.recipe.hash
  if (!hash || discarded.value) return
  const entry = recipesStore.remove(hash)
  discarded.value = true
  emit('discard', hash)
  if (entry) {
    toasts.notify('Receta descartada', 'info', 6000, {
      label: 'Deshacer',
      onClick: () => {
        discarded.value = false
        recipesStore.restore(entry)
      },
    })
  }
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
    else if (e instanceof ApiError && e.status === 422)
      error.value = 'La receta tiene datos inválidos. Inténtalo de nuevo.'
    else
      error.value = e instanceof Error ? e.message : 'No se pudo cocinar'
  } finally {
    cooking.value = false
  }
}
</script>

<template>
  <div
    v-show="!discarded"
    data-test="card"
    class="group overflow-hidden rounded-2xl border border-oat-200 bg-white shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-basil-200 hover:shadow-xl hover:shadow-basil-900/10"
    @click="goToDetail"
  >
    <div class="relative aspect-[16/9] w-full overflow-hidden bg-basil-50">
      <div
        v-if="imagePending && !imageUrl"
        class="skeleton absolute inset-0 flex items-center justify-center rounded-none"
      >
        <AppLoader size="lg" tone="saffron" label="Generando imagen…" />
      </div>
      <Transition name="imgfade" appear>
        <img
          v-if="imageUrl"
          :src="imageUrl"
          :alt="`Imagen de ${recipe.nombre}`"
          class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
      </Transition>
      <div
        v-if="!imagePending && !imageUrl"
        class="absolute inset-0 flex items-center justify-center"
      >
        <svg
          viewBox="0 0 32 32"
          class="h-10 w-10 text-basil-300 transition-transform duration-300 group-hover:scale-110"
          fill="none"
          aria-hidden="true"
        >
          <path d="M6 10h20v2H6z" fill="currentColor" opacity=".85" />
          <path d="M6 12h20c0 5-1.5 8-10 8S6 17 6 12z" fill="currentColor" />
          <path
            d="M12 5c0-1.5 1-2 1-3.5M18 5c0-1.5 1-2 1-3.5"
            stroke="#e8a33d"
            stroke-width="2"
            stroke-linecap="round"
          />
        </svg>
      </div>

      <span
        v-if="recipe.tiempo_minutos"
        class="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-basil-950/85 px-2.5 py-1 text-xs font-medium text-oat-50 backdrop-blur"
      >
        <svg viewBox="0 0 20 20" class="h-3.5 w-3.5 text-saffron-400" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.6" />
          <path d="M10 6v4l3 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
        </svg>
        ~{{ recipe.tiempo_minutos }} min
      </span>
    </div>

    <div class="p-4">
      <div class="flex items-start justify-between gap-2">
        <div class="min-w-0">
          <h3 class="font-display text-lg font-bold leading-snug text-basil-700">
            {{ recipe.nombre }}
          </h3>
        </div>
        <div class="flex shrink-0 items-center gap-1.5">
          <span
            class="rounded-full bg-basil-100 px-2.5 py-0.5 text-xs font-semibold text-basil-700"
          >
            {{ recipe.ingredientes.length }}
            {{ recipe.ingredientes.length === 1 ? 'ingrediente' : 'ingredientes' }}
          </span>
          <button
            data-test="favorite"
            :aria-label="favorited ? 'Quitar de favoritas' : 'Marcar como favorita'"
            class="rounded-full p-1.5 transition hover:bg-tomato-50"
            @click.stop="toggleFavorite"
          >
            <svg
              :key="heartPop"
              :class="favorited ? 'animate-pop text-tomato-500' : 'text-ink-400 hover:text-tomato-500'"
              class="h-5 w-5 transition-colors"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path
                d="M12 21s-7.5-4.7-10-9C.6 8.6 2.3 5 5.6 5c2 0 3.2 1.1 4.4 3 1.2-1.9 2.4-3 4.4-3 3.3 0 5 3.6 3.6 7-2.5 4.3-10 9-10 9z"
              />
            </svg>
          </button>
          <button
            data-test="discard"
            :aria-label="`Descartar ${recipe.nombre}`"
            class="rounded-full p-1.5 transition hover:bg-tomato-50"
            @click.stop="discard"
          >
            <svg
              viewBox="0 0 24 24"
              class="h-5 w-5 text-ink-400 transition-colors hover:text-tomato-600"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M4 6.5h16M9.5 6.5V4.8A.8.8 0 0 1 10.3 4h3.4a.8.8 0 0 1 .8.8v1.7m3.8 0-.7 12a1.6 1.6 0 0 1-1.6 1.5H8a1.6 1.6 0 0 1-1.6-1.5l-.7-12"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <path d="M10.5 10.5v6M13.5 10.5v6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
            </svg>
          </button>
        </div>
      </div>

      <p v-if="recipe.resumen" class="mt-1 text-sm leading-relaxed text-ink-500">
        {{ recipe.resumen }}
      </p>

      <ul class="mt-3 space-y-1">
        <li
          v-for="ing in recipe.ingredientes"
          :key="ing.nombre"
          class="flex justify-between gap-3 rounded-lg bg-oat-100/70 px-2.5 py-1.5 text-sm"
        >
          <span class="min-w-0 truncate text-ink-700">{{ ing.nombre }}</span>
          <span class="shrink-0 font-medium tabular-nums text-ink-900">
            {{ formatIngredient(ing) }}
          </span>
        </li>
      </ul>

      <div v-if="recipe.instrucciones" class="mt-3">
        <button
          data-test="toggle-instructions"
          class="text-sm font-semibold text-basil-700 transition hover:text-basil-800"
          @click.stop="showInstructions = !showInstructions"
        >
          <span class="flex items-center gap-1.5">
            <svg
              :class="showInstructions && 'rotate-180'"
              viewBox="0 0 16 16"
              class="h-3.5 w-3.5 transition-transform duration-200"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M3 6l5 5 5-5"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            {{ showInstructions ? 'Ocultar instrucciones' : 'Ver instrucciones' }}
          </span>
        </button>
        <Transition name="inst">
          <ol
            v-if="showInstructions && instructionSteps"
            class="mt-2 list-decimal space-y-1.5 pl-5 text-sm leading-relaxed text-ink-700"
          >
            <li v-for="(step, index) in instructionSteps" :key="index">{{ step }}</li>
          </ol>
          <MarkdownText
            v-else-if="showInstructions"
            :text="recipe.instrucciones"
            class="mt-2 text-sm leading-relaxed text-ink-700"
          />
        </Transition>
      </div>

      <p v-if="error" class="mt-3 text-sm text-tomato-600">{{ error }}</p>
      <div
        v-if="faltantes.length > 0"
        class="mt-3 rounded-xl border border-tomato-100 bg-tomato-50 p-3 text-sm text-tomato-700"
      >
        <p class="font-semibold">No hay suficiente stock:</p>
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
        class="mt-4 flex w-full items-center justify-center gap-2 rounded-full bg-basil-800 px-4 py-2.5 font-semibold text-oat-50 shadow-md shadow-basil-900/20 transition-all duration-200 hover:-translate-y-0.5 hover:bg-basil-700 hover:shadow-lg"
        @click.stop="goToDetail"
      >
        Ver receta
        <svg viewBox="0 0 16 16" class="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5" fill="none" aria-hidden="true">
          <path
            d="M3 8h10m0 0L9 4m4 4-4 4"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
      <button
        v-else-if="showCook"
        data-test="cook"
        :disabled="cooking || cooked"
        class="mt-4 flex w-full items-center justify-center gap-2 rounded-full bg-gradient-to-r from-saffron-500 to-saffron-600 px-4 py-2.5 font-semibold text-white shadow-md shadow-saffron-600/30 transition-all duration-200 hover:-translate-y-0.5 hover:from-saffron-400 hover:to-saffron-500 hover:shadow-lg disabled:translate-y-0 disabled:opacity-60"
        @click.stop="cook"
      >
        <AppLoader
          v-if="cooking"
          size="sm"
          tone="light"
          :role="null"
        />
        <span v-if="cooking">Cocinando…</span>
        <span v-else-if="cooked" class="animate-pop">¡Cocinada!</span>
        <span v-else class="flex items-center gap-2">
          <svg viewBox="0 0 32 32" class="h-4 w-4" fill="none" aria-hidden="true">
            <path d="M6 10h20v2H6z" fill="currentColor" opacity=".85" />
            <path d="M6 12h20c0 5-1.5 8-10 8S6 17 6 12z" fill="currentColor" />
          </svg>
          Cocinar receta
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.imgfade-enter-active {
  transition: opacity 0.4s ease;
}
.imgfade-enter-from {
  opacity: 0;
}
.inst-enter-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}
.inst-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
