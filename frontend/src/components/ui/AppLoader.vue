<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    size?: 'sm' | 'md' | 'lg'
    tone?: 'basil' | 'saffron' | 'light' | 'tomato'
    label?: string
    role?: 'status' | 'progress' | null
  }>(),
  {
    size: 'md',
    tone: 'basil',
    label: '',
    role: 'status',
  },
)

const box = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'h-5 w-5'
    case 'lg':
      return 'h-10 w-10'
    default:
      return 'h-7 w-7'
  }
})

const svg = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'h-4 w-4'
    case 'lg':
      return 'h-8 w-8'
    default:
      return 'h-6 w-6'
  }
})

const text = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'text-xs'
    case 'lg':
      return 'text-base'
    default:
      return 'text-sm'
  }
})

const bodyFill = computed(() => {
  switch (props.tone) {
    case 'saffron':
      return '#e8a33d'
    case 'light':
      return '#ffffff'
    case 'tomato':
      return '#c24b32'
    default:
      return '#2e513c'
  }
})

const steamColor = computed(() => {
  switch (props.tone) {
    case 'saffron':
      return '#b86f1f'
    case 'light':
      return 'rgba(255,255,255,0.9)'
    case 'tomato':
      return '#a03b27'
    default:
      return '#558a63'
  }
})
</script>

<template>
  <span
    class="inline-flex items-center gap-2"
    :class="text"
    :role="role ?? undefined"
    :aria-label="label || 'Cargando'"
  >
    <span :class="box" class="relative inline-flex items-center justify-center">
      <svg
        :class="svg"
        viewBox="0 0 32 32"
        fill="none"
        aria-hidden="true"
        class="animate-simmer"
      >
        <path
          :stroke="steamColor"
          stroke-width="2"
          stroke-linecap="round"
          class="steam-wisp"
          d="M13 6c0-1.5 1-2 1-3.5"
        />
        <path
          :stroke="steamColor"
          stroke-width="2"
          stroke-linecap="round"
          class="steam-wisp"
          style="animation-delay: 0.5s"
          d="M19 5c0-1.5 1-2 1-3.5"
        />
        <path
          d="M6 10h20v2H6z"
          :fill="bodyFill"
          opacity="0.85"
        />
        <path
          d="M6 12h20c0 5-1.5 8-10 8S6 17 6 12z"
          :fill="bodyFill"
        />
        <path
          :fill="bodyFill"
          d="M5 10.5a1.5 1.5 0 0 1 3 0zM24 10.5a1.5 1.5 0 0 1 3 0z"
        />
        <path
          d="M4 26a2 2 0 0 1 2-2h20a2 2 0 0 1 2 2H4z"
          :fill="bodyFill"
          opacity="0.55"
        />
        <circle
          cx="16"
          cy="21"
          r="1.6"
          :fill="tone === 'light' ? 'rgba(255,255,255,0.9)' : '#f4c471'"
          class="simmer-bubble"
        />
      </svg>
    </span>
    <span v-if="label">{{ label }}</span>
  </span>
</template>

<style scoped>
.steam-wisp {
  transform-origin: center;
  animation: steam 1.4s ease-in-out infinite;
}

.simmer-bubble {
  transform-origin: center;
  animation: simmer-bubble 1.2s ease-in-out infinite;
}

@keyframes simmer-bubble {
  0%,
  100% {
    transform: translateY(0) scale(1);
    opacity: 0.5;
  }
  50% {
    transform: translateY(-1px) scale(1.15);
    opacity: 1;
  }
}
</style>
