<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
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
  'latas',
  'lata',
  'sobres',
  'bolsas',
  'paquete',
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
  gramos_por_unidad: null as number | null,
})

const error = ref<string | null>(null)

const PESO_POR_UNIDAD = new Set([
  'piezas',
  'unidades',
  'latas',
  'lata',
  'sobres',
  'bolsas',
  'paquete',
])

const mostrarPesoPorUnidad = computed(() => PESO_POR_UNIDAD.has(form.unidad))

watch(
  () => props.initial,
  (init) => {
    if (init) {
      form.nombre = init.nombre
      form.cantidad = init.cantidad
      form.unidad = init.unidad
      form.categoria = init.categoria
      form.gramos_por_unidad = init.gramos_por_unidad ?? null
    } else {
      form.nombre = ''
      form.cantidad = 1
      form.unidad = 'piezas'
      form.categoria = 'otros'
      form.gramos_por_unidad = null
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
    gramos_por_unidad: form.gramos_por_unidad,
  })
}
</script>

<template>
  <form class="space-y-4" @submit.prevent="submit">
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <label class="sm:col-span-2">
        <span class="text-sm font-medium text-ink-700">Nombre</span>
        <input
          v-model.trim="form.nombre"
          type="text"
          placeholder="Ej: pechuga de pollo"
          class="input-field mt-1"
        />
      </label>
      <label>
        <span class="text-sm font-medium text-ink-700">Cantidad</span>
        <input
          v-model.number="form.cantidad"
          type="number"
          min="0.01"
          step="0.01"
          class="input-field mt-1"
        />
      </label>
      <label>
        <span class="text-sm font-medium text-ink-700">Unidad</span>
        <select
          v-model="form.unidad"
          class="input-field mt-1"
        >
          <option v-for="u in UNIDADES" :key="u" :value="u">{{ u }}</option>
        </select>
      </label>
      <label v-if="mostrarPesoPorUnidad">
        <span class="text-sm font-medium text-ink-700">Gramos por unidad</span>
        <input
          v-model.number="form.gramos_por_unidad"
          type="number"
          min="0.01"
          step="0.01"
          placeholder="Ej: 140"
          class="input-field mt-1"
        />
        <span class="mt-1 block text-xs text-ink-400">
          Peso de cada unidad para calcular stock en gramos
        </span>
      </label>
      <label class="sm:col-span-2">
        <span class="text-sm font-medium text-ink-700">Categoría</span>
        <select
          v-model="form.categoria"
          class="input-field mt-1"
        >
          <option v-for="c in CATEGORIAS" :key="c" :value="c">{{ c }}</option>
        </select>
      </label>
    </div>
    <p v-if="error" class="mt-3 text-sm text-tomato-600">{{ error }}</p>
    <div class="mt-4 flex justify-end gap-2">
      <button
        type="button"
        class="rounded-full px-4 py-2 text-sm font-medium text-ink-500 transition hover:bg-oat-100 hover:text-ink-700"
        @click="emit('cancelled')"
      >
        Cancelar
      </button>
      <button
        type="submit"
        class="rounded-full bg-basil-800 px-5 py-2 text-sm font-semibold text-oat-50 shadow-md shadow-basil-900/20 transition hover:-translate-y-0.5 hover:bg-basil-700"
      >
        {{ initial ? 'Guardar cambios' : 'Agregar' }}
      </button>
    </div>
  </form>
</template>
