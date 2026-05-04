import { apiFetch } from './client'

export interface EntryOut {
  id: string
  topic_id: string | null
  type: string
  title: string
  excerpt: string
  tags: string[]
  date: string
  source: string | null
  has_img: boolean
  img_url: string | null
  img_height: number | null
  img_color: string
  is_starred: boolean
  backlink_count: number
  headline?: string | null  // FTS snippet with <mark> highlights, present only in search results
}

export interface ArticleDetailOut extends EntryOut {
  body: string
  word_count: number
  read_time_min: number
  source_url: string | null
}

export interface BacklinkOut {
  id: string
  relation_id: string
  title: string
  type: string
  refs: number
}

export interface RelatedEntryOut {
  id: string
  relation_id: string
  title: string
  type: string
  img_color: string
}

export interface AttachmentOut {
  id: string
  filename: string
  ext: string
  size_bytes: number
  created_at: string
}

export interface EntryListParams {
  topic_id?: string
  type?: string
  sort?: string
  q?: string
  tag?: string
}

function buildQuery(params: EntryListParams): string {
  const p = new URLSearchParams()
  if (params.topic_id) p.set('topic_id', params.topic_id)
  if (params.type) p.set('type', params.type)
  if (params.sort) p.set('sort', params.sort)
  if (params.q) p.set('q', params.q)
  if (params.tag) p.set('tag', params.tag)
  const s = p.toString()
  return s ? `?${s}` : ''
}

export const getEntries = (params: EntryListParams = {}) =>
  apiFetch<EntryOut[]>(`/entries${buildQuery(params)}`)

export const getEntry = (id: string) =>
  apiFetch<ArticleDetailOut>(`/entries/${id}`)

export const getBacklinks = (id: string) =>
  apiFetch<BacklinkOut[]>(`/entries/${id}/backlinks`)

export const getRelated = (id: string) =>
  apiFetch<RelatedEntryOut[]>(`/entries/${id}/related`)

export const getAttachments = (id: string) =>
  apiFetch<AttachmentOut[]>(`/entries/${id}/attachments`)

export const getAllTags = () => apiFetch<string[]>('/tags')

// ── Write ─────────────────────────────────────────────────────────────────────

export interface TopicSuggestionCreate {
  name: string
  description?: string
  color: string
}

export interface EntryCreate {
  topic_id: string | null
  type?: string
  title: string
  excerpt?: string
  body?: string
  source_url?: string | null
  source_label?: string | null
  has_img?: boolean
  img_url?: string | null
  is_starred?: boolean
  tags?: string[]
  topic_suggestion?: TopicSuggestionCreate
}

export interface EntryUpdate {
  title?: string
  type?: string
  body?: string
  excerpt?: string
  source_url?: string | null
  source_label?: string | null
  img_url?: string | null
  is_starred?: boolean
  tags?: string[]
}

export const createEntry = (body: EntryCreate) =>
  apiFetch<ArticleDetailOut>('/entries', {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const updateEntry = (id: string, data: EntryUpdate) =>
  apiFetch<ArticleDetailOut>(`/entries/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const deleteEntry = (id: string) =>
  apiFetch<void>(`/entries/${id}`, { method: 'DELETE' })

export const getSuggestions = (id: string) =>
  apiFetch<RelatedEntryOut[]>(`/entries/${id}/suggestions`)

export interface TopicSuggestionOut {
  name: string
  description: string
  color: string
  is_new: boolean
}

export interface TopicPreviewRequest {
  title: string
  excerpt?: string
  body?: string
  feedback?: string | null
}

export interface URLPreviewOut {
  title: string
  excerpt: string
  body: string
  has_img: boolean
  img_url: string | null
  suggestion: TopicSuggestionOut | null
  partial: boolean  // true when full content could not be extracted automatically
}

export const previewTopic = (data: TopicPreviewRequest) =>
  apiFetch<TopicSuggestionOut>('/entries/preview-topic', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const previewImportUrl = (topic_id: string | null, url: string) =>
  apiFetch<URLPreviewOut>('/entries/preview-import-url', {
    method: 'POST',
    body: JSON.stringify({ topic_id, url }),
  })

export const importUrl = (topic_id: string | null, url: string, topic_suggestion?: TopicSuggestionCreate) =>
  apiFetch<ArticleDetailOut>('/entries/import-url', {
    method: 'POST',
    body: JSON.stringify({ topic_id, url, topic_suggestion }),
  })

export async function uploadAttachment(entryId: string, file: File): Promise<AttachmentOut> {
  const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/entries/${entryId}/attachments`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json() as Promise<AttachmentOut>
}

export const deleteAttachment = (attachmentId: string) =>
  apiFetch<void>(`/attachments/${attachmentId}`, { method: 'DELETE' })

export function attachmentDownloadUrl(attachmentId: string): string {
  const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'
  return `${BASE}/attachments/${attachmentId}/download`
}
