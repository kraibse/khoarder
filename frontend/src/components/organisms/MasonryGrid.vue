<script setup lang="ts">
import { computed } from 'vue'
import type { Entry } from '@/data/mock'
import KnowledgeCard from '@/components/molecules/KnowledgeCard.vue'
import { useUIStore } from '@/stores/ui'

defineProps<{
  entries: Entry[]
  showExcerpt?: boolean
}>()

const uiStore = useUIStore()

defineEmits<{ deleted: [] }>()

const masonryClass = computed(() => {
  switch (uiStore.density) {
    case 2:
      return 'columns-1 sm:columns-2 gap-4'
    case 4:
      return 'columns-2 sm:columns-3 lg:columns-4 gap-3'
    default:
      return 'columns-1 sm:columns-2 lg:columns-3 gap-4'
  }
})
</script>

<template>
  <div :class="masonryClass">
    <KnowledgeCard
      v-for="entry in entries"
      :key="entry.id"
      :entry="entry"
      :show-excerpt="showExcerpt !== false"
      @deleted="$emit('deleted')"
    />
  </div>

  <div
    v-if="!entries.length"
    class="flex flex-col items-center justify-center py-24 text-ink-3"
  >
    <p class="text-[15px]">No entries match this filter.</p>
    <p class="text-xs mt-1">Try a different filter or add a new entry.</p>
  </div>
</template>
