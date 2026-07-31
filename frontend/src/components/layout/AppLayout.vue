<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppLoader from '../ui/AppLoader.vue'
import NavBar from './NavBar.vue'

const NAV_DELAY_MS = 2000

const route = useRoute()
const navigating = ref(false)
let timer: number | undefined

watch(
  () => route.fullPath,
  () => {
    navigating.value = true
    clearTimeout(timer)
    timer = window.setTimeout(() => {
      navigating.value = false
    }, NAV_DELAY_MS)
  },
)

onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <div class="min-h-screen bg-oat-50 text-ink-900">
    <div
      aria-hidden="true"
      class="pointer-events-none fixed inset-x-0 top-0 z-0 h-72 bg-[radial-gradient(60%_100%_at_50%_0%,rgba(232,163,61,0.14),transparent_70%)]"
    />
    <div class="relative z-10">
      <NavBar />
      <main class="mx-auto flex max-w-5xl flex-col px-4 py-8">
        <RouterView v-slot="{ Component }">
          <Transition name="route" mode="out-in">
            <div
              v-if="navigating"
              class="flex min-h-[50vh] flex-1 items-center justify-center"
            >
              <AppLoader size="lg" tone="saffron" :role="null" />
            </div>
            <component v-else :is="Component" />
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
