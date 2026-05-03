<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import type { ArticleDetail } from '@/data/mock'
import { updateEntry } from '@/api/entries'

const props = defineProps<{ entry: ArticleDetail }>()
const emit = defineEmits<{ close: []; saved: [] }>()

const ENTRY_TYPES = ['Article', 'Note', 'Paper', 'Excerpt', 'Reference'] as const

const title = ref('')
const type = ref('')
const body = ref('')
const excerpt = ref('')
const tags = ref('')
const sourceUrl = ref('')
const imgUrl = ref('')
const loading = ref(false)
const error = ref('')

watchEffect(() => {
  title.value = props.entry.title
  type.value = props.entry.type
  body.value = props.entry.body ?? ''
  excerpt.value = props.entry.excerpt ?? ''
  tags.value = (props.entry.tags ?? []).join(', ')
  sourceUrl.value = (props.entry as any).sourceUrl ?? ''
  imgUrl.value = props.entry.imgUrl ?? ''
})

async function submit() {
  if (!title.value.trim()) { error.value = 'Title is required.'; return }
  error.value = ''
  loading.value = true
  try {
    await updateEntry(props.entry.id, {
      title: title.value.trim(),
      type: type.value,
      body: body.value,
      excerpt: excerpt.value,
      tags: tags.value.split(',').map((t) => t.trim()).filter(Boolean),
      source_url: sourceUrl.value.trim() || null,
      img_url: imgUrl.value.trim() || null,
    })
    emit('saved')
    emit('close')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Something went wrong.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade" appear>
      <div
        class="fixed inset-0 z-[200] flex items-center justify-center"
        style="background: oklch(16% 0.01 60 / 0.35)"
        @click.self="emit('close')"
      >
        <div class="bg-surface border border-line rounded-[14px] p-7 w-[580px] max-w-[90vw] shadow-modal
                    flex flex-col max-h-[90vh]">
          <h2 class="font-serif text-[20px] mb-5 flex-shrink-0">Edit entry</h2>

          <div class="overflow-y-auto flex-1 pr-1">
            <label class="block text-[11.5px] text-ink-3 mb-1">Title</label>
            <input
              v-model="title"
              type="text"
              autofocus
              class="w-full h-10 px-3 border border-line rounded-[8px] bg-surface-2
                     text-[13px] text-ink placeholder:text-ink-3 outline-none focus:border-accent mb-3"
            />

            <div class="flex gap-3 mb-3">
              <div class="flex-1">
                <label class="block text-[11.5px] text-ink-3 mb-1">Type</label>
                <select
                  v-model="type"
                  class="w-full h-9 px-2 border border-line rounded-[8px] bg-surface-2
                         text-[13px] text-ink outline-none focus:border-accent"
                >
                  <option v-for="t in ENTRY_TYPES" :key="t" :value="t">{{ t }}</option>
                </select>
              </div>
              <div class="flex-1">
                <label class="block text-[11.5px] text-ink-3 mb-1">Tags (comma-separated)</label>
                <input
                  v-model="tags"
                  type="text"
                  placeholder="cognition, memory"
                  class="w-full h-9 px-3 border border-line rounded-[8px] bg-surface-2
                         text-[12px] text-ink placeholder:text-ink-3 outline-none focus:border-accent"
                />
              </div>
            </div>

            <label class="block text-[11.5px] text-ink-3 mb-1">
              Body
              <span class="ml-1 text-ink-3 font-normal">(Markdown — use [[Title]] to link entries)</span>
            </label>
            <textarea
              v-model="body"
              rows="12"
              class="w-full px-3 py-2 border border-line rounded-[8px] bg-surface-2
                     text-[12.5px] font-mono text-ink placeholder:text-ink-3 outline-none
                     focus:border-accent resize-y mb-3"
              placeholder="Write your content here…"
            />

            <label class="block text-[11.5px] text-ink-3 mb-1">Excerpt (optional)</label>
            <textarea
              v-model="excerpt"
              rows="2"
              class="w-full px-3 py-2 border border-line rounded-[8px] bg-surface-2
                     text-[13px] text-ink placeholder:text-ink-3 outline-none focus:border-accent
                     resize-none mb-3"
              placeholder="Short summary shown on cards"
            />

            <label class="block text-[11.5px] text-ink-3 mb-1">Source URL (optional)</label>
            <input
              v-model="sourceUrl"
              type="url"
              class="w-full h-9 px-3 border border-line rounded-[8px] bg-surface-2
                     text-[12px] text-ink placeholder:text-ink-3 outline-none focus:border-accent mb-3"
              placeholder="https://…"
            />

            <label class="block text-[11.5px] text-ink-3 mb-1">Hero Image URL (optional)</label>
            <input
              v-model="imgUrl"
              type="url"
              class="w-full h-9 px-3 border border-line rounded-[8px] bg-surface-2
                     text-[12px] text-ink placeholder:text-ink-3 outline-none focus:border-accent mb-1"
              placeholder="https://…"
            />
          </div>

          <div v-if="error" class="text-[12px] text-red-500 mt-3">{{ error }}</div>
          <div class="flex gap-2 mt-4 flex-shrink-0">
            <button
              type="button"
              class="flex-1 py-[9px] rounded-lg border border-line text-[13px] text-ink-3 hover:bg-surface-2"
              @click="emit('close')"
            >Cancel</button>
            <button
              type="button"
              :disabled="loading"
              class="flex-1 py-[9px] rounded-lg bg-accent text-[13px] text-white disabled:opacity-50"
              @click="submit"
            >{{ loading ? 'Saving…' : 'Save changes' }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
