import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Topic } from '@/data/mock'
import { getTopics, createTopic, updateTopic, type TopicOut, type TopicCreate, type TopicUpdate } from '@/api/topics'

function mapTopic(t: TopicOut): Topic {
  return {
    id: t.id,
    slug: t.slug,
    name: t.name,
    color: t.color,
    description: t.description,
    count: t.count,
  }
}

export const useTopicsStore = defineStore('topics', () => {
  const topics = ref<Topic[]>([])
  const activeTopicId = ref<string>('')
  const loading = ref(false)

  const activeTopic = computed(
    () => topics.value.find((t) => t.id === activeTopicId.value) ?? topics.value[0],
  )

  async function loadTopics() {
    loading.value = true
    try {
      const data = await getTopics()
      topics.value = data.map(mapTopic)
      if (!activeTopicId.value && topics.value.length > 0) {
        activeTopicId.value = topics.value[0].id
      }
    } finally {
      loading.value = false
    }
  }

  function setActiveTopic(id: string) {
    activeTopicId.value = id
  }

  async function createNewTopic(data: TopicCreate) {
    const topic = await createTopic(data)
    await loadTopics()
    activeTopicId.value = topic.id
    return topic
  }

  async function editTopic(slugOrId: string, data: TopicUpdate) {
    await updateTopic(slugOrId, data)
    await loadTopics()
  }

  return { topics, activeTopicId, activeTopic, loading, loadTopics, setActiveTopic, createNewTopic, editTopic }
})
