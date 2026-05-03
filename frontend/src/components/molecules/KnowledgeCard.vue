<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Entry } from '@/data/mock'
import ColorPlaceholder from './ColorPlaceholder.vue'
import OverflowMenu from './OverflowMenu.vue'
import AppTag from '@/components/atoms/AppTag.vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import { updateEntry, deleteEntry } from '@/api/entries'
import { useEntriesStore } from '@/stores/entries'

const props = defineProps<{
  entry: Entry
  showExcerpt?: boolean
  cardRadius?: number
}>()

const router = useRouter()
const entriesStore = useEntriesStore()
const menuPos = ref<{ x: number; y: number } | null>(null)
const isStarred = ref(props.entry.isStarred)

function openCard() {
  router.push({ name: 'article', params: { id: props.entry.id } })
}

function openMenu(e: MouseEvent) {
  e.stopPropagation()
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  menuPos.value = { x: rect.left, y: rect.bottom + 4 }
}

const emit = defineEmits<{
  deleted: []
}>()

async function handleAction(label: string) {
  if (label === 'Star') {
    const next = !isStarred.value
    isStarred.value = next
    try {
      await updateEntry(props.entry.id, { is_starred: next })
      entriesStore.patchEntry(props.entry.id, { isStarred: next })
    } catch (e) {
      // Revert on failure
      isStarred.value = !next
      console.error('Failed to star entry:', e)
    }
  } else if (label === 'Delete') {
    try {
      await deleteEntry(props.entry.id)
      emit('deleted')
    } catch (e) {
      console.error('Failed to delete entry:', e)
    }
  } else {
    console.log(label, props.entry.id)
  }
}
</script>

<template>
  <div class="break-inside-avoid mb-4">
    <article
      :style="{ borderRadius: `${cardRadius ?? 10}px` }"
      class="bg-surface border border-line overflow-hidden cursor-pointer group
             transition-all duration-[180ms]
             hover:-translate-y-px hover:shadow-card"
      style="--border-hover: oklch(78% 0.012 65)"
      @click="openCard"
    >
      <!-- Image / placeholder -->
      <img
        v-if="entry.hasImg && entry.imgUrl"
        :src="entry.imgUrl"
        :alt="entry.title"
        class="w-full object-cover border-b border-line"
        :style="{ height: `${entry.imgH ?? 200}px` }"
        loading="lazy"
      />
      <ColorPlaceholder
        v-else-if="entry.hasImg && entry.imgColor"
        :color="entry.imgColor"
        :height="entry.imgH ?? 200"
        :label="entry.title.toLowerCase().replace(/[^a-z ]/g, '').split(' ').slice(0, 3).join(' ')"
        class="border-b border-line"
      />

      <!-- Card body -->
      <div class="px-[14px] pt-3 pb-[10px] flex flex-col gap-[6px]">
        <!-- Type label -->
        <div class="text-[10px] font-semibold tracking-[0.08em] uppercase text-ink-3">
          {{ entry.type }}
        </div>

        <!-- Title -->
        <h2 class="font-serif text-[15px] leading-[1.35] text-ink" style="text-wrap: pretty">
          {{ entry.title }}
        </h2>

        <!-- Excerpt / search headline -->
        <div
          v-if="showExcerpt !== false"
          class="text-xs text-ink-2 leading-[1.55] line-clamp-3"
        >
          <!-- eslint-disable-next-line vue/no-v-html -->
          <span v-if="entry.headline" class="search-hl" v-html="entry.headline" />
          <span v-else>{{ entry.excerpt }}</span>
        </div>

        <!-- Tags -->
        <div v-if="entry.tags.length" class="flex flex-wrap gap-1 mt-0.5">
          <AppTag
            v-for="tag in entry.tags.slice(0, 3)"
            :key="tag"
            :label="tag"
          />
        </div>
      </div>

      <!-- Card footer -->
      <div
        class="flex items-center justify-between px-[14px] py-[8px] border-t border-line"
      >
        <span class="text-[11px] text-ink-3">
          {{ entry.date }}{{ entry.source ? ` · ${entry.source}` : '' }}
        </span>

        <div class="flex items-center gap-1">
          <!-- Star indicator -->
          <AppIcon
            v-if="isStarred"
            name="star-filled"
            :size="13"
            class="text-accent"
          />

          <!-- Three-dot menu — revealed on hover -->
          <button
            type="button"
            class="w-6 h-6 rounded-[5px] flex items-center justify-center
                   text-ink-3 opacity-0 group-hover:opacity-100
                   hover:bg-surface-2 hover:text-ink
                   transition-opacity duration-[120ms]"
            aria-label="Card actions"
            @click="openMenu"
          >
            <AppIcon name="three-dots" :size="13" />
          </button>
        </div>
      </div>
    </article>

    <!-- Context menu -->
    <OverflowMenu
      v-if="menuPos"
      :x="menuPos.x"
      :y="menuPos.y"
      @close="menuPos = null"
      @action="handleAction"
    />
  </div>
</template>

<style scoped>
.search-hl :deep(mark) {
  background: var(--accent-bg);
  color: var(--accent);
  border-radius: 2px;
  padding: 0 1px;
}
</style>
