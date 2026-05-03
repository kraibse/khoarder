<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

defineProps<{
  x: number
  y: number
}>()

const emit = defineEmits<{
  close: []
  action: [label: string]
}>()

const menuEl = ref<HTMLElement | null>(null)

const items = [
  { label: 'Open', symbol: '→' },
  { label: 'Open in New Tab', symbol: '↗' },
  { label: 'Star', symbol: '☆' },
  { label: 'Copy link', symbol: '#' },
  { sep: true },
  { label: 'Edit tags', symbol: '⬡' },
  { label: 'Move to…', symbol: '→' },
  { sep: true },
  { label: 'Delete', symbol: '×', danger: true },
]

function onOutsideClick(e: MouseEvent) {
  if (menuEl.value && !menuEl.value.contains(e.target as Node)) {
    emit('close')
  }
}

onMounted(() => {
  // Defer so the triggering click doesn't immediately close the menu
  setTimeout(() => document.addEventListener('mousedown', onOutsideClick), 0)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onOutsideClick)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="slide-up" appear>
      <div
        ref="menuEl"
        class="fixed z-[100] bg-surface border border-line rounded-[9px] p-[5px] shadow-menu min-w-[160px]"
        :style="{ top: `${y}px`, left: `${x}px` }"
        @click.stop
      >
        <template v-for="(item, i) in items" :key="i">
          <div v-if="'sep' in item" class="h-px bg-line my-1" />
          <button
            v-else
            type="button"
            :class="[
              'w-full flex items-center gap-2 px-[10px] py-[7px] rounded-[6px]',
              'text-[13px] transition-colors duration-[100ms] text-left',
              item.danger
                ? 'text-danger hover:bg-[var(--danger-bg)]'
                : 'text-ink-2 hover:bg-surface-2 hover:text-ink',
            ]"
            @click="() => { emit('action', item.label); emit('close') }"
          >
            <span class="font-mono text-[11px] opacity-70 w-3.5 flex-shrink-0">{{ item.symbol }}</span>
            {{ item.label }}
          </button>
        </template>
      </div>
    </Transition>
  </Teleport>
</template>
