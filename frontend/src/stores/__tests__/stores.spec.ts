import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { useTopicsStore } from '@/stores/topics'
import { useEntriesStore } from '@/stores/entries'
import { useUIStore } from '@/stores/ui'

describe('Topics Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with empty topics', () => {
    const store = useTopicsStore()
    expect(store.topics).toEqual([])
    expect(store.activeTopicId).toBe('')
  })

  it('sets active topic', () => {
    const store = useTopicsStore()
    store.setActiveTopic('topic-123')
    expect(store.activeTopicId).toBe('topic-123')
  })

  it('computes active topic from list', () => {
    const store = useTopicsStore()
    store.topics = [
      { id: 'a', slug: 'a', name: 'A', color: '#000', description: '', count: 0 },
      { id: 'b', slug: 'b', name: 'B', color: '#000', description: '', count: 0 },
    ]
    store.activeTopicId = 'b'
    expect(store.activeTopic?.name).toBe('B')
  })
})

describe('Entries Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes empty', () => {
    const store = useEntriesStore()
    expect(store.entries).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('filters by type', () => {
    const store = useEntriesStore()
    const ui = useUIStore()

    store.entries = [
      { id: '1', topicId: 't', type: 'Article', title: 'A', excerpt: '', tags: [], date: '2024-01-01', hasImg: false, imgColor: '', isStarred: false },
      { id: '2', topicId: 't', type: 'Note', title: 'B', excerpt: '', tags: [], date: '2024-01-01', hasImg: false, imgColor: '', isStarred: false },
    ]

    ui.activeFilter = 'Articles'
    expect(store.filteredEntries).toHaveLength(1)
    expect(store.filteredEntries[0].type).toBe('Article')

    ui.activeFilter = 'All'
    expect(store.filteredEntries).toHaveLength(2)
  })

  it('filters starred when nav is starred', () => {
    const store = useEntriesStore()
    const topics = useTopicsStore()

    store.entries = [
      { id: '1', topicId: 't', type: 'Article', title: 'A', excerpt: '', tags: [], date: '2024-01-01', hasImg: false, imgColor: '', isStarred: true },
      { id: '2', topicId: 't', type: 'Article', title: 'B', excerpt: '', tags: [], date: '2024-01-01', hasImg: false, imgColor: '', isStarred: false },
    ]
    topics.activeTopicId = 'starred'
    expect(store.filteredEntries).toHaveLength(1)
    expect(store.filteredEntries[0].title).toBe('A')
  })
})

describe('UI Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('toggles sidebar', () => {
    const store = useUIStore()
    expect(store.sidebarOpen).toBe(true)
    store.toggleSidebar()
    expect(store.sidebarOpen).toBe(false)
  })

  it('defaults search to empty', () => {
    const store = useUIStore()
    expect(store.searchQuery).toBe('')
    expect(store.searchAllTopics).toBe(false)
  })
})
