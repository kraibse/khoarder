<script setup lang="ts">
import { ref, computed } from 'vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import IconButton from '@/components/atoms/IconButton.vue'
import { useTopicsStore } from '@/stores/topics'
import { useUIStore } from '@/stores/ui'
import type { Density } from '@/stores/ui'

const props = defineProps<{
  findOpen?: boolean
  findAvailable?: boolean
}>()

const emit = defineEmits<{
  openAdd: []
  toggleFind: []
}>()

const topicsStore = useTopicsStore()
const uiStore = useUIStore()

const searchFocused = ref(false)

const densityOptions: { n: Density; icon: string; title: string }[] = [
  { n: 2, icon: 'grid-2', title: 'Wide' },
  { n: 3, icon: 'grid-3', title: 'Normal' },
  { n: 4, icon: 'grid-4', title: 'Dense' },
]

const navLabels: Record<string, string> = {
  home: 'Overview',
  inbox: 'Inbox',
  all: 'All Entries',
  starred: 'Starred',
}

const breadcrumbLabel = computed(() => {
  return navLabels[topicsStore.activeTopicId] ?? topicsStore.activeTopic?.name ?? ''
})

const breadcrumbCount = computed(() => {
  if (navLabels[topicsStore.activeTopicId]) return null
  return topicsStore.activeTopic?.count ?? null
})

function clearSearch() {
  uiStore.searchQuery = ''
  uiStore.searchAllTopics = false
}
</script>

<template>
  <header
    class="flex items-center gap-3 px-6 border-b border-line bg-surface flex-shrink-0 z-20"
    style="height: 58px"
  >
    <!-- Left: sidebar toggle + breadcrumb -->
    <div class="flex items-center gap-[10px] flex-1 min-w-0">
      <IconButton icon="menu" label="Toggle sidebar" @click="uiStore.toggleSidebar" />

      <div class="flex items-center gap-[6px] min-w-0">
        <span class="text-xs text-ink-3">Topics</span>
        <span class="text-ink-3 text-sm">›</span>
        <span class="font-serif text-[17px] whitespace-nowrap overflow-hidden text-ellipsis">
          {{ breadcrumbLabel }}
        </span>
        <span v-if="breadcrumbCount !== null" class="text-[11px] text-ink-3 font-normal whitespace-nowrap">
          {{ breadcrumbCount }} entries
        </span>
      </div>
    </div>

    <!-- Right: search, density, add -->
    <div class="flex items-center gap-2 flex-shrink-0">
      <!-- Search group -->
      <div class="flex items-center gap-1">
        <!-- Input wrapper -->
        <div class="relative flex items-center">
          <AppIcon
            name="search"
            :size="13"
            class="absolute left-[9px] text-ink-3 pointer-events-none"
          />
          <input
            v-model="uiStore.searchQuery"
            type="search"
            :placeholder="uiStore.searchAllTopics ? 'Search all topics…' : 'Search this topic…'"
            :class="[
              'h-8 pl-7 bg-surface-2 border border-line rounded-[7px]',
              'text-[13px] text-ink placeholder:text-ink-3 outline-none',
              'transition-all duration-200',
              uiStore.searchQuery ? 'pr-[28px]' : 'pr-[10px]',
              searchFocused || uiStore.searchQuery
                ? 'w-[260px] border-accent bg-surface'
                : 'w-[200px]',
            ]"
            @focus="searchFocused = true"
            @blur="searchFocused = false"
          />
          <!-- Clear button -->
          <button
            v-if="uiStore.searchQuery"
            type="button"
            class="absolute right-[8px] text-ink-3 hover:text-ink transition-colors"
            aria-label="Clear search"
            @click="clearSearch"
          >
            <AppIcon name="x" :size="11" />
          </button>
        </div>

        <!-- All-topics toggle — only when searching -->
        <button
          v-if="uiStore.searchQuery"
          type="button"
          :class="[
            'h-8 px-[10px] rounded-[7px] text-[11.5px] border whitespace-nowrap',
            'transition-colors duration-[120ms]',
            uiStore.searchAllTopics
              ? 'bg-accent text-white border-accent'
              : 'bg-surface-2 text-ink-3 border-line hover:border-accent hover:text-ink',
          ]"
          title="Toggle between searching this topic or all topics"
          @click="uiStore.searchAllTopics = !uiStore.searchAllTopics"
        >
          All topics
        </button>
      </div>

      <div class="w-px h-5 bg-line mx-0.5" />

      <!-- Density toggle -->
      <div class="flex items-center bg-surface-2 border border-line rounded-[7px] overflow-hidden">
        <button
          v-for="opt in densityOptions"
          :key="opt.n"
          type="button"
          :title="opt.title"
          :class="[
            'w-[30px] h-[30px] flex items-center justify-center transition-colors duration-[120ms]',
            uiStore.density === opt.n ? 'bg-surface-3 text-ink' : 'text-ink-3 hover:text-ink',
          ]"
          @click="uiStore.density = opt.n"
        >
          <AppIcon :name="opt.icon" :size="13" />
        </button>
      </div>

      <div class="w-px h-5 bg-line mx-0.5" />

      <!-- Find more button — only when a real topic is selected -->
      <button
        v-if="props.findAvailable"
        type="button"
        :title="props.findOpen ? 'Close suggestions' : 'Suggest entries to add to this topic'"
        :class="[
          'h-8 px-3 rounded-[7px] text-xs font-medium flex items-center gap-[6px]',
          'border whitespace-nowrap transition-colors duration-[120ms]',
          props.findOpen
            ? 'bg-accent-bg border-accent text-accent'
            : 'bg-surface border-accent text-accent hover:bg-accent-bg',
        ]"
        @click="emit('toggleFind')"
      >
        <AppIcon name="sparkle" :size="13" />
        Find more
      </button>

      <!-- Add button -->
      <button
        type="button"
        class="h-8 px-3 rounded-[7px] text-xs font-medium flex items-center gap-[6px]
               bg-ink text-surface border border-ink
               hover:bg-accent hover:border-accent transition-colors duration-[120ms]"
        @click="emit('openAdd')"
      >
        <AppIcon name="plus" :size="13" />
        Add
      </button>
    </div>
  </header>
</template>
