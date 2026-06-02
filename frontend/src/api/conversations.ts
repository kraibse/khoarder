import { apiFetch } from './client'

export interface ConversationOut {
  id: string
  topic_id: string | null
  title: string
  created_at: string
  updated_at: string
}

export interface ConversationWithMessagesOut extends ConversationOut {
  messages: MessageOut[]
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

export async function getConversation(id: string): Promise<ConversationWithMessagesOut> {
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

export interface StreamCallbacks {
  onToken: (token: string) => void
  onDone: (message: MessageOut) => void
  onError: (error: string) => void
}

export function sendMessageStream(
  conversationId: string,
  content: string,
  callbacks: StreamCallbacks,
): () => void {
  const base = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'
  const url = `${base}/conversations/${conversationId}/messages/stream`
  const abortController = new AbortController()

  const run = async () => {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
        signal: abortController.signal,
      })
      if (!response.ok) {
        const text = await response.text()
        callbacks.onError(`HTTP ${response.status}: ${text}`)
        return
      }
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (payload === '[DONE]') continue
          try {
            const event = JSON.parse(payload)
            if (event.type === 'token') {
              callbacks.onToken(event.content)
            } else if (event.type === 'done') {
              callbacks.onDone(event.message as MessageOut)
            }
          } catch {
            // Fallback: treat raw payload as a token (non-JSON legacy line)
            callbacks.onToken(payload)
          }
        }
      }
      // Process remaining buffer
      if (buffer.startsWith('data: ')) {
        const payload = buffer.slice(6).trim()
        if (payload && payload !== '[DONE]') {
          try {
            const event = JSON.parse(payload)
            if (event.type === 'done') {
              callbacks.onDone(event.message as MessageOut)
            }
          } catch {
            callbacks.onToken(payload)
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        callbacks.onError(e.message || 'Stream failed')
      }
    }
  }

  run()
  return () => abortController.abort()
}

export async function deleteMessage(conversationId: string, messageId: string): Promise<void> {
  return apiFetch(`/conversations/${conversationId}/messages/${messageId}`, { method: 'DELETE' })
}

export async function createEntryFromChat(
  messageId?: string,
  conversationId?: string,
  type?: string,
  title?: string,
): Promise<{ id: string; title: string }> {
  return apiFetch('/entries/from-chat', {
    method: 'POST',
    body: JSON.stringify({
      message_id: messageId ?? null,
      conversation_id: conversationId ?? null,
      type: type ?? 'Note',
      title: title ?? null,
    }),
  })
}
