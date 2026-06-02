import { apiFetch } from './client'

export interface ConversationOut {
  id: string
  topic_id: string | null
  title: string
  created_at: string
  updated_at: string
}

export interface ConversationListOut {
  id: string
  topic_id: string | null
  title: string
  updated_at: string
  message_count: number
}

export interface MessageOut {
  id: string
  conversation_id: string
  role: string
  content: string
  created_at: string
  entry_id: string | null
}

export async function createConversation(topicId?: string, title?: string): Promise<ConversationOut> {
  return apiFetch('/conversations', {
    method: 'POST',
    body: JSON.stringify({ topic_id: topicId ?? null, title: title ?? 'New Conversation' }),
  })
}

export async function listConversations(topicId?: string): Promise<ConversationListOut[]> {
  const query = topicId ? `?topic_id=${encodeURIComponent(topicId)}` : ''
  return apiFetch(`/conversations${query}`)
}

export async function getConversation(id: string): Promise<ConversationOut> {
  return apiFetch(`/conversations/${id}`)
}

export async function updateConversation(id: string, title: string): Promise<ConversationOut> {
  return apiFetch(`/conversations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  })
}

export async function deleteConversation(id: string): Promise<void> {
  return apiFetch(`/conversations/${id}`, { method: 'DELETE' })
}

export async function sendMessage(conversationId: string, content: string): Promise<MessageOut> {
  return apiFetch(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })
}

export async function deleteMessage(conversationId: string, messageId: string): Promise<void> {
  return apiFetch(`/conversations/${conversationId}/messages/${messageId}`, { method: 'DELETE' })
}
