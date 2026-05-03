import { apiFetch } from './client'

// ── Status ────────────────────────────────────────────────────────────────────

export interface QAStatus {
  configured: boolean
  model: string | null
}

export const getQAStatus = () => apiFetch<QAStatus>('/qa/status')

// ── Q&A ───────────────────────────────────────────────────────────────────────

export interface QASource {
  id: string
  title: string
  type: string
  snippet: string
}

export interface QAResponse {
  answer: string
  sources: QASource[]
}

export const askQuestion = (question: string, topic_id: string) =>
  apiFetch<QAResponse>('/qa', {
    method: 'POST',
    body: JSON.stringify({ question, topic_id }),
  })

// ── Article assistance ────────────────────────────────────────────────────────

export interface AssistRelatedEntry {
  id: string
  title: string
  type: string
  img_color: string
}

export const assistSummarize = (entry_id: string) =>
  apiFetch<{ summary: string }>('/assist/summarize', {
    method: 'POST',
    body: JSON.stringify({ entry_id }),
  })

export const assistTags = (entry_id: string) =>
  apiFetch<{ tags: string[] }>('/assist/tags', {
    method: 'POST',
    body: JSON.stringify({ entry_id }),
  })

export const assistRelated = (entry_id: string) =>
  apiFetch<{ entries: AssistRelatedEntry[] }>('/assist/related', {
    method: 'POST',
    body: JSON.stringify({ entry_id }),
  })

export const assistExtend = (entry_id: string, prompt = '') =>
  apiFetch<{ extension: string }>('/assist/extend', {
    method: 'POST',
    body: JSON.stringify({ entry_id, prompt }),
  })
