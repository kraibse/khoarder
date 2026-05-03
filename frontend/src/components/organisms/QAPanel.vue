<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import { useQA } from '@/composables/useQA'

const props = defineProps<{ topicId: string }>()

const { messages, input, loading, status, send } = useQA(props.topicId)
const threadEl = ref<HTMLElement | null>(null)

function handleKey(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

watch(
  messages,
  async () => {
    await nextTick()
    if (threadEl.value) threadEl.value.scrollTop = threadEl.value.scrollHeight
  },
  { deep: true },
)
</script>

<template>
  <div class="px-[18px] py-4">
    <!-- Header -->
    <div class="flex items-center justify-between mb-[10px]">
      <div class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3">
        Topic Q&A
      </div>
      <div class="flex items-center gap-1 text-[10px] text-ink-3">
        <span
          :class="[
            'w-[6px] h-[6px] rounded-full',
            status.configured ? 'bg-[oklch(55%_0.12_145)]' : 'bg-[oklch(60%_0.04_60)]',
          ]"
        />
        {{ status.configured ? (status.model ?? 'LM Studio') : 'Not configured' }}
      </div>
    </div>

    <!-- Not-configured notice -->
    <div
      v-if="!status.configured"
      class="text-[11.5px] text-ink-3 bg-surface-2 border border-line rounded-[7px] px-3 py-3 mb-3 leading-[1.5]"
    >
      Set <code class="font-mono text-[11px] text-accent">LLM_BASE_URL</code> in your
      <code class="font-mono text-[11px] text-accent">.env</code> to enable Q&amp;A.
    </div>

    <!-- Thread -->
    <div
      ref="threadEl"
      class="flex flex-col gap-2 mb-3 max-h-[260px] overflow-y-auto min-h-[40px]"
    >
      <template v-for="(msg, i) in messages" :key="i">
        <div
          :class="[
            'text-[12.5px] leading-[1.5] px-[11px] py-[9px] rounded-lg max-w-[95%]',
            msg.role === 'user'
              ? 'bg-ink text-surface self-end rounded-br-sm'
              : 'bg-surface border border-line text-ink-2 self-start rounded-bl-sm',
          ]"
        >
          {{ msg.text }}
        </div>

        <!-- Source references -->
        <div v-if="msg.sources && msg.sources.length" class="flex flex-col gap-[3px]">
          <div
            v-for="src in msg.sources"
            :key="src.id"
            class="text-[10.5px] text-ink-3 px-[8px] py-[5px] bg-surface-2 rounded-[5px]
                   border-l-2 border-accent leading-[1.4]"
          >
            <span class="font-medium text-ink-2">{{ src.title }}</span>
            <span class="ml-1 opacity-60">· {{ src.type }}</span>
            <p v-if="src.snippet" class="mt-[2px] opacity-75 line-clamp-2">{{ src.snippet }}</p>
          </div>
        </div>
      </template>

      <div
        v-if="loading"
        class="text-[12.5px] leading-[1.5] px-[11px] py-[9px] rounded-lg max-w-[95%]
               bg-surface border border-line text-ink-2 self-start rounded-bl-sm opacity-50"
      >
        Searching knowledge base…
      </div>
    </div>

    <!-- Input -->
    <div class="flex gap-[6px]">
      <textarea
        v-model="input"
        rows="2"
        :disabled="!status.configured"
        placeholder="Ask about this topic…"
        class="flex-1 text-[12.5px] px-[10px] py-2 rounded-[7px] border border-line
               bg-surface text-ink placeholder:text-ink-3 outline-none resize-none leading-[1.4]
               focus:border-accent transition-colors duration-[120ms]
               disabled:opacity-40 disabled:cursor-not-allowed"
        @keydown="handleKey"
      />
      <button
        type="button"
        :disabled="loading || !status.configured"
        class="w-8 h-8 rounded-[7px] bg-ink text-surface flex items-center justify-center
               flex-shrink-0 self-end hover:bg-accent transition-colors duration-[120ms]
               disabled:opacity-40 disabled:cursor-not-allowed"
        @click="send"
      >
        <AppIcon name="send" :size="12" />
      </button>
    </div>

    <p class="text-[10.5px] text-ink-3 text-center mt-2">
      Answers grounded in your stored knowledge base
    </p>
  </div>
</template>
