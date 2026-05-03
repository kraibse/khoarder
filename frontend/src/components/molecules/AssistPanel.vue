<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import { updateEntry } from '@/api/entries'
import { addRelation } from '@/api/relations'
import {
  assistSummarize,
  assistTags,
  assistRelated,
  assistExtend,
  type AssistRelatedEntry,
} from '@/api/qa'
import type { ArticleDetail } from '@/data/mock'

const props = defineProps<{
  article: ArticleDetail
  entryId: string
}>()

const emit = defineEmits<{
  'tags-applied': []
  'related-linked': []
  'draft-extension': [text: string]
}>()

// ── Summarize ─────────────────────────────────────────────────────────────────

const summary = ref('')
const summaryLoading = ref(false)
const summaryError = ref('')

async function runSummarize() {
  summaryError.value = ''
  summaryLoading.value = true
  try {
    const res = await assistSummarize(props.entryId)
    summary.value = res.summary
  } catch (e) {
    summaryError.value = e instanceof Error ? e.message : 'Error'
  } finally {
    summaryLoading.value = false
  }
}

// ── Tags ──────────────────────────────────────────────────────────────────────

const suggestedTags = ref<string[]>([])
const tagsLoading = ref(false)
const tagsError = ref('')
const appliedTags = ref<Set<string>>(new Set())

async function runSuggestTags() {
  tagsError.value = ''
  tagsLoading.value = true
  try {
    const res = await assistTags(props.entryId)
    suggestedTags.value = res.tags
    appliedTags.value = new Set()
  } catch (e) {
    tagsError.value = e instanceof Error ? e.message : 'Error'
  } finally {
    tagsLoading.value = false
  }
}

async function applyTag(tag: string) {
  const currentTags = props.article.tags ?? []
  if (currentTags.includes(tag)) { appliedTags.value.add(tag); return }
  const newTags = [...currentTags, tag]
  await updateEntry(props.entryId, { tags: newTags })
  props.article.tags = newTags
  appliedTags.value.add(tag)
  emit('tags-applied')
}

// ── Related ───────────────────────────────────────────────────────────────────

const suggestedRelated = ref<AssistRelatedEntry[]>([])
const relatedLoading = ref(false)
const relatedError = ref('')
const linkedIds = ref<Set<string>>(new Set())

async function runSuggestRelated() {
  relatedError.value = ''
  relatedLoading.value = true
  try {
    const res = await assistRelated(props.entryId)
    suggestedRelated.value = res.entries
    linkedIds.value = new Set()
  } catch (e) {
    relatedError.value = e instanceof Error ? e.message : 'Error'
  } finally {
    relatedLoading.value = false
  }
}

async function linkRelated(entry: AssistRelatedEntry) {
  await addRelation(props.entryId, entry.id, 'related')
  linkedIds.value.add(entry.id)
  emit('related-linked')
}

// ── Extend ────────────────────────────────────────────────────────────────────

const extendPrompt = ref('')
const extendLoading = ref(false)
const extendError = ref('')

async function runExtend() {
  extendError.value = ''
  extendLoading.value = true
  try {
    const res = await assistExtend(props.entryId, extendPrompt.value)
    emit('draft-extension', res.extension)
  } catch (e) {
    extendError.value = e instanceof Error ? e.message : 'Error'
  } finally {
    extendLoading.value = false
  }
}
</script>

<template>
  <div class="px-[18px] py-[18px]">
    <div class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3 mb-[12px]">
      AI Assist
    </div>

    <div class="flex flex-col gap-[14px]">

      <!-- Summarize -->
      <div>
        <button
          type="button"
          :disabled="summaryLoading"
          class="w-full flex items-center gap-[7px] px-[10px] py-[7px] rounded-[7px]
                 text-[12.5px] text-ink-2 hover:bg-surface-3 hover:text-ink
                 transition-colors duration-[120ms] text-left disabled:opacity-50"
          @click="runSummarize"
        >
          <AppIcon name="file" :size="13" class="flex-shrink-0 opacity-70" />
          {{ summaryLoading ? 'Summarizing…' : 'Summarize' }}
        </button>
        <div
          v-if="summary"
          class="mt-[6px] text-[12px] text-ink-2 bg-surface-2 border border-line
                 rounded-[7px] px-[10px] py-[8px] leading-[1.55]"
        >
          {{ summary }}
        </div>
        <p v-if="summaryError" class="mt-1 text-[11px] text-red-500">{{ summaryError }}</p>
      </div>

      <!-- Suggest tags -->
      <div>
        <button
          type="button"
          :disabled="tagsLoading"
          class="w-full flex items-center gap-[7px] px-[10px] py-[7px] rounded-[7px]
                 text-[12.5px] text-ink-2 hover:bg-surface-3 hover:text-ink
                 transition-colors duration-[120ms] text-left disabled:opacity-50"
          @click="runSuggestTags"
        >
          <AppIcon name="tag" :size="13" class="flex-shrink-0 opacity-70" />
          {{ tagsLoading ? 'Suggesting…' : 'Suggest tags' }}
        </button>
        <div v-if="suggestedTags.length" class="flex flex-wrap gap-[5px] mt-[6px]">
          <button
            v-for="tag in suggestedTags"
            :key="tag"
            type="button"
            :disabled="appliedTags.has(tag)"
            :class="[
              'text-[11px] px-[8px] py-[3px] rounded-full border transition-colors duration-[120ms]',
              appliedTags.has(tag)
                ? 'bg-accent/10 border-accent/30 text-accent opacity-60 cursor-default'
                : 'bg-surface border-line text-ink-3 hover:border-accent hover:text-accent cursor-pointer',
            ]"
            @click="applyTag(tag)"
          >
            {{ appliedTags.has(tag) ? '✓ ' : '+ ' }}{{ tag }}
          </button>
        </div>
        <p v-if="tagsError" class="mt-1 text-[11px] text-red-500">{{ tagsError }}</p>
      </div>

      <!-- Suggest related -->
      <div>
        <button
          type="button"
          :disabled="relatedLoading"
          class="w-full flex items-center gap-[7px] px-[10px] py-[7px] rounded-[7px]
                 text-[12.5px] text-ink-2 hover:bg-surface-3 hover:text-ink
                 transition-colors duration-[120ms] text-left disabled:opacity-50"
          @click="runSuggestRelated"
        >
          <AppIcon name="link" :size="13" class="flex-shrink-0 opacity-70" />
          {{ relatedLoading ? 'Searching…' : 'Suggest related' }}
        </button>
        <div v-if="suggestedRelated.length" class="flex flex-col gap-[4px] mt-[6px]">
          <div
            v-for="entry in suggestedRelated"
            :key="entry.id"
            class="flex items-center gap-2 px-[8px] py-[6px] rounded-[7px]
                   bg-surface-2 border border-line text-[12px]"
          >
            <span class="flex-1 text-ink-2 truncate">{{ entry.title }}</span>
            <span class="text-[10px] text-ink-3 flex-shrink-0">{{ entry.type }}</span>
            <button
              type="button"
              :disabled="linkedIds.has(entry.id)"
              :class="[
                'flex-shrink-0 text-[10.5px] border px-[7px] py-[2px] rounded-[5px]',
                'transition-colors duration-[120ms]',
                linkedIds.has(entry.id)
                  ? 'text-accent border-accent/30 opacity-60 cursor-default'
                  : 'text-accent border-accent/40 hover:bg-accent hover:text-white',
              ]"
              @click="linkRelated(entry)"
            >
              {{ linkedIds.has(entry.id) ? 'Linked' : 'Link' }}
            </button>
          </div>
        </div>
        <p v-if="relatedError" class="mt-1 text-[11px] text-red-500">{{ relatedError }}</p>
      </div>

      <!-- Draft extension -->
      <div>
        <p class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3 mb-[6px]">
          Draft extension
        </p>
        <textarea
          v-model="extendPrompt"
          rows="2"
          placeholder="Optional direction (e.g. 'focus on practical applications')"
          class="w-full text-[12px] px-[10px] py-[7px] rounded-[7px] border border-line
                 bg-surface text-ink placeholder:text-ink-3 outline-none resize-none
                 focus:border-accent transition-colors duration-[120ms] mb-[6px]"
        />
        <button
          type="button"
          :disabled="extendLoading"
          class="w-full py-[7px] rounded-[7px] bg-accent text-white text-[12.5px]
                 hover:opacity-90 transition-opacity disabled:opacity-50"
          @click="runExtend"
        >
          {{ extendLoading ? 'Drafting…' : 'Draft extension' }}
        </button>
        <p v-if="extendError" class="mt-1 text-[11px] text-red-500">{{ extendError }}</p>
      </div>

    </div>
  </div>
</template>
