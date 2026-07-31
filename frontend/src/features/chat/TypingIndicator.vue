<template>
  <span class="inline-flex items-center gap-1" role="status" aria-label="Escribiendo">
    <span class="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" />
    <span class="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" style="animation-delay: 0.15s" />
    <span class="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" style="animation-delay: 0.3s" />
  </span>
</template>

<style scoped>
.typing-dot {
  animation: typing-bounce 1.2s ease-in-out infinite;
}

@keyframes typing-bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .typing-dot {
    animation: none;
  }
}
</style>
