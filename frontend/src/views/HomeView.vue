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

const isSearchingActive = computed(() => uiStore.searchQuery.trim().length > 0)

const totalHits = computed(() => {
  if (!isSearchingActive.value) return 0
  return entriesStore.filteredEntries.reduce((sum, e) => {
    const fromCount = e.matchCount ?? 0
    const fromList = e.headlines?.length ?? 0
    return sum + Math.max(fromCount, fromList)
  }, 0)
})

function clearSearch() {
  uiStore.searchQuery = ''
  uiStore.searchAllTopics = false
}

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
        <!-- Topic description strip — hidden during cross-topic search OR active search -->
        <div
          v-if="topicsStore.activeTopic && !uiStore.searchAllTopics && !isSearchingActive"
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

        <!-- Search summary banner (in-topic or all-topics) -->
        <div
          v-if="isSearchingActive"
          class="flex items-center gap-2 mb-4 px-3.5 py-2.5 bg-accent-bg rounded-lg border border-accent/30 text-[12.5px] text-accent"
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"
               stroke-linecap="round" class="w-3.5 h-3.5 flex-shrink-0">
            <circle cx="7" cy="7" r="4.5" />
            <path d="M10.5 10.5L14 14" />
          </svg>
          <span>
            <strong class="font-semibold">{{ totalHits }}</strong>
            match{{ totalHits === 1 ? '' : 'es' }} across
            <strong class="font-semibold">{{ entriesStore.filteredEntries.length }}</strong>
            entr{{ entriesStore.filteredEntries.length === 1 ? 'y' : 'ies' }} for
            <strong class="font-semibold">"{{ uiStore.searchQuery.trim() }}"</strong>
            <span v-if="uiStore.searchAllTopics" class="text-accent/60"> · all topics</span>
          </span>
          <button
            type="button"
            class="ml-auto px-2 py-1 rounded-[5px] text-[11px] border border-accent/30
                   hover:bg-surface transition-colors duration-[120ms]"
            @click="clearSearch"
          >
            Clear
          </button>
        </div>

        <!-- Filter bar — hidden during cross-topic search OR active search -->
        <div v-if="!uiStore.searchAllTopics && !isSearchingActive" class="flex items-center gap-2 flex-wrap mb-5">
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
