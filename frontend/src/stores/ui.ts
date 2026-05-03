import { defineStore } from 'pinia'
import { ref } from 'vue'

export type Density = 2 | 3 | 4
export type FilterOption = 'All' | 'Articles' | 'Notes' | 'Papers' | 'Excerpts' | 'References'
export type SortOption = 'date-desc' | 'date-asc' | 'title-asc' | 'backlinks-desc'

export const useUIStore = defineStore('ui', () => {
  const sidebarOpen = ref(true)
  const density = ref<Density>(3)
  const activeFilter = ref<FilterOption>('All')
  const sortBy = ref<SortOption>('date-desc')
  const searchQuery = ref('')
  const searchAllTopics = ref(false)
  const tagsExpanded = ref(false)
  const activeSmartView = ref<string | null>(null)

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  return {
    sidebarOpen,
    density,
    activeFilter,
    sortBy,
    searchQuery,
    searchAllTopics,
    tagsExpanded,
    activeSmartView,
    toggleSidebar,
  }
})
