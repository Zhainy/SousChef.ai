<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { usePantryStore } from '../../stores/pantry'
import { useToastsStore } from '../../stores/toasts'
import type { Ingredient } from '../../types'
import AppModal from '../../components/AppModal.vue'
import IngredientFilters from './IngredientFilters.vue'
import IngredientForm from './IngredientForm.vue'
import IngredientList from './IngredientList.vue'

const store = usePantryStore()
const toasts = useToastsStore()
const showForm = ref(false)
const editing = ref<Ingredient | null>(null)
const confirming = ref<Ingredient | null>(null)
const deleting = ref(false)
const filters = ref({ search: '', categoria: '' })

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

function closeForm(): void {
  showForm.value = false
  editing.value = null
}

async function onSaved(
  payload: Omit<Ingredient, 'id' | 'created_at'>,
): Promise<void> {
  try {
    if (editing.value) {
      await store.update(editing.value.id, payload)
      toasts.notify('Ingrediente actualizado', 'success')
    } else {
      await store.create(payload)
      toasts.notify('Ingrediente agregado', 'success')
    }
    closeForm()
  } catch (e) {
    toasts.notify(e instanceof Error ? e.message : 'Error al guardar', 'error')
  }
}

function askRemove(id: number): void {
  confirming.value = store.items.find((i) => i.id === id) ?? null
}

async function confirmRemove(): Promise<void> {
  if (!confirming.value) return
  deleting.value = true
  try {
    await store.remove(confirming.value.id)
    toasts.notify('Ingrediente eliminado', 'error')
    confirming.value = null
  } catch (e) {
    toasts.notify(e instanceof Error ? e.message : 'Error al eliminar', 'error')
  } finally {
    deleting.value = false
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

    <IngredientFilters
      :categorias="store.categorias"
      @change="(f) => (filters = f)"
    />

    <IngredientList
      :items="filtered"
      @edit="openEdit"
      @remove="askRemove"
    />

    <AppModal
      v-if="showForm"
      :title="editing ? 'Editar ingrediente' : 'Agregar ingrediente'"
      @close="closeForm"
    >
      <IngredientForm
        :initial="editing"
        @saved="onSaved"
        @cancelled="closeForm"
      />
    </AppModal>

    <AppModal
      v-if="confirming"
      title="Eliminar ingrediente"
      @close="confirming = null"
    >
      <p class="text-stone-700">
        ¿Eliminar "{{ confirming.nombre }}" de la despensa?
      </p>
      <div class="mt-5 flex justify-end gap-2">
        <button
          class="rounded-xl px-4 py-2 text-sm font-medium text-stone-600 transition hover:bg-stone-100"
          @click="confirming = null"
        >
          Cancelar
        </button>
        <button
          :disabled="deleting"
          class="flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-60"
          @click="confirmRemove"
        >
          <span
            v-if="deleting"
            class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
          />
          {{ deleting ? 'Eliminando…' : 'Eliminar' }}
        </button>
      </div>
    </AppModal>
  </div>
</template>
