<script setup lang="ts">
import type { Ingredient } from '../../types'

defineProps<{ ingredient: Ingredient }>()

const emit = defineEmits<{
  edit: [id: number]
  remove: [id: number]
}>()
</script>

<template>
  <div
    class="flex items-center justify-between gap-3 rounded-xl border border-stone-200 bg-white p-3 shadow-sm"
  >
    <div class="min-w-0">
      <p class="truncate font-medium">{{ ingredient.nombre }}</p>
      <p class="text-sm text-stone-500">
        {{ ingredient.cantidad }} {{ ingredient.unidad }}
      </p>
    </div>
    <div class="flex shrink-0 items-center gap-2">
      <span
        class="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800"
      >
        {{ ingredient.categoria }}
      </span>
      <button
        class="rounded-lg px-2 py-1 text-sm text-stone-600 hover:bg-stone-100"
        aria-label="Editar"
        @click="emit('edit', ingredient.id)"
      >
        Editar
      </button>
      <button
        class="rounded-lg px-2 py-1 text-sm text-red-600 hover:bg-red-50"
        aria-label="Eliminar"
        @click="emit('remove', ingredient.id)"
      >
        Eliminar
      </button>
    </div>
  </div>
</template>
