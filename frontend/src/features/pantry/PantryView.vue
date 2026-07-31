<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { usePantryStore } from '../../stores/pantry'
import { useToastsStore } from '../../stores/toasts'
import type { Ingredient } from '../../types'
import AppModal from '../../components/AppModal.vue'
import AppLoader from '../../components/ui/AppLoader.vue'
import IngredientFilters from './IngredientFilters.vue'
import IngredientForm from './IngredientForm.vue'
import IngredientList from './IngredientList.vue'
import SkeletonPantry from './SkeletonPantry.vue'

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
  <div class="space-y-5">
    <div class="flex items-end justify-between gap-4">
      <div>
        <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-basil-600">
          <span class="h-px w-6 bg-saffron-500" />
          Tu despensa
        </p>
        <h1 class="font-display mt-1 text-3xl font-semibold text-basil-950 sm:text-4xl">
          Inventario
        </h1>
        <p class="mt-1 text-sm text-ink-500">
          {{ store.items.length }}
          {{ store.items.length === 1 ? 'ingrediente' : 'ingredientes' }} registrados
        </p>
      </div>
      <button
        class="flex shrink-0 items-center gap-1.5 rounded-full bg-basil-800 px-5 py-2.5 text-sm font-semibold text-oat-50 shadow-lg shadow-basil-900/20 transition-all duration-200 hover:-translate-y-0.5 hover:bg-basil-700 hover:shadow-xl hover:shadow-basil-900/25 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-saffron-500"
        @click="openCreate"
      >
        + Agregar ingrediente
      </button>
    </div>

    <SkeletonPantry v-if="store.loading" />
    <p v-else-if="store.error" class="text-sm text-tomato-600">{{ store.error }}</p>

    <template v-else>
      <IngredientFilters
        :categorias="store.categorias"
        @change="(f) => (filters = f)"
      />

      <IngredientList
        :items="filtered"
        @edit="openEdit"
        @remove="askRemove"
      />
    </template>

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
      <p class="text-ink-700">
        ¿Eliminar
        <span class="font-semibold text-tomato-700">"{{ confirming.nombre }}"</span>
        de la despensa?
      </p>
      <div class="mt-5 flex justify-end gap-2">
        <button
          class="rounded-full px-4 py-2 text-sm font-medium text-ink-500 transition hover:bg-oat-100 hover:text-ink-700"
          @click="confirming = null"
        >
          Cancelar
        </button>
        <button
          :disabled="deleting"
          class="flex min-w-32 items-center justify-center gap-2 rounded-full bg-tomato-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-tomato-700 disabled:opacity-60"
          @click="confirmRemove"
        >
          <AppLoader
            v-if="deleting"
            size="sm"
            tone="light"
            :role="null"
          />
          {{ deleting ? 'Eliminando…' : 'Eliminar' }}
        </button>
      </div>
    </AppModal>
  </div>
</template>
