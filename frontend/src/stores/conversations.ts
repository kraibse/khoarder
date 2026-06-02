import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ConversationListOut, ConversationOut, MessageOut } from '@/api/conversations'
import {
  createConversation,
  listConversations,
  getConversation,
  updateConversation,
  deleteConversation,
  sendMessage,
  deleteMessage,
} from '@/api/conversations'

export const useConversationsStore = defineStore('conversations', () => {
  const conversations = ref<ConversationListOut[]>([])
  const activeConversation = ref<ConversationOut | null>(null)
  const messages = ref<MessageOut[]>([])
  const loading = ref(false)
  const sending = ref(false)

  async function loadConversations(topicId?: string) {
    loading.value = true
    try {
      conversations.value = await listConversations(topicId)
    } finally {
      loading.value = false
    }
  }

  async function createNewConversation(topicId?: string, title?: string) {
    const conv = await createConversation(topicId, title)
    await loadConversations(topicId)
    return conv
  }

  async function loadConversation(id: string) {
    loading.value = true
    try {
      activeConversation.value = await getConversation(id)
      messages.value = activeConversation.value.messages ?? []
    } finally {
      loading.value = false
    }
  }

  async function renameConversation(id: string, title: string) {
    const conv = await updateConversation(id, title)
    if (activeConversation.value?.id === id) {
      activeConversation.value = conv
    }
    const idx = conversations.value.findIndex((c) => c.id === id)
    if (idx !== -1) {
      conversations.value[idx].title = title
    }
  }

  async function removeConversation(id: string) {
    await deleteConversation(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (activeConversation.value?.id === id) {
      activeConversation.value = null
      messages.value = []
    }
  }

  async function postMessage(conversationId: string, content: string) {
    sending.value = true
    try {
      const userMsg: MessageOut = {
        id: `tmp-${Date.now()}`,
        conversation_id: conversationId,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
        entry_id: null,
      }
      messages.value.push(userMsg)

      const assistantMsg = await sendMessage(conversationId, content)
      messages.value.push(assistantMsg)

      const idx = conversations.value.findIndex((c) => c.id === conversationId)
      if (idx !== -1) {
        conversations.value[idx].message_count += 2
        conversations.value[idx].updated_at = new Date().toISOString()
      }
    } catch (e: any) {
      const errorMsg: MessageOut = {
        id: `err-${Date.now()}`,
        conversation_id: conversationId,
        role: 'assistant',
        content: `LLM request failed: ${e.message || 'Please check that LM Studio is running and a model is loaded.'}`,
        created_at: new Date().toISOString(),
        entry_id: null,
      }
      messages.value.push(errorMsg)
    } finally {
      sending.value = false
    }
  }

  async function removeMessage(conversationId: string, messageId: string) {
    await deleteMessage(conversationId, messageId)
    messages.value = messages.value.filter((m) => m.id !== messageId)
  }

  return {
    conversations,
    activeConversation,
    messages,
    loading,
    sending,
    loadConversations,
    createNewConversation,
    loadConversation,
    renameConversation,
    removeConversation,
    postMessage,
    removeMessage,
  }
})
