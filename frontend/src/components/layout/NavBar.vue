<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <header
    class="sticky top-0 z-20 border-b border-basil-800 bg-basil-950/95 text-oat-50 shadow-[0_1px_0_rgba(255,255,255,0.06)_inset] backdrop-blur"
  >
    <div class="mx-auto flex max-w-5xl items-center justify-between gap-2 px-3 py-2.5 sm:gap-3 sm:px-4 sm:py-3">
      <!-- Logo: se achica en móvil -->
      <RouterLink to="/" class="group flex min-w-0 shrink-0 items-center gap-2">
        <span
          class="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-basil-800 shadow-inner transition-transform duration-300 group-hover:-rotate-6 sm:h-9 sm:w-9"
          aria-hidden="true"
        >
          <svg viewBox="0 0 32 32" class="h-4.5 w-4.5 sm:h-5 sm:w-5" fill="none" aria-hidden="true">
            <path d="M6 10h20v2H6z" fill="#e8a33d" opacity=".85" />
            <path d="M6 12h20c0 5-1.5 8-10 8S6 17 6 12z" fill="#e8a33d" />
            <path
              class="nav-steam"
              d="M12 5c0-1.5 1-2 1-3.5"
              stroke="#f4c471"
              stroke-width="2"
              stroke-linecap="round"
            />
            <path
              class="nav-steam"
              style="animation-delay: 0.55s"
              d="M18 5c0-1.5 1-2 1-3.5"
              stroke="#f4c471"
              stroke-width="2"
              stroke-linecap="round"
            />
          </svg>
        </span>
        <span class="font-display truncate text-lg font-semibold tracking-tight sm:text-xl">
          SousChef<span class="text-saffron-400">.ai</span>
        </span>
      </RouterLink>

      <!-- Nav: compacto en móvil (íconos + label corto), completo en sm+ -->
      <nav
        class="flex shrink-0 gap-0.5 rounded-full border border-white/10 bg-white/5 p-1 sm:gap-1"
        aria-label="Navegación principal"
      >
        <RouterLink
          v-for="link in [
            { to: '/', label: 'Despensa', icon: '🫙', shortLabel: 'Despensa' },
            { to: '/chat', label: 'Asistente', icon: '🍳', shortLabel: 'Chat' },
            { to: '/recetas', label: 'Recetas', icon: '📋', shortLabel: 'Recetas' },
          ]"
          :key="link.to"
          :to="link.to"
          class="rounded-full text-sm font-medium text-oat-100/70 transition-all duration-200 hover:bg-white/10 hover:text-white"
          active-class="bg-oat-50 !text-basil-900 shadow-sm"
        >
          <!-- Pantallas grandes: sólo texto -->
          <span class="hidden px-3.5 py-1.5 sm:block">{{ link.label }}</span>
          <!-- Pantallas pequeñas: ícono + label corto -->
          <span class="flex items-center gap-1 px-2 py-1.5 sm:hidden">
            <span aria-hidden="true" class="text-base leading-none">{{ link.icon }}</span>
            <span class="text-[11px] leading-none">{{ link.shortLabel }}</span>
          </span>
        </RouterLink>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.nav-steam {
  transform-origin: center;
  animation: steam 1.4s ease-in-out infinite;
}
</style>
