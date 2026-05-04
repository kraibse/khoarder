<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import TopicSuggestModal from '@/components/molecules/TopicSuggestModal.vue'
import { useTopicsStore } from '@/stores/topics'
import { createEntry, uploadAttachment, previewTopic, previewImportUrl } from '@/api/entries'
import type { TopicSuggestionOut, URLPreviewOut } from '@/api/entries'

const emit = defineEmits<{
  close: []
  created: []
}>()

const topicsStore = useTopicsStore()
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
const urlExtracted = ref<URLPreviewOut | null>(null)
const showUrlPaste = ref(false)
const manualBody = ref('')

// Note mode
const noteTitle = ref('')
const noteBody = ref('')
const noteTags = ref('')

// File mode
const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const fileTitle = ref('')

// Topic suggestion modal state
const showTopicModal = ref(false)
const pendingSuggestion = ref<TopicSuggestionOut | null>(null)
const pendingFeedback = ref('')
const pendingAction = ref<{ mode: Mode; data: unknown } | null>(null)

function pickFile() {
  fileInput.value?.click()
}

function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  selectedFile.value = f
  fileTitle.value = f.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ')
}

function resetUrlPaste() {
  showUrlPaste.value = false
  urlExtracted.value = null
  manualBody.value = ''
  pendingSuggestion.value = null
  pendingAction.value = null
}

async function submit() {
  error.value = ''

  if (mode.value === 'url') {
    if (!urlInput.value.trim()) { error.value = 'Please enter a URL.'; return }
    loading.value = true
    try {
      // Always preview first — checks extraction quality and fetches topic suggestion
      const preview = await previewImportUrl(getTopicId(), urlInput.value.trim())
      urlExtracted.value = preview

      if (preview.partial) {
        // Extraction incomplete — show paste fallback step
        showUrlPaste.value = true
        return
      }

      // Full extraction — proceed to topic flow or direct create
      await _afterUrlPreview(preview)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Something went wrong.'
    } finally {
      loading.value = false
    }
    return
  }

  // Note / file modes
  const tId = getTopicId()
  if (tId !== null) {
    await doCreate(tId)
    return
  }

  loading.value = true
  try {
    if (mode.value === 'note') {
      if (!noteTitle.value.trim()) { error.value = 'Title is required.'; return }
      const suggestion = await previewTopic({
        title: noteTitle.value.trim(),
        excerpt: '',
        body: noteBody.value,
      })
      pendingSuggestion.value = suggestion
      pendingAction.value = { mode: 'note', data: { title: noteTitle.value.trim(), body: noteBody.value, tags: noteTags.value } }
      showTopicModal.value = true
    } else if (mode.value === 'file') {
      await doCreate(null)
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Something went wrong.'
  } finally {
    loading.value = false
  }
}

async function _afterUrlPreview(preview: URLPreviewOut) {
  if (!getTopicId() && preview.suggestion) {
    // Auto-categorize — show topic suggestion modal
    pendingSuggestion.value = preview.suggestion
    pendingAction.value = {
      mode: 'url',
      data: { url: urlInput.value.trim(), preview },
    }
    showTopicModal.value = true
  } else {
    await doCreate(getTopicId())
  }
}

async function proceedFromPaste() {
  // Called when user clicks either button in the paste fallback step
  showUrlPaste.value = false
  loading.value = true
  error.value = ''
  try {
    const preview = urlExtracted.value!
    // Use pasted content if provided, otherwise use whatever was extracted
    const effectiveBody = manualBody.value.trim() || preview.body
    const enrichedPreview = { ...preview, body: effectiveBody }

    if (!getTopicId() && preview.suggestion) {
      pendingSuggestion.value = preview.suggestion
      pendingAction.value = {
        mode: 'url',
        data: { url: urlInput.value.trim(), preview: enrichedPreview },
      }
      showTopicModal.value = true
    } else {
      await doCreate(getTopicId())
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Something went wrong.'
  } finally {
    loading.value = false
  }
}

async function doCreate(topicIdOverride: string | null) {
  loading.value = true
  error.value = ''
  try {
    if (mode.value === 'url') {
      const preview = urlExtracted.value!
      const body = manualBody.value.trim() || preview.body
      await createEntry({
        topic_id: topicIdOverride,
        type: body.length > 200 ? 'Article' : 'Reference',
        title: preview.title,
        excerpt: preview.excerpt,
        body,
        source_url: urlInput.value.trim(),
        has_img: preview.has_img,
        img_url: preview.img_url ?? undefined,
        topic_suggestion: pendingSuggestion.value ?? undefined,
      })
    } else if (mode.value === 'note') {
      await createEntry({
        topic_id: topicIdOverride,
        type: 'Note',
        title: noteTitle.value.trim(),
        body: noteBody.value,
        tags: noteTags.value.split(',').map((t) => t.trim()).filter(Boolean),
        topic_suggestion: pendingSuggestion.value || undefined,
      })
    } else if (mode.value === 'file') {
      if (!selectedFile.value) { error.value = 'Please choose a file.'; return }
      const entry = await createEntry({
        topic_id: topicIdOverride,
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

async function onApproveSuggestion() {
  showTopicModal.value = false
  await doCreate(null)
}

async function onRegenerateSuggestion(feedback: string) {
  pendingFeedback.value = feedback
  loading.value = true
  try {
    let newSuggestion: TopicSuggestionOut
    if (pendingAction.value?.mode === 'url') {
      const data = pendingAction.value.data as { url: string; preview: { title: string; excerpt: string; body: string } }
      newSuggestion = await previewTopic({
        title: data.preview.title,
        excerpt: data.preview.excerpt,
        body: data.preview.body,
        feedback,
      })
    } else if (pendingAction.value?.mode === 'note') {
      const data = pendingAction.value.data as { title: string; body: string }
      newSuggestion = await previewTopic({
        title: data.title,
        body: data.body,
        feedback,
      })
    } else {
      return
    }
    pendingSuggestion.value = newSuggestion
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Regeneration failed.'
  } finally {
    loading.value = false
  }
}

function onCancelSuggestion() {
  showTopicModal.value = false
  pendingSuggestion.value = null
  pendingAction.value = null
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
          <template v-else-if="mode === 'url' && !showUrlPaste">
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
                {{ loading ? 'Fetching…' : 'Import' }}
              </button>
            </div>
          </template>

          <!-- URL paste fallback (shown when extraction was partial) -->
          <template v-else-if="mode === 'url' && showUrlPaste">
            <button type="button" class="text-xs text-ink-3 mb-4 hover:text-ink" @click="resetUrlPaste">
              ← Back
            </button>
            <h2 class="font-serif text-[20px] mb-3">Content not available</h2>

            <!-- Status banner -->
            <div class="flex items-start gap-2 px-3 py-2.5 bg-amber-50 border border-amber-200 rounded-[8px] mb-4">
              <AppIcon name="alert" :size="14" class="text-amber-600 mt-[1px] shrink-0" />
              <div>
                <p class="text-[12px] font-medium text-amber-800 leading-snug">Article content couldn't be extracted</p>
                <p class="text-[11.5px] text-amber-700 mt-0.5 leading-snug">
                  This happens with sites that use JavaScript rendering, bot protection (Cloudflare), or paywalls.
                  We saved the title and description.
                </p>
              </div>
            </div>

            <!-- Extracted title preview -->
            <p class="text-[11px] uppercase tracking-wide text-ink-3 mb-1">Found</p>
            <p class="text-[13px] font-medium text-ink mb-4 truncate">{{ urlExtracted?.title }}</p>

            <!-- Manual paste area -->
            <label class="block text-[11px] uppercase tracking-wide text-ink-3 mb-1.5">
              Paste article text <span class="normal-case text-ink-3">(optional)</span>
            </label>
            <textarea
              v-model="manualBody"
              placeholder="Open the article in your browser, select all (Ctrl+A / ⌘A), copy, and paste here."
              rows="7"
              class="w-full px-3 py-2 border border-line rounded-[8px] bg-surface-2
                     text-[12.5px] text-ink placeholder:text-ink-3 outline-none focus:border-accent
                     resize-none mb-4 leading-relaxed"
            />

            <div v-if="error" class="text-[12px] text-red-500 mb-3">{{ error }}</div>

            <div class="flex gap-2">
              <button
                type="button"
                :disabled="loading"
                class="flex-1 py-[9px] rounded-lg border border-line text-[13px] text-ink-3
                       hover:bg-surface-2 disabled:opacity-50 transition-colors"
                @click="manualBody = ''; proceedFromPaste()"
              >
                Save as Reference
              </button>
              <button
                type="button"
                :disabled="loading"
                class="flex-1 py-[9px] rounded-lg bg-accent text-[13px] text-white
                       disabled:opacity-50 transition-colors"
                @click="proceedFromPaste()"
              >
                {{ loading ? 'Saving…' : 'Import' + (manualBody.trim() ? ' with content' : '') }}
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

  <!-- Topic suggestion modal -->
  <TopicSuggestModal
    v-if="showTopicModal && pendingSuggestion"
    :suggestion="pendingSuggestion"
    :loading="loading"
    @approve="onApproveSuggestion"
    @regenerate="onRegenerateSuggestion"
    @cancel="onCancelSuggestion"
  />
</template>
