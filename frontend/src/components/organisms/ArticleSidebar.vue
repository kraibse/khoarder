<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import AppIcon from '@/components/atoms/AppIcon.vue'
import QAPanel from './QAPanel.vue'
import AssistPanel from '@/components/molecules/AssistPanel.vue'
import ColorPlaceholder from '@/components/molecules/ColorPlaceholder.vue'
import type { ArticleDetail, Backlink, RelatedEntry, SourceFile } from '@/data/mock'
import { uploadAttachment, attachmentDownloadUrl, getSuggestions, type RelatedEntryOut } from '@/api/entries'
import { addRelation, removeRelation } from '@/api/relations'
import { deleteEntry } from '@/api/entries'

const props = defineProps<{
  article: ArticleDetail
  backlinks: Backlink[]
  related: RelatedEntry[]
  sourceFiles: SourceFile[]
  entryId: string
}>()

const emit = defineEmits<{
  attached: []
  'edit-entry': []
  'related-changed': []
  'draft-extension': [text: string]
}>()

const router = useRouter()

// File upload
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const uploadError = ref('')

function triggerAttach() {
  fileInput.value?.click()
}

async function onAttachFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploadError.value = ''
  uploading.value = true
  try {
    await uploadAttachment(props.entryId, file)
    emit('attached')
  } catch (err) {
    uploadError.value = err instanceof Error ? err.message : 'Upload failed.'
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

// Delete entry
const deleteConfirm = ref(false)
const deleting = ref(false)

async function handleDelete() {
  if (!deleteConfirm.value) {
    deleteConfirm.value = true
    return
  }
  deleting.value = true
  try {
    await deleteEntry(props.entryId)
    router.back()
  } catch {
    deleteConfirm.value = false
    deleting.value = false
  }
}

// Related suggestions
const suggestions = ref<RelatedEntryOut[]>([])
const loadingSuggestions = ref(false)

async function loadSuggestions() {
  loadingSuggestions.value = true
  try {
    suggestions.value = await getSuggestions(props.entryId)
  } finally {
    loadingSuggestions.value = false
  }
}

async function linkAsRelated(suggestion: RelatedEntryOut) {
  await addRelation(props.entryId, suggestion.id, 'related')
  suggestions.value = suggestions.value.filter((s) => s.id !== suggestion.id)
  emit('related-changed')
}

async function handleRemoveRelated(relationId: string) {
  await removeRelation(relationId)
  emit('related-changed')
}

onMounted(loadSuggestions)
</script>

<template>
  <aside
    class="hidden lg:flex flex-col flex-shrink-0 border-l border-line overflow-y-auto bg-surface-2"
    style="width: 280px; min-width: 280px"
  >
    <!-- Actions -->
    <div class="border-b border-line px-[18px] py-[18px]">
      <div class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3 mb-[10px]">
        Actions
      </div>
      <div class="flex flex-col gap-[2px]">
        <button
          type="button"
          class="flex items-center gap-2 px-[10px] py-[7px] rounded-[7px] text-[12.5px]
                 text-ink-2 hover:bg-surface-3 hover:text-ink transition-colors duration-[120ms] text-left"
          @click="emit('edit-entry')"
        >
          <AppIcon name="edit" :size="13" class="flex-shrink-0" />
          Edit entry
        </button>
        <button
          type="button"
          :disabled="uploading"
          class="flex items-center gap-2 px-[10px] py-[7px] rounded-[7px] text-[12.5px]
                 text-ink-2 hover:bg-surface-3 hover:text-ink transition-colors duration-[120ms] text-left"
          @click="triggerAttach"
        >
          <AppIcon name="file" :size="13" class="flex-shrink-0" />
          {{ uploading ? 'Uploading…' : 'Attach file' }}
        </button>
        <button
          type="button"
          :disabled="deleting"
          class="flex items-center gap-2 px-[10px] py-[7px] rounded-[7px] text-[12.5px]
                 transition-colors duration-[120ms] text-left"
          :class="deleteConfirm
            ? 'text-red-600 bg-red-50 hover:bg-red-100'
            : 'text-danger hover:bg-[var(--danger-bg)]'"
          @click="handleDelete"
          @blur="deleteConfirm = false"
        >
          <AppIcon name="trash" :size="13" class="flex-shrink-0" />
          {{ deleteConfirm ? 'Click again to confirm' : 'Delete entry' }}
        </button>
      </div>
    </div>

    <!-- Backlinks -->
    <div class="border-b border-line px-[18px] py-[18px]">
      <div class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3 mb-[10px]">
        Backlinks · {{ backlinks.length }}
      </div>
      <p v-if="backlinks.length === 0" class="text-[11.5px] text-ink-3">
        No entries link to this one yet. Use <span class="font-mono">[[{{ article.title }}]]</span> in another entry.
      </p>
      <RouterLink
        v-for="(bl, i) in backlinks"
        :key="bl.id"
        :to="`/article/${bl.id}`"
        :class="['flex items-start gap-2 py-[7px] group', i < backlinks.length - 1 ? 'border-b border-line' : '']"
      >
        <div class="w-7 h-7 rounded-[6px] bg-surface-3 flex-shrink-0 flex items-center justify-center">
          <AppIcon name="book" :size="12" class="text-ink-3" />
        </div>
        <div>
          <div class="text-[12.5px] text-ink leading-[1.35] group-hover:text-accent transition-colors duration-[120ms]">
            {{ bl.title }}
          </div>
          <div class="text-[10.5px] text-ink-3 mt-0.5">
            {{ bl.type }} · {{ bl.refs }} reference{{ bl.refs !== 1 ? 's' : '' }}
          </div>
        </div>
      </RouterLink>
    </div>

    <!-- Related entries -->
    <div class="border-b border-line px-[18px] py-[18px]">
      <div class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3 mb-[10px]">
        Related
      </div>
      <div
        v-for="(r, i) in related"
        :key="r.id"
        :class="['flex gap-[9px] items-start py-[7px]', i < related.length - 1 ? 'border-b border-line' : '']"
      >
        <RouterLink :to="`/article/${r.id}`" class="flex gap-[9px] items-start flex-1 min-w-0 group">
          <div class="w-10 h-10 rounded-[6px] flex-shrink-0 overflow-hidden border border-line">
            <ColorPlaceholder :color="r.imgColor" height="40px" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-xs text-ink leading-[1.35] line-clamp-2 group-hover:text-accent transition-colors duration-[120ms]">
              {{ r.title }}
            </div>
            <div class="text-[10.5px] text-ink-3 mt-0.5">{{ r.type }}</div>
          </div>
        </RouterLink>
        <button
          type="button"
          class="flex-shrink-0 mt-1 text-ink-3 hover:text-danger transition-colors"
          title="Remove relation"
          @click="handleRemoveRelated(r.relationId)"
        >
          <AppIcon name="x" :size="12" />
        </button>
      </div>
    </div>

    <!-- Suggestions -->
    <div v-if="suggestions.length > 0" class="border-b border-line px-[18px] py-[18px]">
      <div class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3 mb-[10px]">
        Suggestions
      </div>
      <div
        v-for="(s, i) in suggestions"
        :key="s.id"
        :class="['flex items-center gap-2 py-[7px]', i < suggestions.length - 1 ? 'border-b border-line' : '']"
      >
        <div class="flex-1 min-w-0">
          <div class="text-[12px] text-ink truncate">{{ s.title }}</div>
          <div class="text-[10.5px] text-ink-3">{{ s.type }}</div>
        </div>
        <button
          type="button"
          class="flex-shrink-0 text-[10.5px] text-accent border border-accent/40 px-2 py-[3px]
                 rounded-[5px] hover:bg-accent hover:text-white transition-colors duration-[120ms]"
          @click="linkAsRelated(s)"
        >Link</button>
      </div>
    </div>

    <!-- Source files -->
    <div class="border-b border-line px-[18px] py-[18px]">
      <div class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3 mb-[10px]">
        Sources & Files
      </div>
      <div
        v-for="(file, i) in sourceFiles"
        :key="file.id"
        :class="['flex items-center gap-2 py-[7px] group', i < sourceFiles.length - 1 ? 'border-b border-line' : '']"
      >
        <div
          class="w-8 h-8 rounded-[6px] bg-surface-3 flex items-center justify-center flex-shrink-0
                 text-[9px] font-bold tracking-[0.04em] text-ink-3 border border-line"
        >
          {{ file.ext }}
        </div>
        <div class="flex-1 min-w-0">
          <a
            :href="attachmentDownloadUrl(file.id)"
            download
            class="block text-xs text-ink truncate group-hover:text-accent transition-colors duration-[120ms]"
          >
            {{ file.name }}
          </a>
          <div class="text-[10.5px] text-ink-3">{{ file.size }} · {{ file.date }}</div>
        </div>
      </div>

      <p v-if="uploadError" class="text-[11px] text-red-500 mt-2">{{ uploadError }}</p>

      <input ref="fileInput" type="file" class="hidden" @change="onAttachFile" />
      <button
        type="button"
        :disabled="uploading"
        class="mt-[10px] w-full py-[7px] rounded-[7px] border border-dashed border-line
               text-xs text-ink-3 hover:border-accent hover:text-accent
               transition-colors duration-[120ms] flex items-center justify-center gap-[5px]
               disabled:opacity-50 disabled:cursor-not-allowed"
        @click="triggerAttach"
      >
        <AppIcon name="file-plus" :size="12" />
        {{ uploading ? 'Uploading…' : 'Attach file' }}
      </button>
    </div>

    <!-- AI Assist -->
    <div class="border-b border-line">
      <AssistPanel
        :article="article"
        :entry-id="entryId"
        @tags-applied="emit('related-changed')"
        @related-linked="emit('related-changed')"
        @draft-extension="(text) => emit('draft-extension', text)"
      />
    </div>

    <!-- Q&A -->
    <QAPanel v-if="article.topicId" :topic-id="article.topicId" />
  </aside>
</template>
