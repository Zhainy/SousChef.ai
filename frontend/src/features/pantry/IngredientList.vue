<script setup lang="ts">
import { computed } from 'vue'
import type { Ingredient } from '../../types'
import { categoriaStyle } from '../../lib/categorias'
import IngredientItem from './IngredientItem.vue'

const props = defineProps<{ items: Ingredient[] }>()

const emit = defineEmits<{
  edit: [id: number]
  remove: [id: number]
}>()

const groups = computed(() => {
  const map = new Map<string, Ingredient[]>()
  for (const item of props.items) {
    const list = map.get(item.categoria) ?? []
    list.push(item)
    map.set(item.categoria, list)
  }
  return [...map.entries()]
})

function onEnter(el: Element): void {
  const index = Number((el as HTMLElement).dataset.index ?? 0)
  ;(el as HTMLElement).style.transitionDelay = `${index * 35}ms`
}

function onLeave(el: Element): void {
  ;(el as HTMLElement).style.transitionDelay = '0ms'
}
</script>

<template>
  <div
    v-if="items.length === 0"
    class="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-oat-300 bg-oat-50/50 p-10 text-center"
  >
    <span
      class="flex h-12 w-12 items-center justify-center rounded-full bg-basil-100 text-basil-600"
      aria-hidden="true"
    >
      <svg viewBox="0 0 24 24" class="h-6 w-6" fill="none">
        <path
          d="M5 8h14v2a7 7 0 0 1-7 7 7 7 0 0 1-7-7V8z"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linejoin="round"
        />
        <path d="M8 8a4 4 0 0 1 8 0" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        <path d="M12 17v3M8.5 20.5h7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
      </svg>
    </span>
    <p class="font-medium text-ink-700">No hay ingredientes que coincidan</p>
    <p class="text-sm text-ink-500">
      Prueba con otra búsqueda o categoría.
    </p>
  </div>

  <div v-for="[categoria, list] in groups" :key="categoria" class="space-y-2">
    <h3
      class="mt-6 mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-ink-500"
    >
      <span
        :class="categoriaStyle(categoria).dot"
        class="h-2 w-2 rounded-full"
      />
      {{ categoria }}
      <span class="text-ink-400/70">{{ list.length }}</span>
    </h3>
    <TransitionGroup
      name="pantry-item"
      tag="div"
      class="space-y-2"
      appear
      @enter="onEnter"
      @leave="onLeave"
    >
      <IngredientItem
        v-for="(item, index) in list"
        :key="item.id"
        :data-index="index"
        :ingredient="item"
        @edit="emit('edit', $event)"
        @remove="emit('remove', $event)"
      />
    </TransitionGroup>
  </div>
</template>

<style scoped>
.pantry-item-enter-active {
  transition:
    opacity 0.35s ease,
    transform 0.35s cubic-bezier(0.34, 1.3, 0.64, 1);
}
.pantry-item-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.pantry-item-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}
.pantry-item-leave-to {
  opacity: 0;
  transform: scale(0.98);
}
.pantry-item-move {
  transition: transform 0.35s ease;
}
</style>
