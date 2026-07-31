<template>
  <div class="space-y-6" data-test="skeleton" aria-hidden="true">
    <div v-for="group in 3" :key="group" class="space-y-2">
      <div class="skeleton h-4 w-32" />
      <div v-for="row in 2" :key="row" class="skeleton h-16" />
    </div>
  </div>
</template>
