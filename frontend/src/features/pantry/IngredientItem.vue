<script setup lang="ts">
import type { Ingredient } from '../../types'
import { categoriaStyle } from '../../lib/categorias'

const props = defineProps<{ ingredient: Ingredient }>()

const emit = defineEmits<{
  edit: [id: number]
  remove: [id: number]
}>()

const style = categoriaStyle(props.ingredient.categoria)
</script>

<template>
  <div
    class="group flex items-center justify-between gap-3 rounded-2xl border border-oat-200 bg-white/80 p-3.5 shadow-sm backdrop-blur transition-all duration-200 hover:-translate-y-0.5 hover:border-basil-200 hover:shadow-md"
  >
    <div class="flex min-w-0 items-center gap-3">
      <span
        class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
        :class="`${style.tag} transition-transform duration-200 group-hover:scale-105`"
        aria-hidden="true"
      >
        <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none">
          <path
            d="M5 8h14v2a7 7 0 0 1-7 7 7 7 0 0 1-7-7V8z"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linejoin="round"
          />
          <path
            d="M8 8a4 4 0 0 1 8 0"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
          />
          <path d="M12 17v3M8.5 20.5h7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
      </span>
      <div class="min-w-0">
        <p class="truncate font-semibold text-ink-900">{{ ingredient.nombre }}</p>
        <p class="text-sm tabular-nums text-ink-500">
          {{ ingredient.cantidad }} {{ ingredient.unidad }}
          <span v-if="ingredient.gramos_por_unidad" class="text-ink-400">
            (≈ {{ ingredient.gramos_por_unidad }} g/unidad)
          </span>
        </p>
      </div>
    </div>
    <div class="flex shrink-0 items-center gap-1.5">
      <span
        :class="style.tag"
        class="hidden rounded-full px-2.5 py-0.5 text-xs font-medium sm:inline-block"
      >
        {{ ingredient.categoria }}
      </span>
      <button
        class="rounded-lg px-2.5 py-1.5 text-sm font-medium text-ink-500 transition hover:bg-basil-50 hover:text-basil-700"
        aria-label="Editar"
        @click="emit('edit', ingredient.id)"
      >
        Editar
      </button>
      <button
        class="rounded-lg px-2.5 py-1.5 text-sm font-medium text-ink-500 transition hover:bg-tomato-50 hover:text-tomato-600"
        aria-label="Eliminar"
        @click="emit('remove', ingredient.id)"
      >
        Eliminar
      </button>
    </div>
  </div>
</template>
