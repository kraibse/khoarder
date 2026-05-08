import { apiFetch } from './client'

export interface ConfigOut {
  llm_base_url: string
  llm_model: string
  llm_timeout: number
  llm_context_entries: number
  system_prompt: string
  auto_tag_count: number
  camoufox_enabled: boolean
  camoufox_timeout: number
  camoufox_url: string
  flaresolverr_url: string
  // Browserless: backend never returns the raw token — only the boolean below.
  browserless_enabled: boolean
  browserless_token_set: boolean
  browserless_url: string
  browserless_timeout: number
  static_fetch_timeout: number
  suggest_searxng_url: string
  suggest_use_llm_expand: boolean
  suggest_use_llm_rerank: boolean
}

export interface ConfigUpdate {
  llm_base_url?: string
  llm_model?: string
  llm_timeout?: number
  llm_context_entries?: number
  system_prompt?: string
  auto_tag_count?: number
  camoufox_enabled?: boolean
  camoufox_timeout?: number
  camoufox_url?: string
  flaresolverr_url?: string
  browserless_enabled?: boolean
  // Write-only: empty string clears it, undefined leaves it unchanged.
  browserless_token?: string
  browserless_url?: string
  browserless_timeout?: number
  static_fetch_timeout?: number
  suggest_searxng_url?: string
  suggest_use_llm_expand?: boolean
  suggest_use_llm_rerank?: boolean
}

export interface HealthOut {
  reachable: boolean
  model: string | null
  error: string | null
}

export interface CamoufoxStatusOut {
  installed: boolean
  browser_ready: boolean
  message: string
}

export interface BrowserlessStatusOut {
  configured: boolean
  reachable: boolean
  message: string
}

export const getConfig = () => apiFetch<ConfigOut>('/config')

export const updateConfig = (data: ConfigUpdate) =>
  apiFetch<ConfigOut>('/config', { method: 'PUT', body: JSON.stringify(data) })

export const checkHealth = () => apiFetch<HealthOut>('/config/health')

export const checkCamoufoxStatus = () => apiFetch<CamoufoxStatusOut>('/config/camoufox-status')

export const checkFlaresolverrStatus = () => apiFetch<CamoufoxStatusOut>('/config/flaresolverr-status')

export const checkBrowserlessStatus = () => apiFetch<BrowserlessStatusOut>('/config/browserless-status')
