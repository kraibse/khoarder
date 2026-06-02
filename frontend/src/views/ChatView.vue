<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppSidebar from '@/components/organisms/AppSidebar.vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import SkeletonCard from '@/components/atoms/SkeletonCard.vue'
import { useTopicsStore } from '@/stores/topics'
import { useConversationsStore } from '@/stores/conversations'
import { useMemoriesStore } from '@/stores/memories'
import { createEntryFromChat, sendMessage, deleteMessage } from '@/api/conversations'
import type { ConversationListOut, MessageOut } from '@/api/conversations'
import { checkHealth, listModels, loadModel } from '@/api/config'
import type { HealthOut, ModelInfo } from '@/api/config'

const route = useRoute()
const router = useRouter()
const topicsStore = useTopicsStore()
const convStore = useConversationsStore()
const memStore = useMemoriesStore()

const topicId = computed(() => {
  const t = route.params.topicId as string | undefined
  return t || undefined
})

const input = ref('')
const scrollRef = ref<HTMLElement | null>(null)
const editingTitle = ref<string | null>(null)
const editTitleValue = ref('')
const editingMemoryId = ref<string | null>(null)
const editMemoryValue = ref('')
const llmReachable = ref<boolean | null>(null)
const llmHealthModel = ref<string | null>(null)
const models = ref<ModelInfo[]>([])
const selectedModel = ref('')
const loadingModel = ref(false)
const modelError = ref('')

async function pollHealth() {
  try {
    const h = await checkHealth()
    llmReachable.value = h.reachable
    llmHealthModel.value = h.model
  } catch {
    llmReachable.value = false
    llmHealthModel.value = null
  }
}

async function fetchModels() {
  try {
    const res = await listModels()
    models.value = res.models
    modelError.value = res.error || ''
    const loaded = res.models.find((m) => m.loaded)
    if (loaded) {
      selectedModel.value = loaded.path || loaded.id
    } else if (res.models.length > 0) {
      selectedModel.value = res.models[0].path || res.models[0].id
    }
  } catch (e) {
    models.value = []
    modelError.value = e instanceof Error ? e.message : 'Failed to fetch models'
  }
}

async function handleLoadModel() {
  if (!selectedModel.value) return
  loadingModel.value = true
  modelError.value = ''
  try {
    await loadModel(selectedModel.value)
    await fetchModels()
    await pollHealth()
  } catch (e) {
    modelError.value = e instanceof Error ? e.message : 'Failed to load model'
  } finally {
    loadingModel.value = false
  }
}

let healthInterval: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  convStore.loadConversations(topicId.value)
  memStore.loadMemories(topicId.value)
  pollHealth()
  fetchModels()
  healthInterval = setInterval(pollHealth, 30000)
})

watch(() => route.params.topicId, () => {
  convStore.loadConversations(topicId.value)
  convStore.activeConversation = null
  convStore.messages = []
  memStore.loadMemories(topicId.value)
})

onUnmounted(() => {
  if (healthInterval) clearInterval(healthInterval)
})

watch(() => convStore.messages, () => {
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
}, { deep: true })

const activeTopicName = computed(() => {
  if (!topicId.value) return 'Global'
  const t = topicsStore.topics.find((x) => x.id === topicId.value)
  return t?.name ?? 'Topic'
})

const isEmpty = computed(() => {
  return !convStore.activeConversation || convStore.messages.length === 0
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

  // Auto-load model if none is loaded
  if (llmReachable.value && !llmHealthModel.value && selectedModel.value && !loadingModel.value) {
    await handleLoadModel()
    if (!llmHealthModel.value) {
      modelError.value = 'Model failed to load. Please check LM Studio.'
      return
    }
  }

  if (!convStore.activeConversation) {
    const conv = await convStore.createNewConversation(topicId.value, text.slice(0, 40))
    await convStore.loadConversation(conv.id)
    await convStore.loadConversations(topicId.value)
  }
  input.value = ''
  convStore.postMessageStream(convStore.activeConversation!.id, text)
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

async function saveMessageAsEntry(msgId: string, type: string) {
  try {
    const entry = await createEntryFromChat(msgId, undefined, type)
    alert(`Saved as ${type}: "${entry.title}"`)
  } catch (e) {
    alert(`Save failed: ${(e as Error).message}`)
  }
}

async function regenerateResponse(assistantMsg: MessageOut) {
  const convId = convStore.activeConversation?.id
  if (!convId) return
  // Find the user message just before this assistant message
  const msgs = convStore.messages
  const idx = msgs.findIndex((m) => m.id === assistantMsg.id)
  if (idx <= 0) return
  const userMsg = msgs[idx - 1]
  if (userMsg.role !== 'user') return
  // Remove the stale assistant message from local array first (optimistic)
  convStore.messages = msgs.filter((m) => m.id !== assistantMsg.id)
  try {
    await deleteMessage(convId, assistantMsg.id)
    const response = await sendMessage(convId, userMsg.content)
    convStore.messages.push(response)
  } catch (e) {
    alert(`Regeneration failed: ${(e as Error).message}`)
    // Re-add the original message on failure
    convStore.messages.splice(idx, 0, assistantMsg)
  }
}

function copyMessage(content: string) {
  navigator.clipboard.writeText(content).catch(() => {
    alert('Failed to copy to clipboard')
  })
}

async function addMemoryFromMessage(content: string) {
  try {
    await memStore.addMemory(content, topicId.value, 'fact')
  } catch (e) {
    alert(`Add memory failed: ${(e as Error).message}`)
  }
}

function startEditMemory(mem: { id: string; content: string }) {
  editingMemoryId.value = mem.id
  editMemoryValue.value = mem.content
}

async function saveEditMemory(memId: string) {
  if (editMemoryValue.value.trim()) {
    await memStore.editMemory(memId, { content: editMemoryValue.value.trim() })
  }
  editingMemoryId.value = null
}

async function handleDeleteMemory(memId: string) {
  if (!confirm('Delete this memory?')) return
  await memStore.removeMemory(memId)
}
</script>

<template>
  <div class="flex h-screen">
    <AppSidebar />

    <div class="flex-1 flex min-w-0">
      <!-- Conversation list sidebar -->
      <div class="w-64 border-r border-line flex flex-col bg-surface flex-shrink-0">
        <div class="px-4 border-b border-line flex items-center justify-between h-[58px] flex-shrink-0">
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
        <div class="px-6 border-b border-line flex items-center justify-between h-[58px] flex-shrink-0">
          <div class="text-[14px] font-medium text-ink">
            {{ convStore.activeConversation?.title ?? 'New Conversation' }}
          </div>
          <div class="flex items-center gap-3">
            <div
              v-if="llmReachable === false"
              class="text-[11px] text-danger flex items-center gap-1"
              title="LLM endpoint is not reachable"
            >
              <span class="w-1.5 h-1.5 rounded-full bg-danger" />
              Offline
            </div>
            <div
              v-else-if="llmReachable === true && !llmHealthModel"
              class="text-[11px] text-amber-600 flex items-center gap-1"
              title="No model is loaded in LM Studio"
            >
              <span class="w-1.5 h-1.5 rounded-full bg-amber-500" />
              No model loaded
            </div>
            <div v-if="convStore.sending" class="text-[11px] text-ink-3 flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
              Thinking...
            </div>
          </div>
        </div>

        <!-- Empty state: centered everything -->
        <div v-if="isEmpty" class="flex-1 flex flex-col items-center justify-center px-6">
          <div class="max-w-2xl w-full text-center space-y-6">
            <div class="space-y-2">
              <h2 class="text-[22px] font-serif text-ink">What would you like to know?</h2>
              <p class="text-[13px] text-ink-3">Ask a question about your knowledge base.</p>
            </div>

            <!-- Model selector (only when no model loaded) -->
            <div v-if="llmReachable === true && !llmHealthModel" class="space-y-2">
              <div class="flex items-center justify-center gap-2">
                <select
                  v-model="selectedModel"
                  class="rounded border border-line bg-surface-2 px-3 py-2 text-[13px] text-ink focus:outline-none focus:ring-1 focus:ring-accent min-w-[240px]"
                >
                  <option v-if="models.length === 0" value="">No models found</option>
                  <option v-for="m in models" :key="m.id" :value="m.path || m.id">
                    {{ m.id }}{{ m.loaded ? ' (loaded)' : '' }}
                  </option>
                </select>
                <button
                  type="button"
                  class="rounded border border-line px-3 py-2 text-[13px] text-ink-2 hover:bg-surface-2 disabled:opacity-50 whitespace-nowrap"
                  :disabled="loadingModel || !selectedModel"
                  @click="handleLoadModel"
                >
                  {{ loadingModel ? 'Loading…' : 'Load model' }}
                </button>
              </div>
              <div v-if="modelError" class="text-[11px] text-danger">{{ modelError }}</div>
            </div>

            <!-- Centered input -->
            <div class="flex items-end gap-2 bg-surface-3 rounded-xl border border-line px-3 py-2 focus-within:border-accent transition-colors max-w-2xl mx-auto">
              <textarea
                v-model="input"
                rows="1"
                class="flex-1 bg-transparent text-[14px] text-ink placeholder:text-ink-3 resize-none outline-none max-h-[120px] min-h-[44px]"
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

        <!-- Non-empty: messages + bottom input -->
        <template v-else>
          <div ref="scrollRef" class="flex-1 overflow-y-auto px-6 py-4">
            <div class="max-w-3xl mx-auto space-y-4">
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
                    : msg.id.startsWith('err-')
                      ? 'bg-[var(--danger-bg)] text-danger rounded-bl-md border border-danger'
                      : 'bg-surface-3 text-ink rounded-bl-md border border-line'"
                >
                  <div class="whitespace-pre-wrap">{{ msg.content }}<span v-if="msg.id === convStore.streamingMessageId" class="inline-block w-[6px] h-[13px] ml-0.5 align-middle bg-accent animate-pulse rounded-sm" /></div>
                  <div v-if="msg.role === 'assistant' && !msg.id.startsWith('tmp-') && !msg.id.startsWith('err-') && msg.id !== convStore.streamingMessageId" class="mt-2 flex items-center gap-1.5 border-t border-line pt-1.5">
                    <button
                      type="button"
                      class="rounded p-1 text-ink-3 transition-colors hover:text-ink hover:bg-surface-2"
                      title="Regenerate"
                      @click="regenerateResponse(msg)"
                    >
                      <AppIcon name="refresh" :size="14" />
                    </button>
                    <button
                      type="button"
                      class="rounded p-1 text-ink-3 transition-colors hover:text-ink hover:bg-surface-2"
                      title="Copy"
                      @click="copyMessage(msg.content)"
                    >
                      <AppIcon name="copy" :size="14" />
                    </button>
                    <button
                      type="button"
                      class="rounded p-1 text-ink-3 transition-colors hover:text-ink hover:bg-surface-2"
                      title="Add memory"
                      @click="addMemoryFromMessage(msg.content)"
                    >
                      <AppIcon name="plus-circle" :size="14" />
                    </button>
                    <button
                      type="button"
                      class="rounded p-1 text-ink-3 transition-colors hover:text-ink hover:bg-surface-2"
                      title="Save as note"
                      @click="saveMessageAsEntry(msg.id, 'Note')"
                    >
                      <AppIcon name="document-text" :size="14" />
                    </button>
                    <button
                      type="button"
                      class="rounded p-1 text-ink-3 transition-colors hover:text-ink hover:bg-surface-2"
                      title="Save as article"
                      @click="saveMessageAsEntry(msg.id, 'Article')"
                    >
                      <AppIcon name="newspaper" :size="14" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Bottom input -->
          <div class="px-6 py-3 border-t border-line flex-shrink-0">
            <div class="max-w-3xl mx-auto">
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
        </template>
      </div>

      <!-- Memory sidebar -->
      <div class="w-56 border-l border-line flex flex-col bg-surface flex-shrink-0">
        <div class="px-3 border-b border-line flex items-center justify-between h-[58px] flex-shrink-0">
          <div class="text-[11px] font-semibold tracking-[0.09em] uppercase text-ink-3">Memories</div>
        </div>
        <div class="flex-1 overflow-y-auto py-2 px-3 space-y-2">
          <div
            v-for="mem in memStore.memories"
            :key="mem.id"
            class="group relative px-2 py-1.5 rounded-md bg-surface-3 border border-line hover:border-accent transition-colors"
          >
            <div v-if="editingMemoryId === mem.id" class="flex items-center gap-1">
              <input
                v-model="editMemoryValue"
                class="w-full text-[11px] bg-surface border border-line rounded px-1 py-0.5 outline-none focus:border-accent"
                @keydown.enter="saveEditMemory(mem.id)"
                @keydown.esc="editingMemoryId = null"
                @blur="saveEditMemory(mem.id)"
              />
            </div>
            <div v-else>
              <div class="text-[11px] text-ink leading-snug">{{ mem.content }}</div>
              <div class="mt-1 flex items-center justify-between">
                <div class="text-[9px] text-ink-3 uppercase">{{ mem.type }}</div>
                <div class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100">
                  <button
                    type="button"
                    class="p-0.5 rounded hover:bg-surface-2 text-ink-3"
                    @click="startEditMemory(mem)"
                  >
                    <AppIcon name="edit" :size="8" />
                  </button>
                  <button
                    type="button"
                    class="p-0.5 rounded hover:bg-danger-bg text-danger"
                    @click="handleDeleteMemory(mem.id)"
                  >
                    <AppIcon name="trash" :size="8" />
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div v-if="memStore.memories.length === 0 && !memStore.loading" class="text-center text-ink-3 text-[11px] py-4">
            No memories yet.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
