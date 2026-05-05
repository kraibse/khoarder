<script setup lang="ts">
import { ref, computed } from 'vue'
import AppIcon from '@/components/atoms/AppIcon.vue'

const props = defineProps<{
  cardId: string
  headlines: string[]
  matchCount: number
  query: string
}>()

const emit = defineEmits<{
  jump: [cardId: string, hitIdx: number]
  openAll: [cardId: string]
}>()

const VISIBLE_LIMIT = 3
const FLOOD_LIMIT = 12

const expanded = ref(false)
const tooMany = computed(() => props.matchCount > FLOOD_LIMIT || props.headlines.length > FLOOD_LIMIT)
const totalLabel = computed(() => Math.max(props.matchCount, props.headlines.length))

const visible = computed(() => {
  const cap = expanded.value ? Math.min(props.headlines.length, FLOOD_LIMIT) : VISIBLE_LIMIT
  return props.headlines.slice(0, cap)
})

const hiddenCount = computed(() => Math.min(props.headlines.length, FLOOD_LIMIT) - VISIBLE_LIMIT)

function jump(hitIdx: number) {
  emit('jump', props.cardId, hitIdx)
}

function openAll() {
  emit('openAll', props.cardId)
}
</script>

<template>
  <div class="search-hits" @click.stop>
    <div class="search-hits-label">
      <AppIcon name="search" :size="11" />
      <span>{{ totalLabel }} {{ totalLabel === 1 ? 'match' : 'matches' }} in entry</span>
    </div>

    <button
      v-for="(h, i) in visible"
      :key="i"
      type="button"
      class="search-hit"
      @click="jump(i)"
    >
      <span class="search-hit-num">{{ String(i + 1).padStart(2, '0') }}</span>
      <!-- eslint-disable-next-line vue/no-v-html -->
      <span class="search-hit-text" v-html="h" />
    </button>

    <button
      v-if="!expanded && headlines.length > VISIBLE_LIMIT"
      type="button"
      class="search-hit-more"
      @click="expanded = true"
    >
      Show {{ hiddenCount }} more{{ tooMany ? ` of ${totalLabel}` : '' }} ↓
    </button>

    <button
      v-if="expanded && tooMany"
      type="button"
      class="search-hit-more"
      @click="openAll"
    >
      Open entry to see all {{ totalLabel }} matches →
    </button>

    <button
      v-if="expanded && !tooMany && headlines.length > VISIBLE_LIMIT"
      type="button"
      class="search-hit-more"
      @click="expanded = false"
    >
      Show less ↑
    </button>
  </div>
</template>

<style scoped>
.search-hits {
  border-top: 1px dashed var(--border);
  padding: 8px 14px 6px;
  background: oklch(98% 0.012 200);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.search-hits-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--accent);
  display: flex;
  align-items: center;
  gap: 5px;
  padding-bottom: 2px;
}

.search-hits-label > span {
  white-space: nowrap;
}

.search-hit {
  font-size: 11.5px;
  line-height: 1.55;
  color: var(--text-2);
  padding: 5px 8px;
  border-radius: 5px;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: background 0.12s, border-color 0.12s;
  display: flex;
  gap: 6px;
  align-items: flex-start;
  text-align: left;
  background: transparent;
  border-top: none;
  border-right: none;
  border-bottom: none;
  width: 100%;
}

.search-hit:hover {
  background: var(--bg-2);
  border-left-color: var(--accent);
}

.search-hit-num {
  font-family: monospace;
  font-size: 9.5px;
  color: var(--text-3);
  flex-shrink: 0;
  padding-top: 2px;
  min-width: 16px;
}

.search-hit-text {
  flex: 1;
  min-width: 0;
}

.search-hit-text :deep(mark) {
  background: oklch(85% 0.12 95);
  color: var(--text);
  padding: 0 1px;
  border-radius: 2px;
  font-weight: 500;
}

.search-hit-more {
  font-size: 11px;
  color: var(--accent);
  padding: 4px 8px;
  cursor: pointer;
  border-radius: 5px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: background 0.12s;
  align-self: flex-start;
  background: transparent;
  border: none;
}

.search-hit-more:hover {
  background: var(--accent-bg);
}
</style>
