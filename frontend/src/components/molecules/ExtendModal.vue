<script setup lang="ts">
import { ref } from 'vue'
import { updateEntry } from '@/api/entries'

const props = defineProps<{ entryId: string; currentBody: string; prefill?: string }>()
const emit = defineEmits<{ close: []; extended: [] }>()

const extension = ref(props.prefill ?? '')
const loading = ref(false)
const error = ref('')

async function submit() {
  if (!extension.value.trim()) { error.value = 'Please write something.'; return }
  error.value = ''
  loading.value = true
  try {
    const separator = props.currentBody.trim() ? '\n\n---\n\n' : ''
    await updateEntry(props.entryId, {
      body: props.currentBody + separator + extension.value.trim(),
    })
    emit('extended')
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
        <div class="bg-surface border border-line rounded-[14px] p-7 w-[560px] max-w-[90vw] shadow-modal">
          <h2 class="font-serif text-[20px] mb-1">Extend this entry</h2>
          <p class="text-[12px] text-ink-3 mb-5">
            Your text will be appended after the existing content.
            Markdown and <span class="font-mono">[[Title]]</span> links are supported.
          </p>

          <textarea
            v-model="extension"
            rows="10"
            autofocus
            class="w-full px-3 py-2 border border-line rounded-[8px] bg-surface-2
                   text-[12.5px] font-mono text-ink placeholder:text-ink-3 outline-none
                   focus:border-accent resize-y mb-3"
            placeholder="Continue your thoughts here…"
          />

          <div v-if="error" class="text-[12px] text-red-500 mb-3">{{ error }}</div>
          <div class="flex gap-2">
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
            >{{ loading ? 'Saving…' : 'Append extension' }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
