import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'despensa',
      component: () => import('../features/pantry/PantryView.vue'),
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('../features/chat/ChatView.vue'),
    },
    {
      path: '/recetas',
      name: 'recetas',
      component: () => import('../features/recipes/RecipesView.vue'),
    },
    {
      path: '/recetas/:hash',
      name: 'receta-detalle',
      component: () => import('../features/recipes/RecipeDetailView.vue'),
    },
  ],
})

export default router
