<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/atoms/AppIcon.vue'
import type { SuggestionOut } from '@/api/suggest'

const props = defineProps<{
  suggestion: SuggestionOut
  added: boolean
  adding: boolean
}>()

const emit = defineEmits<{
  add: [s: SuggestionOut]
  preview: [s: SuggestionOut]
}>()

const relevancePct = computed(() => Math.round((props.suggestion.relevance ?? 0) * 100))

function add() {
  if (props.added || props.adding) return
  emit('add', props.suggestion)
}

function preview() {
  emit('preview', props.suggestion)
}
</script>

<template>
  <div class="find-card" :class="{ added }">
    <div class="find-card-head">
      <span class="find-card-type">{{ suggestion.type }}</span>
      <div class="relevance-bar">
        <div class="relevance-bar-fill" :style="{ width: `${relevancePct}%` }" />
      </div>
      <span class="relevance-pct">{{ relevancePct }}%</span>
    </div>

    <div class="find-card-title">{{ suggestion.title }}</div>
    <div v-if="suggestion.excerpt" class="find-card-excerpt">{{ suggestion.excerpt }}</div>
    <div class="find-card-meta">{{ suggestion.source }}</div>

    <div class="find-card-actions">
      <button
        type="button"
        class="find-add-btn"
        :class="{ added }"
        :disabled="added || adding"
        @click="add"
      >
        <template v-if="added">✓ Added</template>
        <template v-else-if="adding">
          <span class="find-add-spinner" />
          Adding…
        </template>
        <template v-else>
          <AppIcon name="plus" :size="11" />
          Add to topic
        </template>
      </button>
      <button
        type="button"
        class="find-preview-btn"
        title="Open source in new tab"
        @click="preview"
      >
        <AppIcon name="external-link" :size="12" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.find-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 12px;
  margin-bottom: 8px;
  transition: border-color 0.15s, box-shadow 0.15s;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.find-card:hover {
  border-color: oklch(78% 0.012 65);
  box-shadow: 0 2px 8px oklch(16% 0.01 60 / 0.04);
}
.find-card.added {
  background: var(--bg-2);
  opacity: 0.7;
  border-style: dashed;
}

.find-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.find-card-type {
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-3);
}
.relevance-bar {
  flex: 1;
  height: 3px;
  background: var(--bg-3);
  border-radius: 2px;
  overflow: hidden;
  max-width: 60px;
}
.relevance-bar-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
}
.relevance-pct {
  font-size: 9.5px;
  font-family: monospace;
  color: var(--text-3);
}

.find-card-title {
  font-family: 'DM Serif Display', Georgia, serif;
  font-size: 14px;
  line-height: 1.3;
  color: var(--text);
  text-wrap: pretty;
}
.find-card-excerpt {
  font-size: 11.5px;
  color: var(--text-2);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.find-card-meta {
  font-size: 10.5px;
  color: var(--text-3);
}

.find-card-actions {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.find-add-btn {
  flex: 1;
  height: 28px;
  padding: 0 10px;
  border-radius: 6px;
  background: var(--text);
  color: var(--bg);
  font-size: 11.5px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  transition: background 0.12s;
  cursor: pointer;
  border: 1px solid var(--text);
}
.find-add-btn:hover:not(:disabled) {
  background: var(--accent);
  border-color: var(--accent);
}
.find-add-btn:disabled {
  cursor: default;
}
.find-add-btn.added {
  background: var(--bg-2);
  color: var(--text-3);
  border-color: var(--border);
}

.find-add-spinner {
  display: inline-block;
  width: 11px;
  height: 11px;
  border: 1.5px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.find-preview-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-3);
  cursor: pointer;
  transition: color 0.12s, border-color 0.12s;
}
.find-preview-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}
</style>
