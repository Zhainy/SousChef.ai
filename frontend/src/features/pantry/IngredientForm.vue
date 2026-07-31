<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { Ingredient } from '../../types'

const props = defineProps<{ initial: Ingredient | null }>()
const emit = defineEmits<{
  saved: [payload: Omit<Ingredient, 'id' | 'created_at'>]
  cancelled: []
}>()

const UNIDADES = [
  'g',
  'kg',
  'ml',
  'l',
  'piezas',
  'unidades',
  'cucharadas',
  'cucharaditas',
  'pizca',
  'al gusto',
]

const CATEGORIAS = [
  'proteínas',
  'verduras',
  'frutas',
  'lácteos',
  'granos',
  'especias',
  'otros',
]

const form = reactive({
  nombre: '',
  cantidad: 1,
  unidad: 'piezas',
  categoria: 'otros',
})

const error = ref<string | null>(null)

watch(
  () => props.initial,
  (init) => {
    if (init) {
      form.nombre = init.nombre
      form.cantidad = init.cantidad
      form.unidad = init.unidad
      form.categoria = init.categoria
    } else {
      form.nombre = ''
      form.cantidad = 1
      form.unidad = 'piezas'
      form.categoria = 'otros'
    }
    error.value = null
  },
  { immediate: true },
)

function submit(): void {
  if (!form.nombre.trim()) {
    error.value = 'El nombre es obligatorio'
    return
  }
  if (!form.cantidad || form.cantidad <= 0) {
    error.value = 'La cantidad debe ser mayor a 0'
    return
  }
  error.value = null
  emit('saved', {
    nombre: form.nombre.trim(),
    cantidad: Number(form.cantidad),
    unidad: form.unidad,
    categoria: form.categoria,
  })
}
</script>

<template>
  <form
    class="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm"
    @submit.prevent="submit"
  >
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <label class="sm:col-span-2">
        <span class="text-sm font-medium text-stone-700">Nombre</span>
        <input
          v-model.trim="form.nombre"
          type="text"
          placeholder="Ej: pechuga de pollo"
          class="mt-1 w-full rounded-xl border border-stone-300 px-3 py-2 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
        />
      </label>
      <label>
        <span class="text-sm font-medium text-stone-700">Cantidad</span>
        <input
          v-model.number="form.cantidad"
          type="number"
          min="0.01"
          step="0.01"
          class="mt-1 w-full rounded-xl border border-stone-300 px-3 py-2 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
        />
      </label>
      <label>
        <span class="text-sm font-medium text-stone-700">Unidad</span>
        <select
          v-model="form.unidad"
          class="mt-1 w-full rounded-xl border border-stone-300 bg-white px-3 py-2 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
        >
          <option v-for="u in UNIDADES" :key="u" :value="u">{{ u }}</option>
        </select>
      </label>
      <label class="sm:col-span-2">
        <span class="text-sm font-medium text-stone-700">Categoría</span>
        <select
          v-model="form.categoria"
          class="mt-1 w-full rounded-xl border border-stone-300 bg-white px-3 py-2 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
        >
          <option v-for="c in CATEGORIAS" :key="c" :value="c">{{ c }}</option>
        </select>
      </label>
    </div>
    <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>
    <div class="mt-4 flex justify-end gap-2">
      <button
        type="button"
        class="rounded-xl px-4 py-2 text-sm font-medium text-stone-600 hover:bg-stone-100"
        @click="emit('cancelled')"
      >
        Cancelar
      </button>
      <button
        type="submit"
        class="rounded-xl bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
      >
        {{ initial ? 'Guardar cambios' : 'Agregar' }}
      </button>
    </div>
  </form>
</template>
