<script setup lang="ts">
import { ref, computed, watchEffect } from 'vue'
import type { Topic } from '@/data/mock'

const props = defineProps<{ topic?: Topic }>()
const emit = defineEmits<{ close: []; saved: [topic: Topic] }>()

// 10 predefined oklch swatches
const PALETTE = [
  'oklch(55% 0.12 200)',
  'oklch(50% 0.14 150)',
  'oklch(52% 0.13 260)',
  'oklch(54% 0.13 30)',
  'oklch(52% 0.13 330)',
  'oklch(55% 0.10 90)',
  'oklch(50% 0.13 180)',
  'oklch(53% 0.12 50)',
  'oklch(50% 0.12 280)',
  'oklch(52% 0.10 120)',
]

const name = ref('')
const description = ref('')
const color = ref(PALETTE[0])
const loading = ref(false)
const error = ref('')

const isEdit = computed(() => !!props.topic)

watchEffect(() => {
  if (props.topic) {
    name.value = props.topic.name
    description.value = props.topic.description
    color.value = props.topic.color
  }
})

import { useTopicsStore } from '@/stores/topics'
const topicsStore = useTopicsStore()

async function submit() {
  if (!name.value.trim()) { error.value = 'Name is required.'; return }
  error.value = ''
  loading.value = true
  try {
    if (isEdit.value && props.topic) {
      await topicsStore.editTopic(props.topic.id, {
        name: name.value.trim(),
        description: description.value,
        color: color.value,
      })
      emit('saved', { ...props.topic, name: name.value.trim(), description: description.value, color: color.value })
    } else {
      const topic = await topicsStore.createNewTopic({
        name: name.value.trim(),
        description: description.value,
        color: color.value,
      })
      emit('saved', {
        id: topic.id, slug: topic.slug, name: topic.name,
        color: topic.color, description: topic.description, count: topic.count,
      })
    }
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
        <div class="bg-surface border border-line rounded-[14px] p-7 w-[440px] max-w-[90vw] shadow-modal">
          <h2 class="font-serif text-[20px] mb-5">{{ isEdit ? 'Edit topic' : 'New topic' }}</h2>

          <label class="block text-[11.5px] text-ink-3 mb-1">Name</label>
          <input
            v-model="name"
            type="text"
            placeholder="e.g. Cognitive Science"
            autofocus
            class="w-full h-10 px-3 border border-line rounded-[8px] bg-surface-2
                   text-[13px] text-ink placeholder:text-ink-3 outline-none focus:border-accent mb-3"
            @keydown.enter="submit"
          />

          <label class="block text-[11.5px] text-ink-3 mb-1">Description</label>
          <textarea
            v-model="description"
            placeholder="What is this topic about?"
            rows="3"
            class="w-full px-3 py-2 border border-line rounded-[8px] bg-surface-2
                   text-[13px] text-ink placeholder:text-ink-3 outline-none focus:border-accent
                   resize-none mb-4"
          />

          <label class="block text-[11.5px] text-ink-3 mb-2">Color</label>
          <div class="flex gap-[8px] mb-5 flex-wrap">
            <button
              v-for="swatch in PALETTE"
              :key="swatch"
              type="button"
              class="w-7 h-7 rounded-full border-2 transition-transform duration-[100ms]"
              :style="{ background: swatch, borderColor: color === swatch ? 'oklch(30% 0.02 200)' : 'transparent' }"
              :class="color === swatch ? 'scale-110' : 'hover:scale-110'"
              @click="color = swatch"
            />
          </div>

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
            >{{ loading ? 'Saving…' : isEdit ? 'Save changes' : 'Create topic' }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
