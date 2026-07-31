<script setup lang="ts">
import { RouterView } from 'vue-router'
import NavBar from './NavBar.vue'
</script>

<template>
  <div class="min-h-screen bg-oat-50 text-ink-900">
    <div
      aria-hidden="true"
      class="pointer-events-none fixed inset-x-0 top-0 z-0 h-72 bg-[radial-gradient(60%_100%_at_50%_0%,rgba(232,163,61,0.14),transparent_70%)]"
    />
    <div class="relative z-10">
      <NavBar />
      <main class="mx-auto max-w-5xl px-4 py-8">
        <RouterView v-slot="{ Component }">
          <Transition name="route" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.route-enter-active,
.route-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}
.route-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.route-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
