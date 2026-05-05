import { apiFetch } from './client'

export interface SuggestionOut {
  id: string
  title: string
  excerpt: string
  source: string
  source_url: string
  type: string
  relevance: number
  tags: string[]
  provider: string
}

export interface SuggestRequest {
  query?: string
  offset?: number
  limit?: number
}

export const fetchSuggestions = (topicSlugOrId: string, body: SuggestRequest) =>
  apiFetch<SuggestionOut[]>(`/topics/${encodeURIComponent(topicSlugOrId)}/suggest`, {
    method: 'POST',
    body: JSON.stringify({
      query: body.query ?? '',
      offset: body.offset ?? 0,
      limit: body.limit ?? 5,
    }),
  })
