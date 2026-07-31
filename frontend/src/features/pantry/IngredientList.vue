<script setup lang="ts">
import { computed } from 'vue'
import type { Ingredient } from '../../types'
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
</script>

<template>
  <div
    v-if="items.length === 0"
    class="rounded-xl border border-dashed border-stone-300 p-8 text-center text-stone-500"
  >
    No hay ingredientes que coincidan.
  </div>
  <div v-for="[categoria, list] in groups" :key="categoria">
    <h3
      class="mt-4 mb-2 text-xs font-semibold uppercase tracking-wider text-stone-400"
    >
      {{ categoria }}
    </h3>
    <div class="space-y-2">
      <IngredientItem
        v-for="item in list"
        :key="item.id"
        :ingredient="item"
        @edit="emit('edit', $event)"
        @remove="emit('remove', $event)"
      />
    </div>
  </div>
</template>
