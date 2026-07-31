<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRecipesStore } from '../../stores/recipes'
import RecipeCard from '../chat/RecipeCard.vue'

const route = useRoute()
const router = useRouter()
const store = useRecipesStore()

const saved = computed(() => store.getByHash(String(route.params.hash)))
</script>

<template>
  <div class="space-y-4">
    <button
      data-test="back"
      class="group inline-flex items-center gap-1.5 text-sm font-semibold text-basil-700 transition hover:text-basil-800"
      @click="router.back()"
    >
      <svg
        viewBox="0 0 16 16"
        class="h-4 w-4 transition-transform duration-200 group-hover:-translate-x-0.5"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M13 8H3m0 0 4 4M3 8l4-4"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
      Volver
    </button>

    <p v-if="!saved" class="rounded-2xl border border-dashed border-oat-300 bg-oat-50/50 p-8 text-center text-ink-500">
      Receta no encontrada.
    </p>
    <RecipeCard
      v-else
      :recipe="saved.recipe"
      :image-url="saved.imageUrl"
      :image-pending="false"
      :show-cook="true"
      class="max-w-2xl"
    />
  </div>
</template>
