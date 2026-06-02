import { apiFetch } from './client'

export interface TopicOut {
  id: string
  slug: string
  name: string
  color: string
  description: string
  count: number
}

export interface TopicCreate {
  name: string
  description?: string
  color?: string
}

export interface TopicUpdate {
  name?: string
  description?: string
  color?: string
}

export const getTopics = () => apiFetch<TopicOut[]>('/topics')
export const getTopic = (slugOrId: string) => apiFetch<TopicOut>(`/topics/${slugOrId}`)
export const getTopicTags = (slugOrId: string) => apiFetch<string[]>(`/topics/${slugOrId}/tags`)

export const createTopic = (data: TopicCreate) =>
  apiFetch<TopicOut>('/topics', { method: 'POST', body: JSON.stringify(data) })

export const updateTopic = (slugOrId: string, data: TopicUpdate) =>
  apiFetch<TopicOut>(`/topics/${slugOrId}`, { method: 'PATCH', body: JSON.stringify(data) })

export function exportTopicUrl(slugOrId: string): string {
  const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'
  return `${BASE}/topics/${slugOrId}/export`
}

export const importTopic = (data: unknown, slugOrId?: string) => {
  const url = slugOrId ? `/topics/${slugOrId}/import` : '/topics/import'
  return apiFetch<{ topic_id: string; created: number }>(url, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export const generateOverview = (topicId: string) =>
  apiFetch<{ id: string; title: string; body: string }>(`/topics/${topicId}/generate-overview`, { method: 'POST' })

export const suggestRelatedEntries = (entryId: string) =>
  apiFetch<{ id: string; title: string; type: string; img_color: string }[]>(`/entries/${entryId}/suggest-related`, { method: 'POST' })
