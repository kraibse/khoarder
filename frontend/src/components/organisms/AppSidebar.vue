<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/atoms/AppIcon.vue'
import TopicModal from '@/components/molecules/TopicModal.vue'
import ImportModal from '@/components/molecules/ImportModal.vue'
import { useTopicsStore } from '@/stores/topics'
import { useUIStore } from '@/stores/ui'
import { SMART_VIEWS, type Topic } from '@/data/mock'
import { getTopicTags, exportTopicUrl } from '@/api/topics'

const router = useRouter()

const topicsStore = useTopicsStore()
const uiStore = useUIStore()

const showTopicModal = ref(false)
const showImportModal = ref(false)
const editingTopic = ref<Topic | undefined>(undefined)

function openNewTopic() {
  editingTopic.value = undefined
  showTopicModal.value = true
}

function openEditTopic(topic: Topic, e: Event) {
  e.stopPropagation()
  editingTopic.value = topic
  showTopicModal.value = true
}

const tagsExpanded = ref(false)
const navTags = ref<string[]>([])

const visibleTags = () => (tagsExpanded.value ? navTags.value : navTags.value.slice(0, 6))

const navItems = [
  { id: 'home', label: 'Overview', icon: 'home' },
  { id: 'inbox', label: 'Inbox', icon: 'inbox' },
  { id: 'all', label: 'All Entries', icon: 'book' },
  { id: 'starred', label: 'Starred', icon: 'star' },
  { id: 'chat', label: 'Chat', icon: 'message' },
]

async function fetchTags(topicId: string) {
  if (!topicId) return
  navTags.value = await getTopicTags(topicId)
}

onMounted(() => {
  if (topicsStore.activeTopicId && !isNavId(topicsStore.activeTopicId)) {
    fetchTags(topicsStore.activeTopicId)
  }
})

watch(() => topicsStore.activeTopicId, (id) => {
  if (id && !isNavId(id)) fetchTags(id)
})

function isNavId(id: string) {
  return navItems.some((n) => n.id === id)
}

function selectTopic(id: string) {
  uiStore.activeSmartView = null
  topicsStore.setActiveTopic(id)
  if (router.currentRoute.value.path.startsWith('/chat')) {
    router.push(`/chat/${id}`)
  }
  if (window.innerWidth < 768) uiStore.sidebarOpen = false
}

function selectNavItem(id: string) {
  if (id === 'chat') {
    router.push('/chat')
    if (window.innerWidth < 768) uiStore.sidebarOpen = false
    return
  }
  uiStore.activeSmartView = null
  topicsStore.setActiveTopic(id)
  if (window.innerWidth < 768) uiStore.sidebarOpen = false
}

function selectSmartView(id: string) {
  uiStore.activeSmartView = id
  topicsStore.activeTopicId = ''
  if (window.innerWidth < 768) uiStore.sidebarOpen = false
}

function handleExport() {
  const topic = topicsStore.activeTopic
  if (topic && !isNavId(topic.id)) {
    window.location.href = exportTopicUrl(topic.id)
  } else {
    alert('Please select a topic to export.')
  }
}

function handleSettings() {
  router.push('/settings')
}
</script>

<template>
  <aside
    class="sidebar"
    :class="{ 'sidebar-collapsed': !uiStore.sidebarOpen }"
  >
    <!-- Logo -->
    <div
      class="flex items-center gap-[9px] px-4 border-b border-line flex-shrink-0"
      style="height: 58px"
    >
      <div
        class="w-7 h-7 rounded-[7px] bg-ink flex items-center justify-center flex-shrink-0"
      >
        <svg
          viewBox="0 0 14 14"
          class="w-[14px] h-[14px]"
          fill="none"
          stroke="var(--bg)"
          stroke-width="1"
          stroke-linecap="round"
        >
          <path d="M7 1L2 4v6l5 3 5-3V4L7 1z" />
          <path d="M7 1v12M2 4l5 3M12 4l-5 3" />
        </svg>
      </div>
      <span class="font-serif text-[15px] tracking-[-0.01em] whitespace-nowrap">
        Knowledge Hoarder
      </span>
    </div>

    <!-- Scroll area -->
    <div class="flex-1 overflow-y-auto py-3">
      <!-- Navigate -->
      <div class="mb-1">
        <div class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3 px-4 pt-[10px] pb-1">
          Navigate
        </div>
        <div
          v-for="item in navItems"
          :key="item.id"
          class="sidebar-item"
          :class="{ active: topicsStore.activeTopicId === item.id || (item.id === 'chat' && router.currentRoute.value.path.startsWith('/chat')) }"
          @click="() => selectNavItem(item.id)"
        >
          <AppIcon :name="item.icon" :size="14" class="opacity-70" />
          {{ item.label }}
        </div>
      </div>

      <!-- Topics -->
      <div class="mb-1">
        <div class="flex items-center justify-between px-4 pt-[10px] pb-1">
          <span class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3">Topics</span>
          <button
            type="button"
            class="text-ink-3 hover:text-ink p-[1px] rounded"
            aria-label="New topic"
            @click="openNewTopic"
          >
            <AppIcon name="plus" :size="11" />
          </button>
        </div>
        <div
          v-for="topic in topicsStore.topics"
          :key="topic.id"
          class="sidebar-item group"
          :class="{ active: topicsStore.activeTopicId === topic.id }"
          @click="selectTopic(topic.id)"
        >
          <span
            class="w-[7px] h-[7px] rounded-full flex-shrink-0"
            :style="{ background: topic.color }"
          />
          <span class="flex-1 truncate">{{ topic.name }}</span>
          <button
            type="button"
            class="ml-1 opacity-0 group-hover:opacity-100 text-ink-3 hover:text-ink
                   transition-opacity duration-[120ms] p-[2px] rounded"
            title="Edit topic"
            @click="openEditTopic(topic, $event)"
          >
            <AppIcon name="edit" :size="10" />
          </button>
          <span
            class="text-[11px] text-ink-3 bg-surface-3 px-[6px] py-[1px] rounded-full flex-shrink-0"
          >
            {{ topic.count }}
          </span>
        </div>
      </div>

      <!-- Smart Views -->
      <div class="mb-1">
        <div class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3 px-4 pt-[10px] pb-1">
          Smart Views
        </div>
        <div
          v-for="view in SMART_VIEWS"
          :key="view.id"
          class="sidebar-item"
          :class="{ active: uiStore.activeSmartView === view.id }"
          @click="() => selectSmartView(view.id)"
        >
          <AppIcon :name="view.icon" :size="14" class="opacity-70" />
          {{ view.name }}
        </div>
      </div>

      <!-- Tags -->
      <div v-if="navTags.length" class="mb-1">
        <div class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3 px-4 pt-[10px] pb-1">
          Tags
        </div>
        <div class="px-3 pb-2 flex flex-wrap gap-1">
          <span
            v-for="tag in visibleTags()"
            :key="tag"
            class="text-[11px] px-[7px] py-[2px] rounded-full bg-surface-3 border border-line
                   text-ink-3 cursor-pointer hover:text-ink transition-colors duration-[120ms]"
          >
            {{ tag }}
          </span>
          <button
            v-if="navTags.length > 6"
            type="button"
            class="text-[11px] px-[7px] py-[2px] rounded-full text-accent cursor-pointer"
            @click="tagsExpanded = !tagsExpanded"
          >
            {{ tagsExpanded ? 'less' : `+${navTags.length - 6} more` }}
          </button>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="border-t border-line py-2 flex-shrink-0">
      <div
        v-for="item in [
          { icon: 'upload', label: 'Import', action: () => showImportModal = true },
          { icon: 'download', label: 'Export', action: handleExport },
          { icon: 'settings', label: 'Settings', action: handleSettings },
        ]"
        :key="item.label"
        class="sidebar-item cursor-pointer"
        @click="item.action"
      >
        <AppIcon :name="item.icon" :size="14" class="opacity-70" />
        {{ item.label }}
      </div>
    </div>
  </aside>

  <TopicModal
    v-if="showTopicModal"
    :topic="editingTopic"
    @close="showTopicModal = false"
    @saved="(t) => { selectTopic(t.id); showTopicModal = false }"
  />

  <ImportModal
    v-if="showImportModal"
    @close="showImportModal = false"
    @imported="showImportModal = false"
  />
</template>
