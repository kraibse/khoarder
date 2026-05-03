<script setup lang="ts">
import type { Heading } from '@/composables/useTableOfContents'

const props = defineProps<{
  headings: Heading[]
  activeSlug: string | null
}>()

const emit = defineEmits<{
  navigate: [slug: string]
}>()

function onClick(slug: string) {
  emit('navigate', slug)
}
</script>

<template>
  <nav v-if="headings.length > 0" class="toc text-[12px] leading-relaxed">
    <p class="text-[10px] font-semibold tracking-[0.08em] uppercase text-ink-3 mb-2">
      Contents
    </p>
    <ul class="space-y-[3px]">
      <li
        v-for="h in headings"
        :key="h.slug"
        :class="[
          'cursor-pointer transition-colors duration-100 hover:text-ink truncate',
          h.level === 1 ? 'pl-0' : h.level === 2 ? 'pl-2.5' : 'pl-5',
          activeSlug === h.slug ? 'text-accent font-medium' : 'text-ink-3',
        ]"
        @click="onClick(h.slug)"
      >
        {{ h.text }}
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.toc {
  max-height: calc(100vh - 280px);
  overflow-y: auto;
}
.toc::-webkit-scrollbar {
  width: 3px;
}
.toc::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 2px;
}
</style>
