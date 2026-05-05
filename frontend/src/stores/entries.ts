import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Entry, EntryType } from '@/data/mock'
import { getEntries, type EntryOut } from '@/api/entries'
import { useUIStore } from './ui'
import { useTopicsStore } from './topics'

function mapEntry(e: EntryOut): Entry {
  return {
    id: e.id,
    topicId: e.topic_id,
    type: e.type as EntryType,
    hasImg: e.has_img,
    imgUrl: e.img_url ?? undefined,
    imgH: e.img_height ?? undefined,
    imgColor: e.img_color,
    isStarred: e.is_starred,
    title: e.title,
    excerpt: e.excerpt,
    tags: e.tags,
    date: e.date,
    source: e.source ?? undefined,
    backlinkCount: e.backlink_count,
    headline: e.headline ?? undefined,
    headlines: e.headlines ?? undefined,
    matchCount: e.match_count ?? undefined,
  }
}

export const useEntriesStore = defineStore('entries', () => {
  const entries = ref<Entry[]>([])
  const loading = ref(false)
  const uiStore = useUIStore()
  const topicsStore = useTopicsStore()

  const isSearching = computed(() => uiStore.searchQuery.trim().length > 0)

  const filteredEntries = computed(() => {
    let result =
      uiStore.activeFilter === 'All'
        ? entries.value
        : entries.value.filter((e) => {
            const f = uiStore.activeFilter
            if (f === 'Articles') return e.type === 'Article'
            if (f === 'Notes') return e.type === 'Note'
            if (f === 'Papers') return e.type === 'Paper'
            if (f === 'Excerpts') return e.type === 'Excerpt'
            if (f === 'References') return e.type === 'Reference'
            return true
          })

    // Smart view / nav item filtering
    if (uiStore.activeSmartView) {
      switch (uiStore.activeSmartView) {
        case 'untagged':
          result = result.filter((e) => e.tags.length === 0)
          break
        case 'no-excerpt':
          result = result.filter((e) => !e.excerpt || e.excerpt.trim().length === 0)
          break
        case 'backlinked':
          result = [...result].sort((a, b) => (b.backlinkCount ?? 0) - (a.backlinkCount ?? 0))
          break
        // 'recent' needs no filter — default API sort is date desc
      }
    }

    // Starred nav item
    if (topicsStore.activeTopicId === 'starred') {
      result = result.filter((e) => e.isStarred)
    }

    // When searching, backend returns results ranked by relevance — preserve that order
    if (isSearching.value) return result

    const sorted = [...result]
    if (uiStore.sortBy === 'date-asc') sorted.sort((a, b) => a.date.localeCompare(b.date))
    else if (uiStore.sortBy === 'title-asc') sorted.sort((a, b) => a.title.localeCompare(b.title))
    else if (uiStore.sortBy === 'backlinks-desc')
      sorted.sort((a, b) => (b.backlinkCount ?? 0) - (a.backlinkCount ?? 0))
    // default: date-desc — API already returns newest first

    return sorted
  })

  async function loadEntries(topicId: string | null, q?: string): Promise<void> {
    loading.value = true
    try {
      const data = await getEntries({
        ...(topicId ? { topic_id: topicId } : {}),
        ...(q ? { q } : {}),
      })
      entries.value = data.map(mapEntry)
    } finally {
      loading.value = false
    }
  }

  function getById(id: string): Entry | undefined {
    return entries.value.find((e) => e.id === id)
  }

  function patchEntry(id: string, partial: Partial<Entry>): void {
    const idx = entries.value.findIndex((e) => e.id === id)
    if (idx !== -1) {
      entries.value[idx] = { ...entries.value[idx], ...partial }
    }
  }

  return { entries, filteredEntries, loading, isSearching, loadEntries, getById, patchEntry }
})
