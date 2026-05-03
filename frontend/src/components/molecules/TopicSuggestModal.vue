<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import type { TopicSuggestionOut } from '@/api/entries'

const props = defineProps<{
  suggestion: TopicSuggestionOut
  loading: boolean
}>()

const emit = defineEmits<{
  approve: []
  regenerate: [feedback: string]
  cancel: []
}>()

const feedback = ref('')
const showFeedback = ref(false)

function onRegenerate() {
  if (!showFeedback.value) {
    showFeedback.value = true
    return
  }
  emit('regenerate', feedback.value.trim())
}

function onApprove() {
  emit('approve')
}

function onCancel() {
  emit('cancel')
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade" appear>
      <div
        class="fixed inset-0 z-[210] flex items-center justify-center"
        style="background: oklch(16% 0.01 60 / 0.35)"
        @click.self="onCancel"
      >
        <div class="bg-surface border border-line rounded-[14px] p-7 w-[440px] max-w-[90vw] shadow-modal">
          <h2 class="font-serif text-[20px] mb-1">Suggested topic</h2>
          <p class="text-[12px] text-ink-3 mb-5">Review the AI-generated topic before saving.</p>

          <!-- Topic preview card -->
          <div class="border border-line rounded-[10px] p-4 mb-5 bg-surface-2">
            <div class="flex items-center gap-3 mb-2">
              <div
                class="w-8 h-8 rounded-full flex-shrink-0"
                :style="{ background: suggestion.color }"
              />
              <div>
                <p class="text-[14px] font-medium text-ink">{{ suggestion.name }}</p>
                <p v-if="suggestion.is_new" class="text-[11px] text-accent font-medium">New topic</p>
                <p v-else class="text-[11px] text-ink-3">Existing topic</p>
              </div>
            </div>
            <p v-if="suggestion.description" class="text-[12px] text-ink-2 leading-relaxed">
              {{ suggestion.description }}
            </p>
          </div>

          <!-- Feedback input -->
          <Transition name="fade">
            <div v-if="showFeedback" class="mb-4">
              <label class="text-[12px] text-ink-3 mb-1 block">Feedback for regeneration (optional)</label>
              <textarea
                v-model="feedback"
                placeholder="e.g. Make it more specific, use a different color..."
                rows="2"
                class="w-full px-3 py-2 border border-line rounded-[8px] bg-surface-2
                       text-[13px] text-ink placeholder:text-ink-3 outline-none focus:border-accent
                       resize-none"
              />
            </div>
          </Transition>

          <!-- Actions -->
          <div class="flex gap-2">
            <button
              type="button"
              class="flex-1 py-[9px] rounded-lg border border-line text-[13px] text-ink-3 hover:bg-surface-2"
              @click="onCancel"
            >
              Cancel
            </button>
            <button
              type="button"
              :disabled="loading"
              class="flex-1 py-[9px] rounded-lg border border-line text-[13px] text-ink-2 hover:bg-surface-2 disabled:opacity-50"
              @click="onRegenerate"
            >
              {{ loading && showFeedback ? 'Regenerating…' : 'Regenerate' }}
            </button>
            <button
              type="button"
              :disabled="loading"
              class="flex-1 py-[9px] rounded-lg bg-accent text-[13px] text-white disabled:opacity-50"
              @click="onApprove"
            >
              {{ loading ? 'Saving…' : 'Approve' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
