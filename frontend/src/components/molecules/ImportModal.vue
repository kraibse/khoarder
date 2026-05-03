<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import { importTopic } from '@/api/topics'

const emit = defineEmits<{
  close: []
  imported: []
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const file = ref<File | null>(null)
const targetTopic = ref<string>('')
const importing = ref(false)
const error = ref<string | null>(null)

defineExpose({ fileInput })

function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    file.value = input.files[0]
    error.value = null
  }
}

async function handleImport() {
  if (!file.value) {
    error.value = 'Please select a JSON file.'
    return
  }
  importing.value = true
  error.value = null
  try {
    const text = await file.value.text()
    const data = JSON.parse(text)
    await importTopic(data, targetTopic.value || undefined)
    emit('imported')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Import failed'
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[100] flex items-center justify-center">
      <div class="absolute inset-0 bg-black/20" @click="$emit('close')" />
      <div
        class="relative w-full max-w-md rounded-lg border border-line bg-surface p-6 shadow-lg"
      >
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-lg font-semibold text-ink">Import Topic</h3>
          <button class="rounded p-1 hover:bg-surface-2" @click="$emit('close')">
            <AppIcon name="x" :size="18" />
          </button>
        </div>

        <div class="space-y-4">
          <div>
            <label class="mb-1 block text-sm text-ink-2">Topic JSON file</label>
            <input
              ref="fileInput"
              type="file"
              accept=".json"
              class="w-full cursor-pointer rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink file:mr-3 file:rounded file:border-0 file:bg-accent file:px-3 file:py-1 file:text-xs file:text-white hover:border-border-hover focus:outline-none"
              @change="handleFileChange"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm text-ink-2">Target topic slug (optional)</label>
            <input
              v-model="targetTopic"
              type="text"
              placeholder="my-topic"
              class="w-full rounded border border-line bg-surface-2 px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <p v-if="error" class="text-sm text-danger">{{ error }}</p>

          <div class="flex justify-end gap-2">
            <button
              class="rounded border border-line px-4 py-2 text-sm text-ink-2 hover:bg-surface-2"
              @click="$emit('close')"
            >
              Cancel
            </button>
            <button
              class="rounded bg-accent px-4 py-2 text-sm text-white hover:bg-accent/90 disabled:opacity-50"
              :disabled="importing"
              @click="handleImport"
            >
              {{ importing ? 'Importing...' : 'Import' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
