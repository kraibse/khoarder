<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Entry } from '@/data/mock'
import ColorPlaceholder from './ColorPlaceholder.vue'
import OverflowMenu from './OverflowMenu.vue'
import SearchHits from './SearchHits.vue'
import AppTag from '@/components/atoms/AppTag.vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import { updateEntry, deleteEntry } from '@/api/entries'
import { useEntriesStore } from '@/stores/entries'
import { useUIStore } from '@/stores/ui'
import { useTopicsStore } from '@/stores/topics'

const props = defineProps<{
  entry: Entry
  showExcerpt?: boolean
  cardRadius?: number
}>()

const uiStore = useUIStore()
const topicsStore = useTopicsStore()
const router = useRouter()
const entriesStore = useEntriesStore()
const menuPos = ref<{ x: number; y: number } | null>(null)
const isStarred = ref(props.entry.isStarred)

const showTagEditor = ref(false)
const tagInput = ref('')
const tagLoading = ref(false)

const showMovePicker = ref(false)
const moveTargetTopicId = ref<string | null>(null)
const moveLoading = ref(false)

function openCard() {
  const q = uiStore.searchQuery.trim()
  router.push({
    name: 'article',
    params: { id: props.entry.id },
    ...(q ? { query: { q } } : {}),
  })
}

function jumpToHit(_id: string, hitIdx: number) {
  const q = uiStore.searchQuery.trim()
  router.push({
    name: 'article',
    params: { id: props.entry.id },
    query: { q, hit: String(hitIdx) },
  })
}

function openAllHits(_id: string) {
  const q = uiStore.searchQuery.trim()
  router.push({
    name: 'article',
    params: { id: props.entry.id },
    query: { q, all: '1' },
  })
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
  } else if (label === 'Open') {
    openCard()
  } else if (label === 'Open in New Tab') {
    const q = uiStore.searchQuery.trim()
    const url = router.resolve({
      name: 'article',
      params: { id: props.entry.id },
      ...(q ? { query: { q } } : {}),
    }).href
    window.open(url, '_blank')
  } else if (label === 'Copy link') {
    const q = uiStore.searchQuery.trim()
    const url = window.location.origin + router.resolve({
      name: 'article',
      params: { id: props.entry.id },
      ...(q ? { query: { q } } : {}),
    }).href
    try {
      await navigator.clipboard.writeText(url)
    } catch (e) {
      console.error('Failed to copy link:', e)
    }
  } else if (label === 'Edit tags') {
    tagInput.value = (props.entry.tags ?? []).join(', ')
    showTagEditor.value = true
  } else if (label === 'Move to…') {
    moveTargetTopicId.value = props.entry.topicId
    showMovePicker.value = true
  }
}

async function saveTags() {
  tagLoading.value = true
  try {
    const tags = tagInput.value.split(',').map((t) => t.trim()).filter(Boolean)
    await updateEntry(props.entry.id, { tags })
    entriesStore.patchEntry(props.entry.id, { tags })
    showTagEditor.value = false
  } catch (e) {
    console.error('Failed to save tags:', e)
  } finally {
    tagLoading.value = false
  }
}

async function doMove() {
  if (!moveTargetTopicId.value) return
  moveLoading.value = true
  try {
    await updateEntry(props.entry.id, { topic_id: moveTargetTopicId.value })
    showMovePicker.value = false
    emit('deleted')
  } catch (e) {
    console.error('Failed to move entry:', e)
  } finally {
    moveLoading.value = false
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

        <!-- Excerpt — always show when available -->
        <div
          v-if="showExcerpt !== false && entry.excerpt"
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

      <!-- Search hit excerpts — only when search is active -->
      <SearchHits
        v-if="entry.headlines && entry.headlines.length > 0"
        :card-id="entry.id"
        :headlines="entry.headlines"
        :match-count="entry.matchCount ?? entry.headlines.length"
        :query="uiStore.searchQuery"
        @jump="jumpToHit"
        @open-all="openAllHits"
      />

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

    <!-- Tag editor modal -->
    <Teleport to="body">
      <Transition name="fade" appear>
        <div
          v-if="showTagEditor"
          class="fixed inset-0 z-[200] flex items-center justify-center"
          style="background: oklch(16% 0.01 60 / 0.35)"
          @click.self="showTagEditor = false"
        >
          <div class="bg-surface border border-line rounded-[14px] p-6 w-[420px] max-w-[90vw] shadow-modal">
            <h3 class="font-serif text-[18px] mb-4">Edit tags</h3>
            <input
              v-model="tagInput"
              type="text"
              placeholder="cognition, memory"
              class="w-full h-10 px-3 border border-line rounded-[8px] bg-surface-2
                     text-[13px] text-ink placeholder:text-ink-3 outline-none focus:border-accent mb-4"
              @keydown.enter="saveTags"
            />
            <div class="flex gap-2">
              <button
                type="button"
                class="flex-1 py-[9px] rounded-lg border border-line text-[13px] text-ink-3 hover:bg-surface-2"
                @click="showTagEditor = false"
              >Cancel</button>
              <button
                type="button"
                :disabled="tagLoading"
                class="flex-1 py-[9px] rounded-lg bg-accent text-[13px] text-white disabled:opacity-50"
                @click="saveTags"
              >{{ tagLoading ? 'Saving…' : 'Save' }}</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Move-to picker modal -->
    <Teleport to="body">
      <Transition name="fade" appear>
        <div
          v-if="showMovePicker"
          class="fixed inset-0 z-[200] flex items-center justify-center"
          style="background: oklch(16% 0.01 60 / 0.35)"
          @click.self="showMovePicker = false"
        >
          <div class="bg-surface border border-line rounded-[14px] p-6 w-[420px] max-w-[90vw] shadow-modal">
            <h3 class="font-serif text-[18px] mb-4">Move to topic</h3>
            <select
              v-model="moveTargetTopicId"
              class="w-full h-10 px-3 border border-line rounded-[8px] bg-surface-2
                     text-[13px] text-ink outline-none focus:border-accent mb-4"
            >
              <option v-for="t in topicsStore.topics" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
            <div class="flex gap-2">
              <button
                type="button"
                class="flex-1 py-[9px] rounded-lg border border-line text-[13px] text-ink-3 hover:bg-surface-2"
                @click="showMovePicker = false"
              >Cancel</button>
              <button
                type="button"
                :disabled="moveLoading"
                class="flex-1 py-[9px] rounded-lg bg-accent text-[13px] text-white disabled:opacity-50"
                @click="doMove"
              >{{ moveLoading ? 'Moving…' : 'Move' }}</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
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
