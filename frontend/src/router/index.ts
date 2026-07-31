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
  ],
})

export default router
