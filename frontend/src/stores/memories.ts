import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MemoryOut } from '@/api/memories'
import {
  createMemory,
  listMemories,
  updateMemory,
  deleteMemory,
} from '@/api/memories'

export const useMemoriesStore = defineStore('memories', () => {
  const memories = ref<MemoryOut[]>([])
  const loading = ref(false)

  async function loadMemories(topicId?: string) {
    loading.value = true
    try {
      memories.value = await listMemories(topicId)
    } finally {
      loading.value = false
    }
  }

  async function addMemory(content: string, topicId?: string, type = 'fact') {
    const mem = await createMemory({
      content,
      topic_id: topicId ?? null,
      type,
      trust_score: 1.0,
    })
    memories.value.unshift(mem)
    return mem
  }

  async function editMemory(id: string, updates: { content?: string; type?: string; trust_score?: number }) {
    const mem = await updateMemory(id, updates)
    const idx = memories.value.findIndex((m) => m.id === id)
    if (idx !== -1) {
      memories.value[idx] = mem
    }
    return mem
  }

  async function removeMemory(id: string) {
    await deleteMemory(id)
    memories.value = memories.value.filter((m) => m.id !== id)
  }

  return {
    memories,
    loading,
    loadMemories,
    addMemory,
    editMemory,
    removeMemory,
  }
})
