<script setup lang="ts">
import { ref, watch } from 'vue'

defineProps<{ categorias: string[] }>()

const emit = defineEmits<{
  change: [filters: { search: string; categoria: string }]
}>()

const search = ref('')
const categoria = ref('')

watch([search, categoria], () => {
  emit('change', { search: search.value, categoria: categoria.value })
})
</script>

<template>
  <div class="flex flex-col gap-2 sm:flex-row">
    <input
      v-model="search"
      type="search"
      placeholder="Buscar ingrediente…"
      class="flex-1 rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
    />
    <select
      v-model="categoria"
      class="rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
    >
      <option value="">Todas las categorías</option>
      <option v-for="c in categorias" :key="c" :value="c">{{ c }}</option>
    </select>
  </div>
</template>
