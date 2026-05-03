<script setup lang="ts">
import { ref, computed } from 'vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import { useTopicsStore } from '@/stores/topics'
import { createEntry, importUrl, uploadAttachment } from '@/api/entries'

const emit = defineEmits<{
  close: []
  created: []
}>()

const topicsStore = useTopicsStore()
const topicId = computed(() => topicsStore.activeTopicId)
const navIds = ['home', 'inbox', 'all', 'starred']
const selectedTopicId = ref<string | null>(
  navIds.includes(topicsStore.activeTopicId) ? null : topicsStore.activeTopicId
)

function getTopicId() {
  return selectedTopicId.value
}

type Mode = 'url' | 'note' | 'file' | null
const mode = ref<Mode>(null)
const loading = ref(false)
const error = ref('')

// URL mode
const urlInput = ref('')

// Note mode
const noteTitle = ref('')
const noteBody = ref('')
const noteTags = ref('')

// File mode
const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const fileTitle = ref('')

function pickFile() {
  fileInput.value?.click()
}

function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  selectedFile.value = f
  fileTitle.value = f.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ')
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const tId = getTopicId()
    if (mode.value === 'url') {
      if (!urlInput.value.trim()) { error.value = 'Please enter a URL.'; return }
      await importUrl(tId, urlInput.value.trim())
    } else if (mode.value === 'note') {
      if (!noteTitle.value.trim()) { error.value = 'Title is required.'; return }
      await createEntry({
        topic_id: tId,
        type: 'Note',
        title: noteTitle.value.trim(),
        body: noteBody.value,
        tags: noteTags.value.split(',').map((t) => t.trim()).filter(Boolean),
      })
    } else if (mode.value === 'file') {
      if (!selectedFile.value) { error.value = 'Please choose a file.'; return }
      const entry = await createEntry({
        topic_id: tId,
        type: 'Reference',
        title: fileTitle.value.trim() || selectedFile.value.name,
      })
      await uploadAttachment(entry.id, selectedFile.value)
    }
    emit('created')
    emit('close')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Something went wrong.'
  } finally {
    loading.value = false
  }
}

const modes: Array<{ id: 'url' | 'note' | 'file'; label: string; sub: string; icon: string }> = [
  { id: 'url', label: 'Paste URL', sub: 'Import from web', icon: 'link' },
  { id: 'note', label: 'Write Note', sub: 'Start from scratch', icon: 'edit' },
  { id: 'file', label: 'Upload File', sub: 'PDF, EPUB, image', icon: 'file' },
]
</script>

<template>
  <Teleport to="body">
    <Transition name="fade" appear>
      <div
        class="fixed inset-0 z-[200] flex items-center justify-center"
        style="background: oklch(16% 0.01 60 / 0.35)"
        @click.self="emit('close')"
      >
        <div class="bg-surface border border-line rounded-[14px] p-7 w-[480px] max-w-[90vw] shadow-modal">

          <!-- Mode picker -->
          <template v-if="!mode">
            <h2 class="font-serif text-[20px] mb-5">Add to topic</h2>
            <div class="grid grid-cols-3 gap-[10px]">
              <button
                v-for="m in modes"
                :key="m.id"
                type="button"
                class="bg-surface-2 border border-line rounded-[10px] p-4 text-left cursor-pointer
                       transition-colors duration-[120ms] hover:border-accent flex flex-col gap-1"
                @click="mode = m.id"
              >
                <AppIcon :name="m.icon" :size="16" class="text-ink-2 mb-[2px]" />
                <span class="text-[13px] font-medium text-ink">{{ m.label }}</span>
                <span class="text-[11.5px] text-ink-3">{{ m.sub }}</span>
              </button>
            </div>
            <button
              type="button"
              class="mt-[18px] w-full py-[9px] rounded-lg border border-line
                     text-[13px] text-ink-3 hover:bg-surface-2 transition-colors"
              @click="emit('close')"
            >
              Cancel
            </button>
          </template>

          <!-- URL form -->
          <template v-else-if="mode === 'url'">
            <button type="button" class="text-xs text-ink-3 mb-4 hover:text-ink" @click="mode = null">
              ← Back
            </button>
            <h2 class="font-serif text-[20px] mb-4">Import from URL</h2>
            <select
              v-model="selectedTopicId"
              class="w-full h-9 px-3 border border-line rounded-[8px] bg-surface-2 text-[13px] text-ink outline-none focus:border-accent mb-3"
            >
              <option :value="null">Auto-categorize</option>
              <option v-for="t in topicsStore.topics" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
            <input
              v-model="urlInput"
              type="url"
              placeholder="https://example.com/article"
              class="w-full h-10 px-3 border border-line rounded-[8px] bg-surface-2
                     text-[13px] text-ink placeholder:text-ink-3 outline-none focus:border-accent mb-3"
              autofocus
              @keydown.enter="submit"
            />
            <p class="text-[11.5px] text-ink-3 mb-4">Title and excerpt will be extracted from the page.</p>
            <div v-if="error" class="text-[12px] text-red-500 mb-3">{{ error }}</div>
            <div class="flex gap-2">
              <button type="button" class="flex-1 py-[9px] rounded-lg border border-line text-[13px] text-ink-3 hover:bg-surface-2" @click="emit('close')">Cancel</button>
              <button type="button" :disabled="loading" class="flex-1 py-[9px] rounded-lg bg-accent text-[13px] text-white disabled:opacity-50" @click="submit">
                {{ loading ? 'Importing…' : 'Import' }}
              </button>
            </div>
          </template>

          <!-- Note form -->
          <template v-else-if="mode === 'note'">
            <button type="button" class="text-xs text-ink-3 mb-4 hover:text-ink" @click="mode = null">
              ← Back
            </button>
            <h2 class="font-serif text-[20px] mb-4">Write a note</h2>
            <select
              v-model="selectedTopicId"
              class="w-full h-9 px-3 border border-line rounded-[8px] bg-surface-2 text-[13px] text-ink outline-none focus:border-accent mb-3"
            >
              <option :value="null">Auto-categorize</option>
              <option v-for="t in topicsStore.topics" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
            <input
              v-model="noteTitle"
              type="text"
              placeholder="Title"
              class="w-full h-10 px-3 border border-line rounded-[8px] bg-surface-2
                     text-[13px] text-ink placeholder:text-ink-3 outline-none focus:border-accent mb-2"
              autofocus
            />
            <textarea
              v-model="noteBody"
              placeholder="Body (optional)"
              rows="5"
              class="w-full px-3 py-2 border border-line rounded-[8px] bg-surface-2
                     text-[13px] text-ink placeholder:text-ink-3 outline-none focus:border-accent
                     resize-none mb-2"
            />
            <input
              v-model="noteTags"
              type="text"
              placeholder="Tags (comma-separated)"
              class="w-full h-9 px-3 border border-line rounded-[8px] bg-surface-2
                     text-[12px] text-ink placeholder:text-ink-3 outline-none focus:border-accent mb-3"
            />
            <div v-if="error" class="text-[12px] text-red-500 mb-3">{{ error }}</div>
            <div class="flex gap-2">
              <button type="button" class="flex-1 py-[9px] rounded-lg border border-line text-[13px] text-ink-3 hover:bg-surface-2" @click="emit('close')">Cancel</button>
              <button type="button" :disabled="loading" class="flex-1 py-[9px] rounded-lg bg-accent text-[13px] text-white disabled:opacity-50" @click="submit">
                {{ loading ? 'Saving…' : 'Save note' }}
              </button>
            </div>
          </template>

          <!-- File form -->
          <template v-else-if="mode === 'file'">
            <button type="button" class="text-xs text-ink-3 mb-4 hover:text-ink" @click="mode = null">
              ← Back
            </button>
            <h2 class="font-serif text-[20px] mb-4">Upload a file</h2>
            <select
              v-model="selectedTopicId"
              class="w-full h-9 px-3 border border-line rounded-[8px] bg-surface-2 text-[13px] text-ink outline-none focus:border-accent mb-3"
            >
              <option :value="null">Auto-categorize</option>
              <option v-for="t in topicsStore.topics" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
            <input ref="fileInput" type="file" class="hidden" @change="onFileChange" />
            <div
              class="border-2 border-dashed border-line rounded-[10px] p-6 text-center cursor-pointer
                     hover:border-accent transition-colors mb-3"
              @click="pickFile"
            >
              <AppIcon name="upload" :size="20" class="text-ink-3 mx-auto mb-2" />
              <p class="text-[13px] text-ink-2">
                {{ selectedFile ? selectedFile.name : 'Click to choose a file' }}
              </p>
              <p v-if="selectedFile" class="text-[11px] text-ink-3 mt-1">
                {{ (selectedFile.size / 1024).toFixed(0) }} KB
              </p>
            </div>
            <input
              v-model="fileTitle"
              type="text"
              placeholder="Title (optional, defaults to filename)"
              class="w-full h-9 px-3 border border-line rounded-[8px] bg-surface-2
                     text-[12px] text-ink placeholder:text-ink-3 outline-none focus:border-accent mb-3"
            />
            <div v-if="error" class="text-[12px] text-red-500 mb-3">{{ error }}</div>
            <div class="flex gap-2">
              <button type="button" class="flex-1 py-[9px] rounded-lg border border-line text-[13px] text-ink-3 hover:bg-surface-2" @click="emit('close')">Cancel</button>
              <button type="button" :disabled="loading" class="flex-1 py-[9px] rounded-lg bg-accent text-[13px] text-white disabled:opacity-50" @click="submit">
                {{ loading ? 'Uploading…' : 'Upload' }}
              </button>
            </div>
          </template>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>
