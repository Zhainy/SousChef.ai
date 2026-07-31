<script setup lang="ts">
import { ref } from 'vue'
import { useRecipesStore } from '../../stores/recipes'
import RecipeCard from '../chat/RecipeCard.vue'

type Tab = 'dia' | 'generadas' | 'favoritas'

const store = useRecipesStore()
const activeTab = ref<Tab>('dia')

const tabs: { id: Tab; label: string }[] = [
  { id: 'dia', label: 'Receta del día' },
  { id: 'generadas', label: 'Generadas hoy' },
  { id: 'favoritas', label: 'Favoritas' },
]
</script>

<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-2xl font-bold">Recetas</h1>
      <p class="text-sm text-stone-500">Tus recetas generadas en el chat</p>
    </div>

    <div class="flex gap-1 rounded-full bg-stone-100 p-1">
      <button
        v-for="t in tabs"
        :key="t.id"
        data-test="tab"
        :class="[
          'rounded-full px-4 py-1.5 text-sm font-medium transition',
          activeTab === t.id
            ? 'bg-white text-amber-700 shadow-sm'
            : 'text-stone-600 hover:bg-white',
        ]"
        @click="activeTab = t.id"
      >
        {{ t.label }}
      </button>
    </div>

    <section v-if="activeTab === 'dia'">
      <div v-if="store.delDia" class="max-w-md">
        <RecipeCard
          :recipe="store.delDia.recipe"
          :image-url="store.delDia.imageUrl"
          :image-pending="false"
          :show-view="false"
        />
      </div>
      <p v-else class="text-sm text-stone-500">
        Aún no has cocinado ninguna receta hoy. Ábrela desde el detalle y presiona "Cocinar receta".
      </p>
    </section>

    <section v-else-if="activeTab === 'generadas'">
      <div v-if="store.generadasHoy.length > 0" class="grid gap-4 md:grid-cols-2">
        <RecipeCard
          v-for="r in store.generadasHoy"
          :key="r.hash"
          :recipe="r.recipe"
          :image-url="r.imageUrl"
          :image-pending="false"
          :show-view="false"
        />
      </div>
      <p v-else class="text-sm text-stone-500">
        No hay recetas generadas hoy. Pregúntale al asistente qué puedes cocinar con tu despensa.
      </p>
    </section>

    <section v-else>
      <div v-if="store.favoritas.length > 0" class="grid gap-4 md:grid-cols-2">
        <RecipeCard
          v-for="r in store.favoritas"
          :key="r.hash"
          :recipe="r.recipe"
          :image-url="r.imageUrl"
          :image-pending="false"
          :show-view="false"
        />
      </div>
      <p v-else class="text-sm text-stone-500">
        Marca recetas con el corazón para guardarlas aquí.
      </p>
    </section>
  </div>
</template>
