import { apiFetch } from './client'

export interface MemoryOut {
  id: string
  topic_id: string | null
  content: string
  type: string
  trust_score: number
  created_at: string
  updated_at: string
}

export interface MemoryCreate {
  topic_id?: string | null
  content: string
  type?: string
  trust_score?: number
}

export interface MemoryUpdate {
  content?: string
  type?: string
  trust_score?: number
}

export async function createMemory(body: MemoryCreate): Promise<MemoryOut> {
  return apiFetch('/memories', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listMemories(topicId?: string): Promise<MemoryOut[]> {
  const query = topicId !== undefined ? `?topic_id=${encodeURIComponent(topicId)}` : ''
  return apiFetch(`/memories${query}`)
}

export async function getMemory(id: string): Promise<MemoryOut> {
  return apiFetch(`/memories/${id}`)
}

export async function updateMemory(id: string, body: MemoryUpdate): Promise<MemoryOut> {
  return apiFetch(`/memories/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function deleteMemory(id: string): Promise<void> {
  return apiFetch(`/memories/${id}`, { method: 'DELETE' })
}
