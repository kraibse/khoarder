import { ref, onMounted } from 'vue'
import type { QAMessage } from '@/data/mock'
import { askQuestion, getQAStatus, type QAStatus } from '@/api/qa'

export function useQA(topicId: string) {
  const messages = ref<QAMessage[]>([
    {
      role: 'assistant',
      text: "Ask me anything about this topic. I'll answer based on the entries in your knowledge base.",
    },
  ])
  const input = ref('')
  const loading = ref(false)
  const status = ref<QAStatus>({ configured: false, model: null })

  onMounted(async () => {
    try {
      status.value = await getQAStatus()
    } catch {
      // backend unreachable — leave as unconfigured
    }
  })

  async function send() {
    const q = input.value.trim()
    if (!q || loading.value) return

    input.value = ''
    messages.value.push({ role: 'user', text: q })
    loading.value = true

    try {
      const res = await askQuestion(q, topicId)
      messages.value.push({
        role: 'assistant',
        text: res.answer,
        sources: res.sources,
      })
    } catch (err) {
      messages.value.push({
        role: 'assistant',
        text: err instanceof Error ? err.message : 'Unable to reach LM Studio. Check your configuration.',
      })
    } finally {
      loading.value = false
    }
  }

  return { messages, input, loading, status, send }
}
