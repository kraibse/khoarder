<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/atoms/AppIcon.vue'
import { getConfig, updateConfig, checkHealth, type ConfigOut, type HealthOut } from '@/api/config'

const router = useRouter()
const config = ref<ConfigOut | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const success = ref(false)

const health = ref<HealthOut | null>(null)
const checkingHealth = ref(false)

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
    await updateConfig({
      llm_base_url: config.value.llm_base_url,
      llm_model: config.value.llm_model,
      llm_timeout: config.value.llm_timeout,
      llm_context_entries: config.value.llm_context_entries,
      system_prompt: config.value.system_prompt,
      auto_tag_count: config.value.auto_tag_count,
    })
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
</script>

<template>
  <div class="min-h-screen bg-surface">
    <div class="mx-auto max-w-2xl px-6 py-8">
      <button
        class="mb-6 flex items-center gap-2 text-sm text-ink-2 hover:text-ink"
        @click="router.push('/')"
      >
        <AppIcon name="arrow-left" :size="16" />
        Back
      </button>

      <h1 class="mb-8 text-2xl font-semibold text-ink">Settings</h1>

      <div v-if="loading" class="text-sm text-ink-2">Loading...</div>

      <div v-else-if="!config" class="rounded border border-danger bg-[var(--danger-bg)] p-4 text-sm text-danger">
        {{ error }}
      </div>

      <div v-else class="space-y-8">
        <section>
          <h2 class="mb-4 text-sm font-medium uppercase tracking-wide text-ink-3">LM Studio</h2>
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
                <label class="mb-1 block text-sm text-ink-2">Timeout (seconds)</label>
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
                <p class="mt-1 text-xs text-ink-3">Tags per new entry (0 to disable)</p>
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

        <section>
          <h2 class="mb-4 text-sm font-medium uppercase tracking-wide text-ink-3">Extension Drafting</h2>
          <div>
            <label class="mb-1 block text-sm text-ink-2">System prompt</label>
            <textarea
              v-model="config.system_prompt"
              rows="6"
              placeholder="You are a knowledge-base writing assistant..."
              class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:ring-1 focus:ring-accent resize-none"
            />
            <p class="mt-1 text-xs text-ink-3">
              Custom instructions for the AI when drafting extensions. Leave empty to use the default prompt.
            </p>
          </div>
        </section>

        <div class="flex items-center gap-4 pt-4 border-t border-line">
          <button
            class="rounded bg-accent px-4 py-2 text-sm text-white hover:bg-accent/90 disabled:opacity-50"
            :disabled="saving"
            @click="handleSave"
          >
            {{ saving ? 'Saving...' : 'Save changes' }}
          </button>
          <span v-if="success" class="text-sm text-green-600">Saved.</span>
          <span v-if="error" class="text-sm text-danger">{{ error }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
