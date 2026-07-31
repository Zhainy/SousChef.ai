<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <header class="sticky top-0 z-10 border-b border-stone-200 bg-white/80 backdrop-blur">
    <div class="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
      <RouterLink to="/" class="text-lg font-bold tracking-tight text-amber-700">
        SousChef<span class="text-stone-400">.ai</span>
      </RouterLink>
      <nav class="flex gap-1 rounded-full bg-stone-100 p-1">
        <RouterLink
          to="/"
          class="rounded-full px-4 py-1.5 text-sm font-medium text-stone-600 transition hover:bg-white"
          active-class="bg-white text-amber-700 shadow-sm"
        >
          Despensa
        </RouterLink>
        <RouterLink
          to="/chat"
          class="rounded-full px-4 py-1.5 text-sm font-medium text-stone-600 transition hover:bg-white"
          active-class="bg-white text-amber-700 shadow-sm"
        >
          Asistente
        </RouterLink>
      </nav>
    </div>
  </header>
</template>
