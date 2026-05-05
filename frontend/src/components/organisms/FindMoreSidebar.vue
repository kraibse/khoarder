<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import SkeletonCard from '@/components/atoms/SkeletonCard.vue'
import SuggestionCard from '@/components/molecules/SuggestionCard.vue'
import type { Topic } from '@/data/mock'
import { fetchSuggestions, type SuggestionOut } from '@/api/suggest'
import { importUrl } from '@/api/entries'

const props = defineProps<{
  topic: Topic
}>()

const emit = defineEmits<{
  close: []
  added: [suggestion: SuggestionOut]
}>()

const PAGE_SIZE = 5

const query = ref('')
const queryInput = ref<HTMLInputElement | null>(null)
const loading = ref(true)
const loadingMore = ref(false)
const results = ref<SuggestionOut[]>([])
const exhausted = ref(false)
const error = ref<string | null>(null)
const added = ref<Set<string>>(new Set())
const adding = ref<Set<string>>(new Set())

let debounce: ReturnType<typeof setTimeout> | null = null
let activeRequestId = 0

async function runSearch(reset: boolean) {
  const myId = ++activeRequestId
  if (reset) {
    loading.value = true
    results.value = []
    exhausted.value = false
  } else {
    loadingMore.value = true
  }
  error.value = null

  try {
    const offset = reset ? 0 : results.value.length
    const batch = await fetchSuggestions(props.topic.slug || props.topic.id, {
      query: query.value.trim(),
      offset,
      limit: PAGE_SIZE,
    })
    if (myId !== activeRequestId) return

    if (reset) {
      results.value = batch
    } else {
      const seen = new Set(results.value.map((r) => r.id))
      const fresh = batch.filter((b) => !seen.has(b.id))
      results.value = [...results.value, ...fresh]
    }
    if (batch.length < PAGE_SIZE) {
      exhausted.value = true
    }
  } catch (e) {
    if (myId !== activeRequestId) return
    error.value = e instanceof Error ? e.message : 'Failed to load suggestions'
  } finally {
    if (myId === activeRequestId) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

watch(query, (next, prev) => {
  if (next === prev) return
  if (debounce) clearTimeout(debounce)
  debounce = setTimeout(() => runSearch(true), next.trim().length === 0 ? 350 : 450)
})

watch(
  () => props.topic.id,
  () => runSearch(true),
)

onMounted(() => {
  queryInput.value?.focus()
  runSearch(true)
})

async function handleAdd(s: SuggestionOut) {
  if (added.value.has(s.id) || adding.value.has(s.id)) return
  adding.value.add(s.id)
  try {
    await importUrl(props.topic.id, s.source_url)
    added.value.add(s.id)
    emit('added', s)
  } catch (e) {
    console.error('Add to topic failed:', e)
  } finally {
    adding.value.delete(s.id)
  }
}

function handlePreview(s: SuggestionOut) {
  if (s.source_url) {
    window.open(s.source_url, '_blank', 'noopener,noreferrer')
  }
}

function close() {
  emit('close')
}
</script>

<template>
  <aside class="find-sidebar">
    <header class="find-header">
      <div class="find-title-block">
        <div class="find-title">
          <AppIcon name="sparkle" :size="14" class="text-accent" />
          Suggestions
        </div>
        <div class="find-sub">
          For
          <strong class="text-ink-2 font-medium">{{ topic.name }}</strong>
        </div>
      </div>
      <button
        type="button"
        class="find-close-btn"
        title="Close suggestions"
        @click="close"
      >
        <AppIcon name="x" :size="14" />
      </button>
    </header>

    <div class="find-search">
      <div class="find-search-wrap">
        <AppIcon name="search" :size="13" class="find-search-icon" />
        <input
          ref="queryInput"
          v-model="query"
          type="search"
          class="find-search-input"
          placeholder="Refine suggestions… (or leave empty)"
        />
      </div>
      <p class="find-search-hint">
        <template v-if="query.trim().length === 0">Showing top picks for this topic</template>
        <template v-else>Filtering by "{{ query.trim() }}"</template>
      </p>
    </div>

    <div class="find-results">
      <div class="find-results-label">
        <span>{{ loading ? 'Searching…' : `${results.length} suggestion${results.length === 1 ? '' : 's'}` }}</span>
        <span
          v-if="!loading && results.length > 0"
          class="font-normal normal-case tracking-normal text-ink-3 text-[11px]"
        >
          by relevance
        </span>
      </div>

      <template v-if="loading">
        <SkeletonCard v-for="i in 5" :key="`sk-${i}`" />
      </template>

      <div
        v-else-if="error"
        class="find-empty"
      >
        <div class="empty-icon">
          <AppIcon name="alert" :size="16" />
        </div>
        Suggestions failed to load.<br />
        <span class="text-[11px] text-ink-3">{{ error }}</span>
      </div>

      <div
        v-else-if="results.length === 0"
        class="find-empty"
      >
        <div class="empty-icon">
          <AppIcon name="search" :size="16" />
        </div>
        <template v-if="query.trim()">
          No suggestions match "{{ query.trim() }}".<br />
          Try a broader query or clear the search.
        </template>
        <template v-else>
          No suggestions yet.<br />
          Try a refine query above.
        </template>
      </div>

      <template v-else>
        <SuggestionCard
          v-for="s in results"
          :key="s.id"
          :suggestion="s"
          :added="added.has(s.id)"
          :adding="adding.has(s.id)"
          @add="handleAdd"
          @preview="handlePreview"
        />

        <template v-if="loadingMore">
          <SkeletonCard v-for="i in 2" :key="`sk-more-${i}`" />
        </template>

        <button
          v-if="!loadingMore && !exhausted"
          type="button"
          class="find-more-btn"
          @click="runSearch(false)"
        >
          <AppIcon name="chevron-down" :size="12" />
          Find more
        </button>

        <div
          v-if="!loadingMore && exhausted && results.length > PAGE_SIZE"
          class="text-center text-[11px] text-ink-3 py-3"
        >
          End of suggestions · {{ results.length }} shown
        </div>
      </template>
    </div>
  </aside>
</template>

<style scoped>
.find-sidebar {
  width: 360px;
  min-width: 360px;
  flex-shrink: 0;
  border-left: 1px solid var(--border);
  background: var(--bg-2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: find-slide-in 0.22s cubic-bezier(0.2, 0.8, 0.2, 1);
}

@keyframes find-slide-in {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@media (max-width: 1100px) {
  .find-sidebar {
    width: 320px;
    min-width: 320px;
  }
}

.find-header {
  padding: 16px 16px 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.find-title-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.find-title {
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: 17px;
  line-height: 1.3;
  display: flex;
  align-items: center;
  gap: 6px;
}
.find-sub {
  font-size: 11.5px;
  color: var(--text-3);
}
.find-close-btn {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-3);
  transition: background 0.12s, color 0.12s;
  background: transparent;
  border: none;
  cursor: pointer;
}
.find-close-btn:hover {
  background: var(--bg-3);
  color: var(--text);
}

.find-search {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  background: var(--bg);
}
.find-search-wrap {
  position: relative;
}
.find-search-icon {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-3);
  pointer-events: none;
}
.find-search-input {
  width: 100%;
  height: 34px;
  padding: 0 12px 0 32px;
  background: var(--bg-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text);
  outline: none;
  transition: border-color 0.15s, background 0.15s;
}
.find-search-input::placeholder {
  color: var(--text-3);
}
.find-search-input:focus {
  border-color: var(--accent);
  background: var(--bg);
}
.find-search-hint {
  font-size: 11px;
  color: var(--text-3);
  margin-top: 6px;
  padding: 0 2px;
}

.find-results {
  flex: 1;
  overflow-y: auto;
  padding: 10px 12px 12px;
}
.find-results-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-3);
  padding: 4px 4px 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.find-empty {
  padding: 32px 18px;
  text-align: center;
  color: var(--text-3);
  font-size: 12.5px;
  line-height: 1.5;
}
.find-empty .empty-icon {
  width: 38px;
  height: 38px;
  margin: 0 auto 10px;
  border-radius: 9px;
  background: var(--bg-3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-3);
}

.find-more-btn {
  width: 100%;
  height: 34px;
  margin-top: 8px;
  background: var(--bg);
  border: 1px dashed var(--border);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-2);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  cursor: pointer;
  transition: border-color 0.12s, color 0.12s;
}
.find-more-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}
</style>
