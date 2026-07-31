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
  <div class="space-y-5">
    <div>
      <p class="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-basil-600">
        <span class="h-px w-6 bg-saffron-500" />
        Tus recetas
      </p>
      <h1 class="font-display mt-1 text-3xl font-semibold text-basil-950 sm:text-4xl">
        Recetas
      </h1>
      <p class="mt-1 text-sm text-ink-500">
        Las que generó el asistente con tu despensa
      </p>
    </div>

    <div class="flex gap-1 rounded-full border border-oat-200 bg-white/70 p-1 shadow-sm backdrop-blur">
      <button
        v-for="t in tabs"
        :key="t.id"
        data-test="tab"
        :class="[
          'rounded-full px-4 py-1.5 text-sm font-semibold transition-all duration-200',
          activeTab === t.id
            ? 'bg-basil-800 text-oat-50 shadow-sm'
            : 'text-ink-500 hover:bg-basil-50 hover:text-basil-700',
        ]"
        @click="activeTab = t.id"
      >
        {{ t.label }}
      </button>
    </div>

    <Transition name="tab" mode="out-in">
      <section v-if="activeTab === 'dia'" key="dia">
        <div v-if="store.delDia" class="max-w-md">
          <RecipeCard
            :recipe="store.delDia.recipe"
            :image-url="store.delDia.imageUrl"
            :image-pending="false"
            :show-view="false"
          />
        </div>
        <div v-else class="empty-state">
          <span class="empty-state__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" class="h-6 w-6" fill="none">
              <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6" />
              <path d="M12 7v5l3 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
            </svg>
          </span>
          <p class="font-medium text-ink-700">Aún no has cocinado ninguna receta hoy</p>
          <p class="text-sm text-ink-500">
            Ábrela desde el detalle y presiona "Cocinar receta".
          </p>
        </div>
      </section>

      <section v-else-if="activeTab === 'generadas'" key="generadas">
        <div v-if="store.generadasHoy.length > 0" class="grid gap-5 md:grid-cols-2">
          <RecipeCard
            v-for="r in store.generadasHoy"
            :key="r.hash"
            :recipe="r.recipe"
            :image-url="r.imageUrl"
            :image-pending="false"
            :show-view="false"
          />
        </div>
        <div v-else class="empty-state">
          <span class="empty-state__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" class="h-6 w-6" fill="none">
              <path d="M5 8h14v2a7 7 0 0 1-7 7 7 7 0 0 1-7-7V8z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
            </svg>
          </span>
          <p class="font-medium text-ink-700">No hay recetas generadas hoy</p>
          <p class="text-sm text-ink-500">
            Pregúntale al asistente qué puedes cocinar con tu despensa.
          </p>
        </div>
      </section>

      <section v-else key="favoritas">
        <div v-if="store.favoritas.length > 0" class="grid gap-5 md:grid-cols-2">
          <RecipeCard
            v-for="r in store.favoritas"
            :key="r.hash"
            :recipe="r.recipe"
            :image-url="r.imageUrl"
            :image-pending="false"
            :show-view="false"
          />
        </div>
        <div v-else class="empty-state">
          <span class="empty-state__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" class="h-6 w-6" fill="currentColor">
              <path d="M12 21s-7.5-4.7-10-9C.6 8.6 2.3 5 5.6 5c2 0 3.2 1.1 4.4 3 1.2-1.9 2.4-3 4.4-3 3.3 0 5 3.6 3.6 7-2.5 4.3-10 9-10 9z" />
            </svg>
          </span>
          <p class="font-medium text-ink-700">Marca recetas con el corazón</p>
          <p class="text-sm text-ink-500">para guardarlas aquí.</p>
        </div>
      </section>
    </Transition>
  </div>
</template>

<style scoped>
@reference '../../assets/main.css';

.empty-state {
  @apply flex flex-col items-center gap-1 rounded-2xl border border-dashed border-oat-300 bg-oat-50/50 p-10 text-center;
}

.empty-state__icon {
  @apply mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-basil-100 text-basil-600;
}

.tab-enter-active,
.tab-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.tab-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.tab-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
