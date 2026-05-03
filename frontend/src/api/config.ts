import { apiFetch } from './client'

export interface ConfigOut {
  llm_base_url: string
  llm_model: string
  llm_timeout: number
  llm_context_entries: number
  system_prompt: string
}

export interface ConfigUpdate {
  llm_base_url?: string
  llm_model?: string
  llm_timeout?: number
  llm_context_entries?: number
  system_prompt?: string
}

export interface HealthOut {
  reachable: boolean
  model: string | null
  error: string | null
}

export const getConfig = () => apiFetch<ConfigOut>('/config')

export const updateConfig = (data: ConfigUpdate) =>
  apiFetch<ConfigOut>('/config', { method: 'PUT', body: JSON.stringify(data) })

export const checkHealth = () => apiFetch<HealthOut>('/config/health')
