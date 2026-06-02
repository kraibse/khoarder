<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppSidebar from '@/components/organisms/AppSidebar.vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import SkeletonCard from '@/components/atoms/SkeletonCard.vue'
import { useTopicsStore } from '@/stores/topics'
import { useConversationsStore } from '@/stores/conversations'
import type { ConversationListOut } from '@/api/conversations'

const route = useRoute()
const router = useRouter()
const topicsStore = useTopicsStore()
const convStore = useConversationsStore()

const topicId = computed(() => {
  const t = route.params.topicId as string | undefined
  return t || undefined
})

const input = ref('')
const scrollRef = ref<HTMLElement | null>(null)
const editingTitle = ref<string | null>(null)
const editTitleValue = ref('')

onMounted(() => {
  convStore.loadConversations(topicId.value)
})

watch(() => route.params.topicId, () => {
  convStore.loadConversations(topicId.value)
  convStore.activeConversation = null
  convStore.messages = []
})

watch(() => convStore.messages.length, () => {
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
})

const activeTopicName = computed(() => {
  if (!topicId.value) return 'Global'
  const t = topicsStore.topics.find((x) => x.id === topicId.value)
  return t?.name ?? 'Topic'
})

async function startNewConversation() {
  const conv = await convStore.createNewConversation(topicId.value)
  await convStore.loadConversation(conv.id)
  await convStore.loadConversations(topicId.value)
}

async function selectConversation(conv: ConversationListOut) {
  await convStore.loadConversation(conv.id)
}

async function handleSend() {
  const text = input.value.trim()
  if (!text || convStore.sending) return
  if (!convStore.activeConversation) {
    const conv = await convStore.createNewConversation(topicId.value, text.slice(0, 40))
    await convStore.loadConversation(conv.id)
    await convStore.loadConversations(topicId.value)
  }
  input.value = ''
  await convStore.postMessage(convStore.activeConversation!.id, text)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function startEditTitle(conv: ConversationListOut) {
  editingTitle.value = conv.id
  editTitleValue.value = conv.title
}

async function saveTitle(conv: ConversationListOut) {
  if (editTitleValue.value.trim()) {
    await convStore.renameConversation(conv.id, editTitleValue.value.trim())
  }
  editingTitle.value = null
}

async function handleDeleteConversation(conv: ConversationListOut) {
  if (!confirm(`Delete "${conv.title}"?`)) return
  await convStore.removeConversation(conv.id)
}
</script>

<template>
  <div class="flex h-screen">
    <AppSidebar />

    <div class="flex-1 flex min-w-0">
      <!-- Conversation list sidebar -->
      <div class="w-64 border-r border-line flex flex-col bg-surface flex-shrink-0">
        <div class="px-4 py-3 border-b border-line flex items-center justify-between">
          <div>
            <div class="text-[10px] font-semibold tracking-[0.09em] uppercase text-ink-3">
              {{ activeTopicName }}
            </div>
            <div class="text-[13px] font-medium text-ink">Chat</div>
          </div>
          <button
            type="button"
            class="p-1.5 rounded-md hover:bg-surface-3 transition-colors"
            @click="startNewConversation"
          >
            <AppIcon name="plus" :size="14" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto py-2">
          <div
            v-for="conv in convStore.conversations"
            :key="conv.id"
            class="px-3 py-2 mx-2 rounded-md cursor-pointer flex items-center gap-2 group hover:bg-surface-3"
            :class="{ 'bg-surface-3': convStore.activeConversation?.id === conv.id }"
            @click="selectConversation(conv)"
          >
            <AppIcon name="message" :size="12" class="text-ink-3 flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <div
                v-if="editingTitle === conv.id"
                class="flex items-center gap-1"
              >
                <input
                  v-model="editTitleValue"
                  class="w-full text-[12px] bg-surface border border-line rounded px-1 py-0.5 outline-none focus:border-accent"
                  @keydown.enter="saveTitle(conv)"
                  @keydown.esc="editingTitle = null"
                  @blur="saveTitle(conv)"
                  ref="(el) => { if (el) (el as HTMLInputElement).focus() }"
                />
              </div>
              <div v-else class="text-[12px] text-ink truncate">
                {{ conv.title }}
              </div>
              <div class="text-[10px] text-ink-3">
                {{ conv.message_count }} messages
              </div>
            </div>
            <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100">
              <button
                type="button"
                class="p-1 rounded hover:bg-surface-2 text-ink-3"
                @click.stop="startEditTitle(conv)"
              >
                <AppIcon name="edit" :size="10" />
              </button>
              <button
                type="button"
                class="p-1 rounded hover:bg-danger-bg text-danger"
                @click.stop="handleDeleteConversation(conv)"
              >
                <AppIcon name="trash" :size="10" />
              </button>
            </div>
          </div>

          <div v-if="convStore.conversations.length === 0 && !convStore.loading" class="px-4 py-8 text-center text-ink-3 text-[12px]">
            No conversations yet.
            <br />Click + to start one.
          </div>
        </div>
      </div>

      <!-- Main chat area -->
      <div class="flex-1 flex flex-col min-w-0 bg-surface">
        <!-- Header -->
        <div class="px-6 py-3 border-b border-line flex items-center justify-between flex-shrink-0">
          <div class="text-[14px] font-medium text-ink">
            {{ convStore.activeConversation?.title ?? 'New Conversation' }}
          </div>
          <div v-if="convStore.sending" class="text-[11px] text-ink-3 flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            Thinking...
          </div>
        </div>

        <!-- Messages -->
        <div ref="scrollRef" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <template v-if="convStore.activeConversation">
            <div
              v-for="msg in convStore.messages"
              :key="msg.id"
              class="flex"
              :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
            >
              <div
                class="max-w-[80%] px-4 py-2.5 rounded-2xl text-[13px] leading-relaxed"
                :class="msg.role === 'user'
                  ? 'bg-accent text-white rounded-br-md'
                  : 'bg-surface-3 text-ink rounded-bl-md border border-line'"
              >
                <div class="whitespace-pre-wrap">{{ msg.content }}</div>
              </div>
            </div>
          </template>

          <div v-else class="flex items-center justify-center h-full text-ink-3 text-[13px]">
            Select a conversation or start a new one.
          </div>
        </div>

        <!-- Input -->
        <div class="px-6 py-3 border-t border-line flex-shrink-0">
          <div class="flex items-end gap-2 bg-surface-3 rounded-xl border border-line px-3 py-2 focus-within:border-accent transition-colors">
            <textarea
              v-model="input"
              rows="1"
              class="flex-1 bg-transparent text-[13px] text-ink placeholder:text-ink-3 resize-none outline-none max-h-[120px]"
              placeholder="Ask anything..."
              @keydown="handleKeydown"
              @input="(e) => { const t = e.target as HTMLTextAreaElement; t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px' }"
            />
            <button
              type="button"
              class="p-2 rounded-lg bg-accent text-white hover:opacity-90 transition-opacity flex-shrink-0 disabled:opacity-40"
              :disabled="!input.trim() || convStore.sending"
              @click="handleSend"
            >
              <AppIcon name="send" :size="14" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
