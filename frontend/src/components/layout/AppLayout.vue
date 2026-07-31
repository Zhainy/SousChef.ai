<script setup lang="ts">
import { RouterView } from 'vue-router'
import NavBar from './NavBar.vue'
</script>

<template>
  <div class="min-h-screen bg-stone-50 text-stone-900">
    <NavBar />
    <main class="mx-auto max-w-5xl px-4 py-6">
      <RouterView />
    </main>
  </div>
</template>
