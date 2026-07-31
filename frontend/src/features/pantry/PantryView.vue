<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { usePantryStore } from '../../stores/pantry'
import type { Ingredient } from '../../types'
import IngredientFilters from './IngredientFilters.vue'
import IngredientForm from './IngredientForm.vue'
import IngredientList from './IngredientList.vue'

const store = usePantryStore()
const showForm = ref(false)
const editing = ref<Ingredient | null>(null)
const filters = ref({ search: '', categoria: '' })
const actionError = ref<string | null>(null)

const filtered = computed(() => {
  const q = filters.value.search.trim().toLowerCase()
  return store.items.filter((item) => {
    const matchesSearch = !q || item.nombre.toLowerCase().includes(q)
    const matchesCategoria =
      !filters.value.categoria || item.categoria === filters.value.categoria
    return matchesSearch && matchesCategoria
  })
})

onMounted(() => store.load())

function openCreate(): void {
  editing.value = null
  showForm.value = true
}

function openEdit(id: number): void {
  editing.value = store.items.find((i) => i.id === id) ?? null
  showForm.value = true
}

async function onSaved(
  payload: Omit<Ingredient, 'id' | 'created_at'>,
): Promise<void> {
  actionError.value = null
  try {
    if (editing.value) await store.update(editing.value.id, payload)
    else await store.create(payload)
    showForm.value = false
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : 'Error al guardar'
  }
}

async function onRemove(id: number): Promise<void> {
  if (!window.confirm('¿Eliminar este ingrediente de la despensa?')) return
  actionError.value = null
  try {
    await store.remove(id)
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : 'Error al eliminar'
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">Despensa</h1>
        <p class="text-sm text-stone-500">
          {{ store.items.length }} ingredientes registrados
        </p>
      </div>
      <button
        class="rounded-xl bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
        @click="openCreate"
      >
        + Agregar ingrediente
      </button>
    </div>

    <p v-if="store.loading" class="text-sm text-stone-500">Cargando…</p>
    <p v-if="store.error" class="text-sm text-red-600">{{ store.error }}</p>
    <p v-if="actionError" class="text-sm text-red-600">{{ actionError }}</p>

    <IngredientFilters
      :categorias="store.categorias"
      @change="(f) => (filters = f)"
    />

    <IngredientForm
      v-if="showForm"
      :initial="editing"
      @saved="onSaved"
      @cancelled="showForm = false"
    />

    <IngredientList
      :items="filtered"
      @edit="openEdit"
      @remove="onRemove"
    />
  </div>
</template>
