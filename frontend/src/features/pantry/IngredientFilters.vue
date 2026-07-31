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
    <div class="relative flex-1">
      <svg
        viewBox="0 0 20 20"
        class="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400"
        fill="none"
        aria-hidden="true"
      >
        <circle
          cx="8.5"
          cy="8.5"
          r="5.5"
          stroke="currentColor"
          stroke-width="1.6"
        />
        <path
          d="m13 13 4 4"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
        />
      </svg>
      <input
        v-model="search"
        type="search"
        placeholder="Buscar ingrediente…"
        class="w-full rounded-full border border-oat-200 bg-white/80 py-2.5 pl-10 pr-4 text-sm shadow-sm transition focus:border-basil-500 focus:outline-none focus:ring-4 focus:ring-basil-100"
      />
    </div>
    <select
      v-model="categoria"
      class="rounded-full border border-oat-200 bg-white/80 px-4 py-2.5 text-sm shadow-sm transition focus:border-basil-500 focus:outline-none focus:ring-4 focus:ring-basil-100"
    >
      <option value="">Todas las categorías</option>
      <option v-for="c in categorias" :key="c" :value="c">{{ c }}</option>
    </select>
  </div>
</template>
