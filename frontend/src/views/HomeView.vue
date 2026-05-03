<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import AppSidebar from '@/components/organisms/AppSidebar.vue'
import AppTopBar from '@/components/organisms/AppTopBar.vue'
import MasonryGrid from '@/components/organisms/MasonryGrid.vue'
import FilterChip from '@/components/atoms/FilterChip.vue'
import AddModal from '@/components/molecules/AddModal.vue'
import { useTopicsStore } from '@/stores/topics'
import { useUIStore } from '@/stores/ui'
import { useEntriesStore } from '@/stores/entries'
import type { FilterOption } from '@/stores/ui'

const topicsStore = useTopicsStore()
const uiStore = useUIStore()
const entriesStore = useEntriesStore()

const showAdd = ref(false)
const filters: FilterOption[] = ['All', 'Articles', 'Notes', 'Papers', 'Excerpts', 'References']

const topicStats = computed(() => {
  const topic = topicsStore.activeTopic
  if (!topic) return []
  return [`${topic.count} entries`]
})

function activeTopicId(): string | null {
  if (uiStore.activeSmartView) return null
  const tid = topicsStore.activeTopicId
  if (tid === 'all' || tid === 'starred' || tid === 'inbox' || tid === 'home') return null
  return uiStore.searchAllTopics ? null : tid
}

function reload(q?: string) {
  const tid = activeTopicId()
  const hasSpecialView = uiStore.activeSmartView || ['all', 'starred', 'inbox', 'home'].includes(topicsStore.activeTopicId)
  if (tid !== null || uiStore.searchAllTopics || hasSpecialView) {
    entriesStore.loadEntries(tid, q || undefined)
  }
}

onMounted(async () => {
  await topicsStore.loadTopics()
  reload()
})

// Reload when topic changes (preserve search query)
watch(
  () => topicsStore.activeTopicId,
  () => {
    uiStore.searchAllTopics = false
    reload(uiStore.searchQuery.trim() || undefined)
  },
)

// Reload when smart view changes
watch(
  () => uiStore.activeSmartView,
  () => {
    reload(uiStore.searchQuery.trim() || undefined)
  },
)

// Debounced search query watcher
let searchDebounce: ReturnType<typeof setTimeout> | null = null
watch(
  () => uiStore.searchQuery,
  (q) => {
    if (searchDebounce) clearTimeout(searchDebounce)
    searchDebounce = setTimeout(() => reload(q.trim() || undefined), 280)
  },
)

// Immediate reload when toggling scope
watch(
  () => uiStore.searchAllTopics,
  () => reload(uiStore.searchQuery.trim() || undefined),
)
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-surface">
    <!-- Mobile sidebar overlay -->
    <Transition name="fade">
      <div
        v-if="uiStore.sidebarOpen"
        class="md:hidden fixed inset-0 z-[39]"
        style="background: oklch(16% 0.01 60 / 0.30)"
        @click="uiStore.sidebarOpen = false"
      />
    </Transition>

    <AppSidebar />

    <!-- Main column -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <AppTopBar @open-add="showAdd = true" />

      <main class="flex-1 overflow-y-auto p-6">
        <!-- Topic description strip — hidden during cross-topic search -->
        <div
          v-if="topicsStore.activeTopic && !uiStore.searchAllTopics"
          class="flex items-center gap-3 mb-4 px-4 py-3 bg-surface-2 rounded-lg border border-line"
        >
          <span
            class="w-2 h-2 rounded-full flex-shrink-0"
            :style="{ background: topicsStore.activeTopic.color }"
          />
          <span class="text-[12.5px] text-ink-2 flex-1 truncate">
            {{ topicsStore.activeTopic.description }}
          </span>
          <div class="flex gap-3 flex-shrink-0">
            <span
              v-for="stat in topicStats"
              :key="stat"
              class="text-[11px] text-ink-3 whitespace-nowrap"
            >
              {{ stat }}
            </span>
          </div>
        </div>

        <!-- Cross-topic search banner -->
        <div
          v-if="uiStore.searchAllTopics && entriesStore.isSearching"
          class="flex items-center gap-2 mb-4 px-4 py-2 bg-accent-bg rounded-lg border border-accent/30 text-[12.5px] text-accent"
        >
          <span>Searching all topics</span>
          <span class="text-accent/60">·</span>
          <span>{{ entriesStore.filteredEntries.length }} result{{ entriesStore.filteredEntries.length !== 1 ? 's' : '' }}</span>
        </div>

        <!-- Filter bar — hidden during cross-topic search (filters don't apply) -->
        <div v-if="!uiStore.searchAllTopics" class="flex items-center gap-2 flex-wrap mb-5">
          <FilterChip
            v-for="filter in filters"
            :key="filter"
            :label="filter"
            :active="uiStore.activeFilter === filter"
            @click="uiStore.activeFilter = filter"
          />
          <div class="flex-1" />
          <select
            v-model="uiStore.sortBy"
            class="h-[26px] px-2 text-[11.5px] font-sans border border-line rounded-[6px]
                   bg-surface text-ink-2 outline-none cursor-pointer
                   hover:border-accent transition-colors duration-[120ms]"
          >
            <option value="date-desc">Date added ↓</option>
            <option value="date-asc">Date added ↑</option>
            <option value="title-asc">Title A–Z</option>
            <option value="backlinks-desc">Most backlinked</option>
          </select>
        </div>

        <!-- Masonry grid -->
        <MasonryGrid :entries="entriesStore.filteredEntries" @deleted="reload()" />
      </main>
    </div>

    <!-- Add modal -->
    <AddModal
      v-if="showAdd"
      @close="showAdd = false"
      @created="reload()"
    />
  </div>
</template>
