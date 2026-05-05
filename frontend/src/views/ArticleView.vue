<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { marked } from 'marked'
import ArticleTopBar from '@/components/organisms/ArticleTopBar.vue'
import ArticleSidebar from '@/components/organisms/ArticleSidebar.vue'
import ColorPlaceholder from '@/components/molecules/ColorPlaceholder.vue'
import ExtendSection from '@/components/molecules/ExtendSection.vue'
import EntryEditModal from '@/components/molecules/EntryEditModal.vue'
import ExtendModal from '@/components/molecules/ExtendModal.vue'
import AddModal from '@/components/molecules/AddModal.vue'
import TableOfContents from '@/components/molecules/TableOfContents.vue'
import AppTag from '@/components/atoms/AppTag.vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import { useReadProgress } from '@/composables/useReadProgress'
import { useTableOfContents } from '@/composables/useTableOfContents'
import { useTopicsStore } from '@/stores/topics'
import { useEntriesStore } from '@/stores/entries'
import { useRouter } from 'vue-router'
import type { ArticleDetail, Backlink, RelatedEntry, SourceFile } from '@/data/mock'
import { getEntry, getBacklinks, getRelated, getAttachments } from '@/api/entries'
import type { ArticleDetailOut, BacklinkOut, RelatedEntryOut, AttachmentOut } from '@/api/entries'

marked.use({ breaks: true })

const props = defineProps<{ id: string }>()
const router = useRouter()

const topicsStore = useTopicsStore()
const entriesStore = useEntriesStore()

const article = ref<ArticleDetail | null>(null)
const backlinks = ref<Backlink[]>([])
const related = ref<RelatedEntry[]>([])
const sourceFiles = ref<SourceFile[]>([])
const loading = ref(true)

const showEditModal = ref(false)
const showExtendModal = ref(false)
const extendPrefill = ref('')
const showAddModal = ref(false)
const addModalPresetMode = ref<'url' | 'note' | null>(null)

const topic = computed(() =>
  article.value ? topicsStore.topics.find((t) => t.id === article.value!.topicId) : null,
)

const { headings, activeSlug, observe, scrollTo } = useTableOfContents(
  computed(() => article.value?.body)
)

// Render body: pre-process [[Title]] then run through marked
// Post-process to inject heading IDs for TOC anchor links
const renderedBody = computed(() => {
  const raw = article.value?.body ?? ''
  const withRefs = raw.replace(
    /\[\[(.+?)\]\]/g,
    '<span class="backlink-ref">$1</span>',
  )
  let html = marked(withRefs) as string
  // Inject id attributes into heading tags
  const slugMap = new Map<string, number>()
  html = html.replace(/<(h[1-6])>([^<]+)<\/\1>/g, (_match, tag, text) => {
    let slug = text
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/\s+/g, '-')
      .substring(0, 64)
    const count = slugMap.get(slug) ?? 0
    slugMap.set(slug, count + 1)
    if (count > 0) slug = `${slug}-${count}`
    return `<${tag} id="${slug}">${text}</${tag}>`
  })
  return html
})

watch(renderedBody, () => {
  nextTick(() => {
    if (scrollEl.value) observe(scrollEl.value)
  })
})

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`
  if (b < 1_048_576) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1_048_576).toFixed(1)} MB`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function mapArticle(e: ArticleDetailOut): ArticleDetail {
  return {
    id: e.id,
    topicId: e.topic_id,
    type: e.type as ArticleDetail['type'],
    hasImg: e.has_img,
    imgUrl: e.img_url ?? undefined,
    imgH: e.img_height ?? undefined,
    imgColor: e.img_color,
    isStarred: e.is_starred,
    title: e.title,
    excerpt: e.excerpt,
    body: e.body,
    tags: e.tags,
    date: e.date,
    source: e.source ?? '',
    sourceUrl: e.source_url ?? undefined,
    wordCount: e.word_count,
    readTime: `${e.read_time_min} min read`,
    backlinkCount: e.backlink_count,
  }
}

function mapBacklink(b: BacklinkOut): Backlink {
  return { id: b.id, relationId: b.relation_id, title: b.title, type: b.type as Backlink['type'], refs: b.refs }
}

function mapRelated(r: RelatedEntryOut): RelatedEntry {
  return { id: r.id, relationId: r.relation_id, title: r.title, type: r.type as RelatedEntry['type'], imgColor: r.img_color }
}

function mapAttachment(a: AttachmentOut): SourceFile {
  return { id: a.id, name: a.filename, ext: a.ext, size: formatBytes(a.size_bytes), date: formatDate(a.created_at) }
}

async function refreshArticle() {
  const [entryData, bl, rel, att] = await Promise.all([
    getEntry(props.id),
    getBacklinks(props.id),
    getRelated(props.id),
    getAttachments(props.id),
  ])
  article.value = mapArticle(entryData)
  backlinks.value = bl.map(mapBacklink)
  related.value = rel.map(mapRelated)
  sourceFiles.value = att.map(mapAttachment)
}

async function refreshAttachments() {
  const att = await getAttachments(props.id)
  sourceFiles.value = att.map(mapAttachment)
}

async function refreshRelated() {
  const [bl, rel] = await Promise.all([getBacklinks(props.id), getRelated(props.id)])
  backlinks.value = bl.map(mapBacklink)
  related.value = rel.map(mapRelated)
}

async function loadArticle() {
  loading.value = true
  if (topicsStore.topics.length === 0) {
    await topicsStore.loadTopics()
  }
  await refreshArticle()
  loading.value = false
}

onMounted(loadArticle)

watch(() => props.id, loadArticle)

function onWriteExtension() {
  extendPrefill.value = ''
  showExtendModal.value = true
}

function onDraftExtension(text: string) {
  extendPrefill.value = text
  showExtendModal.value = true
}

function onAttachFile() {
  // Delegate to sidebar's file picker — sidebar handles it internally
}

function onImportUrl() {
  addModalPresetMode.value = 'url'
  showAddModal.value = true
}

function onPasteExcerpt() {
  addModalPresetMode.value = 'note'
  showAddModal.value = true
}

const scrollEl = ref<HTMLElement | null>(null)
const heroEl = ref<HTMLElement | null>(null)
const heroHeight = ref(0)

function updateHeroHeight() {
  if (heroEl.value) {
    heroHeight.value = heroEl.value.offsetHeight
  }
}

const { progress } = useReadProgress(scrollEl, heroHeight)

onMounted(() => {
  updateHeroHeight()
  window.addEventListener('resize', updateHeroHeight)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateHeroHeight)
})
</script>

<template>
  <div class="flex flex-col h-screen overflow-hidden bg-surface">
    <ArticleTopBar
      v-if="article"
      :article="article"
      :topic="topic ?? undefined"
      @star-toggled="(s) => {
        if (article) {
          article.isStarred = s
          entriesStore.patchEntry(article.id, { isStarred: s })
        }
      }"
    />

    <div v-if="loading" class="flex-1 flex items-center justify-center text-ink-3 text-sm">
      Loading…
    </div>

    <!-- Body row -->
    <div v-else-if="article" class="flex flex-1 overflow-hidden">
      <!-- Main scrollable column -->
      <main ref="scrollEl" class="flex-1 overflow-y-auto min-w-0">
        <!-- Hero image -->
        <div ref="heroEl" class="relative overflow-hidden border-b border-line" style="aspect-ratio: 16/7">
          <img
            v-if="article.imgUrl"
            :src="article.imgUrl"
            :alt="article.title"
            class="absolute inset-0 w-full h-full object-cover"
          />
          <ColorPlaceholder
            v-else
            :color="article.imgColor"
            height="100%"
            label="article hero image"
            class="absolute inset-0"
          />
          <div
            class="absolute inset-0"
            style="background: linear-gradient(to bottom, transparent 50%, oklch(16% 0.01 60 / 0.15) 100%)"
          />
        </div>

        <!-- Read progress bar (below hero, starts when hero scrolls out) -->
        <div class="h-[3px] bg-surface-2 w-full">
          <div
            class="h-full bg-accent transition-[width] duration-100 ease-linear"
            :style="{ width: `${progress}%` }"
            aria-hidden="true"
          />
        </div>

        <!-- Article inner with TOC -->
        <div class="flex justify-center">
          <!-- Table of contents (wide screens only) -->
          <aside class="hidden 2xl:block w-[220px] flex-shrink-0 pl-8 pt-8">
            <div class="sticky top-8">
              <TableOfContents
                :headings="headings"
                :active-slug="activeSlug"
                @navigate="(slug) => scrollTo(slug, scrollEl!)"
              />
            </div>
          </aside>

          <div class="max-w-article w-full px-8 pb-20">
          <!-- Article header -->
          <div class="pt-8 pb-6 border-b border-line mb-7">
            <!-- Topic chip -->
            <div
              v-if="topic"
              class="flex items-center gap-[6px] text-[11px] font-semibold tracking-[0.07em] uppercase text-accent mb-3"
            >
              <span
                class="w-[7px] h-[7px] rounded-full"
                :style="{ background: topic.color }"
              />
              {{ topic.name }}
            </div>

            <!-- Title -->
            <h1
              class="font-serif text-[32px] leading-[1.2] tracking-[-0.01em] text-ink mb-4"
              style="text-wrap: pretty"
            >
              {{ article.title }}
            </h1>

            <!-- Meta row -->
            <div class="flex flex-wrap items-center gap-3 text-xs text-ink-3">
              <span class="flex items-center gap-[5px]">
                <AppIcon name="clock" :size="12" />
                {{ article.readTime }}
              </span>
              <span class="flex items-center gap-[5px]">
                <AppIcon name="filter" :size="12" />
                {{ article.wordCount.toLocaleString() }} words
              </span>
              <span class="flex items-center gap-[5px]">
                <AppIcon name="edit" :size="12" />
                {{ article.date }}
              </span>
            <a
              v-if="article.sourceUrl"
              :href="article.sourceUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="ml-auto text-[11px] italic text-accent hover:underline truncate max-w-[240px]"
            >
              {{ article.source }}
            </a>
            <span v-else-if="article.source" class="ml-auto text-[11px] italic text-ink-3">
              {{ article.source }}
            </span>
            </div>

            <!-- Tags -->
            <div class="flex flex-wrap gap-[5px] mt-[14px]">
              <AppTag v-for="tag in article.tags" :key="tag" :label="tag" />
            </div>
          </div>

          <!-- Article body (Markdown rendered; [[Title]] shown as styled spans) -->
          <div class="article-prose" v-html="renderedBody" />

          <!-- Extend section (user-triggered only) -->
          <ExtendSection
            @write-extension="onWriteExtension"
            @attach-file="onAttachFile"
            @import-url="onImportUrl"
            @paste-excerpt="onPasteExcerpt"
          />
        </div>
        </div>
      </main>

      <!-- Right sidebar -->
      <ArticleSidebar
        :article="article"
        :backlinks="backlinks"
        :related="related"
        :source-files="sourceFiles"
        :entry-id="props.id"
        @attached="refreshAttachments"
        @edit-entry="showEditModal = true"
        @related-changed="refreshRelated"
        @draft-extension="onDraftExtension"
        @deleted="router.push('/')"
      />
    </div>

    <!-- Modals -->
    <EntryEditModal
      v-if="showEditModal && article"
      :entry="article"
      @close="showEditModal = false"
      @saved="refreshArticle"
    />

    <ExtendModal
      v-if="showExtendModal && article"
      :entry-id="props.id"
      :current-body="article.body ?? ''"
      :prefill="extendPrefill"
      @close="showExtendModal = false"
      @extended="refreshArticle"
    />

    <AddModal
      v-if="showAddModal"
      @close="showAddModal = false"
      @created="showAddModal = false"
    />
  </div>
</template>
