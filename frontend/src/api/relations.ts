import { apiFetch } from './client'

export interface RelationOut {
  id: string
  from_entry_id: string
  to_entry_id: string
  kind: string
}

export const addRelation = (from_entry_id: string, to_entry_id: string, kind: string) =>
  apiFetch<RelationOut>('/relations', {
    method: 'POST',
    body: JSON.stringify({ from_entry_id, to_entry_id, kind }),
  })

export const removeRelation = (id: string) =>
  apiFetch<void>(`/relations/${id}`, { method: 'DELETE' })
