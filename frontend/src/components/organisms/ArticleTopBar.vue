<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/atoms/AppIcon.vue'
import IconButton from '@/components/atoms/IconButton.vue'
import type { ArticleDetail, Topic } from '@/data/mock'
import { updateEntry } from '@/api/entries'

const props = defineProps<{
  article: ArticleDetail
  topic?: Topic
}>()

const emit = defineEmits<{
  'star-toggled': [starred: boolean]
}>()

const router = useRouter()
const isStarred = ref(props.article.isStarred)

async function toggleStar() {
  const next = !isStarred.value
  isStarred.value = next
  try {
    await updateEntry(props.article.id, { is_starred: next })
    emit('star-toggled', next)
  } catch (e) {
    isStarred.value = !next
    console.error('Failed to toggle star:', e)
  }
}
</script>

<template>
  <header
    class="flex items-center gap-3 px-5 border-b border-line bg-surface flex-shrink-0 z-20"
    style="height: 54px"
  >
    <!-- Left: back + breadcrumb -->
    <div class="flex items-center gap-2 flex-1 min-w-0">
      <button
        type="button"
        class="flex items-center gap-[5px] text-[12.5px] text-ink-3 px-2 py-[5px] rounded-[6px]
               hover:bg-surface-2 hover:text-ink transition-colors duration-[120ms] flex-shrink-0"
        @click="router.back()"
      >
        <AppIcon name="arrow-left" :size="13" />
        Back
      </button>

      <div class="w-px h-4 bg-line mx-1" />

      <div class="flex items-center gap-[6px] text-[12.5px] text-ink-3 overflow-hidden">
        <span class="text-accent font-medium whitespace-nowrap">{{ topic?.name }}</span>
        <span class="opacity-40">›</span>
        <span class="truncate">{{ article.title }}</span>
      </div>
    </div>

    <!-- Right: actions -->
    <div class="flex items-center gap-[6px] flex-shrink-0">
      <button
        type="button"
        class="h-8 w-8 rounded-[7px] flex items-center justify-center text-ink-2 hover:bg-surface-2 hover:text-ink transition-colors"
        :class="isStarred ? 'text-accent' : ''"
        :title="isStarred ? 'Unstar' : 'Star'"
        @click="toggleStar"
      >
        <AppIcon :name="isStarred ? 'star-filled' : 'star'" :size="15" />
      </button>
      <a
        v-if="article.sourceUrl"
        :href="article.sourceUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="h-8 w-8 rounded-[7px] flex items-center justify-center text-ink-2 hover:bg-surface-2 hover:text-ink transition-colors"
        title="Visit source"
      >
        <AppIcon name="link" :size="15" />
      </a>
      <IconButton icon="copy" label="Copy link" />
      <IconButton icon="share" label="Share" />
      <div class="w-px h-5 bg-line mx-0.5" />
      <button
        type="button"
        class="h-8 px-3 rounded-[7px] text-xs font-medium flex items-center gap-[6px]
               text-ink-2 bg-transparent border border-line
               hover:bg-surface-2 hover:text-ink transition-colors duration-[120ms]"
      >
        <AppIcon name="edit" :size="13" />
        Edit
      </button>
    </div>
  </header>
</template>
