<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{ text: string }>()

const html = computed(() =>
  DOMPurify.sanitize(
    marked.parse(props.text, { gfm: true, breaks: true }) as string,
  ),
)
</script>

<template>
  <div class="markdown" v-html="html" />
</template>

<style scoped>
.markdown :deep(p) {
  margin-block: 0.5em;
}
.markdown :deep(p:first-child) {
  margin-block-start: 0;
}
.markdown :deep(p:last-child) {
  margin-block-end: 0;
}
.markdown :deep(strong) {
  font-weight: 700;
  color: inherit;
}
.markdown :deep(em) {
  font-style: italic;
}
.markdown :deep(ul),
.markdown :deep(ol) {
  margin-block: 0.5em;
  padding-left: 1.25rem;
  list-style: revert;
}
.markdown :deep(li) {
  margin-block: 0.15em;
}
.markdown :deep(h1),
.markdown :deep(h2),
.markdown :deep(h3) {
  margin-block: 0.6em 0.3em;
  font-weight: 600;
}
.markdown :deep(a) {
  color: oklch(0.37 0.09 150);
  text-decoration: underline;
}
.markdown :deep(code) {
  border-radius: 0.375rem;
  background: oklch(0.95 0.02 90);
  padding: 0.1em 0.35em;
  font-size: 0.9em;
}
.markdown :deep(pre) {
  margin-block: 0.6em;
  overflow-x: auto;
  border-radius: 0.75rem;
  background: oklch(0.955 0.005 90);
  color: oklch(0.25 0.01 90);
  border: 1px solid oklch(0.9 0.01 90);
  padding: 0.75rem 1rem;
}
.markdown :deep(pre code) {
  background: transparent;
  padding: 0;
}
.markdown :deep(blockquote) {
  margin-block: 0.5em;
  border-left: 3px solid oklch(0.85 0.02 90);
  padding-left: 0.75rem;
  color: oklch(0.5 0.01 90);
}
</style>
