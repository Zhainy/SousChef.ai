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
      class="inline-flex items-center gap-1 text-sm font-medium text-amber-700 hover:text-amber-800"
      @click="router.back()"
    >
      ← Volver
    </button>

    <p v-if="!saved" class="text-stone-500">Receta no encontrada.</p>
    <RecipeCard
      v-else
      :recipe="saved.recipe"
      :image-url="saved.imageUrl"
      :image-pending="false"
      :show-cook="true"
    />
  </div>
</template>
