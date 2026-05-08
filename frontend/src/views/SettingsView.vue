<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/atoms/AppIcon.vue'
import {
  getConfig,
  updateConfig,
  checkHealth,
  checkCamoufoxStatus,
  checkFlaresolverrStatus,
  checkBrowserlessStatus,
  type ConfigOut,
  type ConfigUpdate,
  type HealthOut,
  type CamoufoxStatusOut,
  type BrowserlessStatusOut,
} from '@/api/config'

const router = useRouter()
const config = ref<ConfigOut | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const success = ref(false)

// LM Studio health
const health = ref<HealthOut | null>(null)
const checkingHealth = ref(false)

// Camoufox status
const cfStatus = ref<CamoufoxStatusOut | null>(null)
const checkingCf = ref(false)

// FlareSolverr status
const fsStatus = ref<CamoufoxStatusOut | null>(null)
const checkingFs = ref(false)

// Browserless status + token-input state.
// `tokenInput` stays blank by default; sending an empty string would clear the
// stored token, so we only forward it when the user actually typed.
const blStatus = ref<BrowserlessStatusOut | null>(null)
const checkingBl = ref(false)
const tokenInput = ref('')
const tokenClearRequested = ref(false)

// Sidebar navigation
type Section =
  | 'lm-studio'
  | 'extension-drafting'
  | 'camoufox'
  | 'flaresolverr'
  | 'browserless'
  | 'find-more'
const activeSection = ref<Section>('lm-studio')

const sections: Array<{ id: Section; label: string; icon: string }> = [
  { id: 'lm-studio', label: 'LM Studio', icon: 'server' },
  { id: 'extension-drafting', label: 'Extension Drafting', icon: 'edit' },
  { id: 'camoufox', label: 'Camoufox', icon: 'globe' },
  { id: 'flaresolverr', label: 'FlareSolverr', icon: 'shield' },
  { id: 'browserless', label: 'Browserless', icon: 'globe' },
  { id: 'find-more', label: 'Find more', icon: 'sparkle' },
]

onMounted(async () => {
  loading.value = true
  try {
    config.value = await getConfig()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load settings'
  } finally {
    loading.value = false
  }
})

async function handleSave() {
  if (!config.value) return
  saving.value = true
  error.value = null
  success.value = false
  try {
    const payload: ConfigUpdate = {
      llm_base_url: config.value.llm_base_url,
      llm_model: config.value.llm_model,
      llm_timeout: config.value.llm_timeout,
      llm_context_entries: config.value.llm_context_entries,
      system_prompt: config.value.system_prompt,
      auto_tag_count: config.value.auto_tag_count,
      camoufox_enabled: config.value.camoufox_enabled,
      camoufox_timeout: config.value.camoufox_timeout,
      camoufox_url: config.value.camoufox_url,
      flaresolverr_url: config.value.flaresolverr_url,
      browserless_enabled: config.value.browserless_enabled,
      browserless_url: config.value.browserless_url,
      browserless_timeout: config.value.browserless_timeout,
      static_fetch_timeout: config.value.static_fetch_timeout,
      suggest_searxng_url: config.value.suggest_searxng_url,
      suggest_use_llm_expand: config.value.suggest_use_llm_expand,
      suggest_use_llm_rerank: config.value.suggest_use_llm_rerank,
    }
    // Browserless token: only send when user actually typed or asked to clear.
    if (tokenClearRequested.value) {
      payload.browserless_token = ''
    } else if (tokenInput.value.trim()) {
      payload.browserless_token = tokenInput.value
    }
    const updated = await updateConfig(payload)
    config.value = updated
    tokenInput.value = ''
    tokenClearRequested.value = false
    success.value = true
    setTimeout(() => (success.value = false), 3000)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to save settings'
  } finally {
    saving.value = false
  }
}

async function handleHealthCheck() {
  checkingHealth.value = true
  try {
    health.value = await checkHealth()
  } catch (e) {
    health.value = { reachable: false, model: null, error: e instanceof Error ? e.message : 'Unknown error' }
  } finally {
    checkingHealth.value = false
  }
}

async function handleCfCheck() {
  checkingCf.value = true
  cfStatus.value = null
  try {
    cfStatus.value = await checkCamoufoxStatus()
  } catch (e) {
    cfStatus.value = { installed: false, browser_ready: false, message: e instanceof Error ? e.message : 'Check failed' }
  } finally {
    checkingCf.value = false
  }
}

async function handleFsCheck() {
  checkingFs.value = true
  fsStatus.value = null
  try {
    fsStatus.value = await checkFlaresolverrStatus()
  } catch (e) {
    fsStatus.value = { installed: false, browser_ready: false, message: e instanceof Error ? e.message : 'Check failed' }
  } finally {
    checkingFs.value = false
  }
}

async function handleBlCheck() {
  checkingBl.value = true
  blStatus.value = null
  try {
    blStatus.value = await checkBrowserlessStatus()
  } catch (e) {
    blStatus.value = {
      configured: false,
      reachable: false,
      message: e instanceof Error ? e.message : 'Check failed',
    }
  } finally {
    checkingBl.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-surface">
    <div class="mx-auto max-w-4xl px-6 py-12">

      <!-- Back + title -->
      <button
        class="mb-6 flex items-center gap-2 text-sm text-ink-2 hover:text-ink"
        @click="router.push('/')"
      >
        <AppIcon name="arrow-left" :size="16" />
        Back
      </button>
      <h1 class="mb-8 font-serif text-2xl text-ink">Settings</h1>

      <div v-if="loading" class="text-sm text-ink-2">Loading…</div>

      <div v-else-if="!config" class="rounded border border-danger bg-[var(--danger-bg)] p-4 text-sm text-danger">
        {{ error }}
      </div>

      <!-- Two-column layout: sidebar + content -->
      <div v-else class="flex gap-0">

        <!-- ── Sidebar ───────────────────────────────────────────────────── -->
        <aside class="w-56 shrink-0 border-r border-line pr-6 pt-0.5">
          <p class="mb-3 px-2 text-[10px] uppercase tracking-widest text-ink-3">Sections</p>
          <nav class="space-y-0.5">
            <button
              v-for="s in sections"
              :key="s.id"
              type="button"
              class="flex w-full items-center gap-2.5 rounded-lg px-3 py-[7px] text-[13px] transition-colors duration-[100ms]"
              :class="activeSection === s.id
                ? 'bg-accent-bg text-accent font-medium'
                : 'text-ink-2 hover:bg-surface-2'"
              @click="activeSection = s.id"
            >
              <AppIcon :name="s.icon" :size="14" class="shrink-0" />
              {{ s.label }}
            </button>
          </nav>
        </aside>

        <!-- ── Content ──────────────────────────────────────────────────── -->
        <div class="flex-1 pl-8">

          <!-- LM Studio ─────────────────────────────────────────────────── -->
          <section v-if="activeSection === 'lm-studio'" class="space-y-5">
            <div>
              <h2 class="mb-0.5 text-[15px] font-semibold text-ink">LM Studio</h2>
              <p class="text-[12.5px] text-ink-3">Connect a locally-running LM Studio instance for AI features.</p>
            </div>

            <div class="space-y-4">
              <div>
                <label class="mb-1 block text-sm text-ink-2">Base URL</label>
                <input
                  v-model="config.llm_base_url"
                  type="text"
                  placeholder="http://192.168.1.100:1234/v1"
                  class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                />
                <p class="mt-1 text-xs text-ink-3">Leave empty to disable AI features.</p>
              </div>

              <div>
                <label class="mb-1 block text-sm text-ink-2">Model name</label>
                <input
                  v-model="config.llm_model"
                  type="text"
                  class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>

              <div class="grid grid-cols-3 gap-4">
                <div>
                  <label class="mb-1 block text-sm text-ink-2">Timeout (s)</label>
                  <input
                    v-model.number="config.llm_timeout"
                    type="number"
                    min="1"
                    max="300"
                    class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
                <div>
                  <label class="mb-1 block text-sm text-ink-2">Context entries</label>
                  <input
                    v-model.number="config.llm_context_entries"
                    type="number"
                    min="1"
                    max="50"
                    class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
                <div>
                  <label class="mb-1 block text-sm text-ink-2">Auto-tags</label>
                  <input
                    v-model.number="config.auto_tag_count"
                    type="number"
                    min="0"
                    max="10"
                    class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                  <p class="mt-1 text-xs text-ink-3">0 to disable</p>
                </div>
              </div>

              <div class="flex items-center gap-3 pt-1">
                <button
                  class="rounded border border-line px-3 py-1.5 text-sm text-ink-2 hover:bg-surface-2 disabled:opacity-50"
                  :disabled="checkingHealth"
                  @click="handleHealthCheck"
                >
                  {{ checkingHealth ? 'Checking…' : 'Test connection' }}
                </button>
                <span v-if="health" class="text-sm">
                  <span v-if="health.reachable" class="text-green-600">Connected</span>
                  <span v-else class="text-danger">Unreachable</span>
                  <span v-if="health.model" class="text-ink-3"> · {{ health.model }}</span>
                </span>
              </div>
              <p v-if="health?.error" class="text-xs text-danger">{{ health.error }}</p>
            </div>
          </section>

          <!-- Extension Drafting ─────────────────────────────────────────── -->
          <section v-else-if="activeSection === 'extension-drafting'" class="space-y-5">
            <div>
              <h2 class="mb-0.5 text-[15px] font-semibold text-ink">Extension Drafting</h2>
              <p class="text-[12.5px] text-ink-3">Custom instructions for the AI when drafting article extensions.</p>
            </div>

            <div>
              <label class="mb-1 block text-sm text-ink-2">System prompt</label>
              <textarea
                v-model="config.system_prompt"
                rows="10"
                placeholder="You are a knowledge-base writing assistant..."
                class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:ring-1 focus:ring-accent resize-none"
              />
              <p class="mt-1 text-xs text-ink-3">
                Leave empty to use the built-in default prompt.
              </p>
            </div>
          </section>

          <!-- Camoufox ───────────────────────────────────────────────────── -->
          <section v-else-if="activeSection === 'camoufox'" class="space-y-5">
            <div>
              <h2 class="mb-0.5 text-[15px] font-semibold text-ink">Camoufox</h2>
              <p class="text-[12.5px] text-ink-3">
                Stealth headless browser for importing articles from JavaScript-heavy or
                bot-protected sites (Cloudflare, SPAs, paywalls). Used only as a last resort
                when all standard extractors return empty content.
              </p>
            </div>

            <!-- Enable toggle -->
            <div class="flex items-start gap-3 rounded-lg border border-line bg-surface-2 px-4 py-3.5">
              <div class="flex-1">
                <p class="text-[13px] font-medium text-ink">Enable Camoufox fallback</p>
                <p class="mt-0.5 text-[12px] text-ink-3">
                  When enabled, Camoufox launches a headless Firefox browser to render pages
                  that return no content through standard HTTP extraction.
                </p>
              </div>
              <button
                type="button"
                role="switch"
                :aria-checked="config.camoufox_enabled"
                class="relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1"
                :class="config.camoufox_enabled ? 'bg-accent' : 'bg-[var(--border)]'"
                @click="config.camoufox_enabled = !config.camoufox_enabled"
              >
                <span
                  class="absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-150"
                  :class="config.camoufox_enabled ? 'translate-x-[18px]' : 'translate-x-0.5'"
                />
              </button>
            </div>

            <!-- Options (greyed when disabled) -->
            <div
              class="space-y-4 transition-opacity duration-150"
              :class="config.camoufox_enabled ? 'opacity-100' : 'opacity-40 pointer-events-none'"
            >
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="mb-1 block text-sm text-ink-2">Page timeout (seconds)</label>
                  <input
                    v-model.number="config.camoufox_timeout"
                    type="number"
                    min="5"
                    max="120"
                    class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                  <p class="mt-1 text-xs text-ink-3">Time to wait for page to fully load.</p>
                </div>

                <div>
                  <label class="mb-1 block text-sm text-ink-2">Service URL</label>
                  <input
                    v-model="config.camoufox_url"
                    type="text"
                    placeholder="http://camoufox-browser:3392"
                    class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                  <p class="mt-1 text-xs text-ink-3">URL of the camoufox-browser container.</p>
                </div>
              </div>
            </div>

            <!-- Status check -->
            <div class="border-t border-line pt-5">
              <p class="mb-3 text-[12.5px] font-medium text-ink-2">Installation status</p>

              <div class="flex items-center gap-3">
                <button
                  class="rounded border border-line px-3 py-1.5 text-sm text-ink-2 hover:bg-surface-2 disabled:opacity-50"
                  :disabled="checkingCf"
                  @click="handleCfCheck"
                >
                  {{ checkingCf ? 'Checking…' : 'Check status' }}
                </button>

                <template v-if="cfStatus">
                  <span v-if="cfStatus.browser_ready" class="flex items-center gap-1.5 text-sm text-green-600">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-green-500" />
                    Ready
                  </span>
                  <span v-else-if="cfStatus.installed" class="flex items-center gap-1.5 text-sm text-amber-600">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
                    Installed, browser not downloaded
                  </span>
                  <span v-else class="flex items-center gap-1.5 text-sm text-danger">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-danger" />
                    Not installed
                  </span>
                </template>
              </div>

              <!-- Setup instructions -->
              <div v-if="cfStatus && !cfStatus.browser_ready" class="mt-4 rounded-lg border border-line bg-surface-2 px-4 py-3">
                <p class="mb-2 text-[12px] font-medium text-ink-2">Setup instructions</p>
                <ol class="space-y-1.5 text-[12px] text-ink-3">
                  <li>
                    <span class="mr-1 font-medium text-ink-2">1.</span>
                    Start the container:
                    <code class="ml-1 rounded bg-surface-3 px-1.5 py-0.5 font-mono text-[11px] text-ink">docker compose up camoufox-browser</code>
                  </li>
                  <li>
                    <span class="mr-1 font-medium text-ink-2">2.</span>
                    Set the service URL above and click <em>Check status</em> to verify.
                  </li>
                  <li>
                    <span class="mr-1 font-medium text-ink-2">3.</span>
                    Enable the toggle and save.
                  </li>
                </ol>
                <p v-if="cfStatus.message" class="mt-2 text-[11px] text-ink-3 font-mono">{{ cfStatus.message }}</p>
              </div>
            </div>
          </section>

          <!-- FlareSolverr ───────────────────────────────────────────────── -->
          <section v-else-if="activeSection === 'flaresolverr'" class="space-y-5">
            <div>
              <h2 class="mb-0.5 text-[15px] font-semibold text-ink">FlareSolverr</h2>
              <p class="text-[12.5px] text-ink-3">
                Cloudflare challenge solver fallback. Used automatically when Camoufox
                returns bot-challenge HTML or fails to extract content.
              </p>
            </div>

            <div class="space-y-4">
              <div>
                <label class="mb-1 block text-sm text-ink-2">Service URL</label>
                <input
                  v-model="config.flaresolverr_url"
                  type="text"
                  placeholder="http://flaresolverr:8191"
                  class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                />
                <p class="mt-1 text-xs text-ink-3">
                  URL of the FlareSolverr container. Leave empty to disable.
                </p>
              </div>
            </div>

            <!-- Status check -->
            <div class="border-t border-line pt-5">
              <p class="mb-3 text-[12.5px] font-medium text-ink-2">Service status</p>

              <div class="flex items-center gap-3">
                <button
                  class="rounded border border-line px-3 py-1.5 text-sm text-ink-2 hover:bg-surface-2 disabled:opacity-50"
                  :disabled="checkingFs"
                  @click="handleFsCheck"
                >
                  {{ checkingFs ? 'Checking…' : 'Check status' }}
                </button>

                <template v-if="fsStatus">
                  <span v-if="fsStatus.browser_ready" class="flex items-center gap-1.5 text-sm text-green-600">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-green-500" />
                    Ready
                  </span>
                  <span v-else-if="fsStatus.installed" class="flex items-center gap-1.5 text-sm text-amber-600">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
                    Installed, not ready
                  </span>
                  <span v-else class="flex items-center gap-1.5 text-sm text-danger">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-danger" />
                    Not installed
                  </span>
                </template>
              </div>

              <p v-if="fsStatus?.message" class="mt-2 text-[11px] text-ink-3 font-mono">{{ fsStatus.message }}</p>
            </div>
          </section>

          <!-- Browserless ─────────────────────────────────────────────────── -->
          <section v-else-if="activeSection === 'browserless'" class="space-y-5">
            <div>
              <h2 class="mb-0.5 text-[15px] font-semibold text-ink">Browserless.io</h2>
              <p class="text-[12.5px] text-ink-3">
                Optional remote-browser fallback. Used after Camoufox if local rendering
                fails or the page needs a real browser fingerprint. The free tier accepts
                a token; provide yours below — it is stored on the server and never sent
                back to the UI in plaintext.
              </p>
            </div>

            <!-- Enable toggle -->
            <div class="flex items-start gap-3 rounded-lg border border-line bg-surface-2 px-4 py-3.5">
              <div class="flex-1">
                <p class="text-[13px] font-medium text-ink">Enable Browserless fallback</p>
                <p class="mt-0.5 text-[12px] text-ink-3">
                  Required for the strategy to be used. Disabled when no token is configured.
                </p>
              </div>
              <button
                type="button"
                role="switch"
                :aria-checked="config.browserless_enabled"
                class="relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1"
                :class="config.browserless_enabled ? 'bg-accent' : 'bg-[var(--border)]'"
                @click="config.browserless_enabled = !config.browserless_enabled"
              >
                <span
                  class="absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-150"
                  :class="config.browserless_enabled ? 'translate-x-[18px]' : 'translate-x-0.5'"
                />
              </button>
            </div>

            <div
              class="space-y-4 transition-opacity duration-150"
              :class="config.browserless_enabled ? 'opacity-100' : 'opacity-40 pointer-events-none'"
            >
              <div>
                <label class="mb-1 block text-sm text-ink-2">API token</label>
                <div class="flex items-center gap-2">
                  <input
                    v-model="tokenInput"
                    type="password"
                    autocomplete="off"
                    :placeholder="config.browserless_token_set ? '•••••••• (saved — leave blank to keep)' : 'Paste your Browserless token'"
                    class="flex-1 rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                    @input="tokenClearRequested = false"
                  />
                  <button
                    v-if="config.browserless_token_set && !tokenClearRequested"
                    type="button"
                    class="rounded border border-line px-3 py-1.5 text-xs text-ink-2 hover:bg-surface-2"
                    @click="tokenClearRequested = true; tokenInput = ''"
                  >
                    Clear
                  </button>
                  <span
                    v-else-if="tokenClearRequested"
                    class="text-xs text-danger"
                  >Will clear on save</span>
                </div>
                <p class="mt-1 text-xs text-ink-3">
                  Get a token at <span class="font-mono">browserless.io</span> · the free tier is fine for low-volume imports.
                </p>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="mb-1 block text-sm text-ink-2">Endpoint</label>
                  <input
                    v-model="config.browserless_url"
                    type="text"
                    placeholder="https://production-sfo.browserless.io"
                    class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                  <p class="mt-1 text-xs text-ink-3">Override only if your account uses a different region.</p>
                </div>
                <div>
                  <label class="mb-1 block text-sm text-ink-2">Render timeout (s)</label>
                  <input
                    v-model.number="config.browserless_timeout"
                    type="number"
                    min="5"
                    max="120"
                    class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
              </div>
            </div>

            <!-- Status check -->
            <div class="border-t border-line pt-5">
              <p class="mb-3 text-[12.5px] font-medium text-ink-2">Service status</p>

              <div class="flex items-center gap-3">
                <button
                  class="rounded border border-line px-3 py-1.5 text-sm text-ink-2 hover:bg-surface-2 disabled:opacity-50"
                  :disabled="checkingBl"
                  @click="handleBlCheck"
                >
                  {{ checkingBl ? 'Checking…' : 'Check connection' }}
                </button>

                <template v-if="blStatus">
                  <span v-if="blStatus.reachable" class="flex items-center gap-1.5 text-sm text-green-600">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-green-500" />
                    Reachable
                  </span>
                  <span v-else-if="blStatus.configured" class="flex items-center gap-1.5 text-sm text-amber-600">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
                    Configured, not reachable
                  </span>
                  <span v-else class="flex items-center gap-1.5 text-sm text-danger">
                    <span class="inline-block h-1.5 w-1.5 rounded-full bg-danger" />
                    No token configured
                  </span>
                </template>
              </div>

              <p v-if="blStatus?.message" class="mt-2 text-[11px] text-ink-3 font-mono">{{ blStatus.message }}</p>
            </div>
          </section>

          <!-- Find more ──────────────────────────────────────────────────── -->
          <section v-else-if="activeSection === 'find-more'" class="space-y-5">
            <div>
              <h2 class="mb-0.5 text-[15px] font-semibold text-ink">Find more</h2>
              <p class="text-[12.5px] text-ink-3">
                Tune the discovery providers used by the topic-level <em>Find more</em>
                sidebar. Wikipedia, arXiv, Semantic Scholar, OpenAlex and Hacker News are
                always on. Optional sources and LM Studio enrichment are configured here.
              </p>
            </div>

            <div class="space-y-4">
              <div>
                <label class="mb-1 block text-sm text-ink-2">SearXNG instance URL</label>
                <input
                  v-model="config.suggest_searxng_url"
                  type="text"
                  placeholder="https://searx.example.org"
                  class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                />
                <p class="mt-1 text-xs text-ink-3">
                  Adds a metasearch provider for varied web sources. Leave empty to disable.
                  The instance must expose <code class="font-mono">/search?format=json</code>.
                </p>
              </div>

              <div class="flex items-start gap-3 rounded-lg border border-line bg-surface-2 px-4 py-3.5">
                <div class="flex-1">
                  <p class="text-[13px] font-medium text-ink">LM Studio query expansion</p>
                  <p class="mt-0.5 text-[12px] text-ink-3">
                    Let the local LLM invent 2–3 alternate search phrases from the topic
                    context to surface heterodox sources. Requires LM Studio configured.
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  :aria-checked="config.suggest_use_llm_expand"
                  class="relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1"
                  :class="config.suggest_use_llm_expand ? 'bg-accent' : 'bg-[var(--border)]'"
                  @click="config.suggest_use_llm_expand = !config.suggest_use_llm_expand"
                >
                  <span
                    class="absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-150"
                    :class="config.suggest_use_llm_expand ? 'translate-x-[18px]' : 'translate-x-0.5'"
                  />
                </button>
              </div>

              <div class="flex items-start gap-3 rounded-lg border border-line bg-surface-2 px-4 py-3.5">
                <div class="flex-1">
                  <p class="text-[13px] font-medium text-ink">LM Studio relevance reranker</p>
                  <p class="mt-0.5 text-[12px] text-ink-3">
                    After fast keyword ranking, ask the LLM to rescore the top candidates
                    against the topic. Slower but produces more coherent picks.
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  :aria-checked="config.suggest_use_llm_rerank"
                  class="relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1"
                  :class="config.suggest_use_llm_rerank ? 'bg-accent' : 'bg-[var(--border)]'"
                  @click="config.suggest_use_llm_rerank = !config.suggest_use_llm_rerank"
                >
                  <span
                    class="absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-150"
                    :class="config.suggest_use_llm_rerank ? 'translate-x-[18px]' : 'translate-x-0.5'"
                  />
                </button>
              </div>
            </div>
          </section>

          <!-- ── Save bar (always visible) ───────────────────────────────── -->
          <div class="mt-8 flex items-center gap-4 border-t border-line pt-5">
            <button
              class="rounded bg-accent px-4 py-2 text-sm text-white hover:bg-accent/90 disabled:opacity-50"
              :disabled="saving"
              @click="handleSave"
            >
              {{ saving ? 'Saving…' : 'Save changes' }}
            </button>
            <span v-if="success" class="text-sm text-green-600">Saved.</span>
            <span v-if="error" class="text-sm text-danger">{{ error }}</span>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>
