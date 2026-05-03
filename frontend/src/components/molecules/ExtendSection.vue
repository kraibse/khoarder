<script setup lang="ts">
import AppIcon from '@/components/atoms/AppIcon.vue'

defineEmits<{
  'write-extension': []
  'attach-file': []
  'paste-excerpt': []
  'import-url': []
}>()
</script>

<template>
  <div class="mt-10 p-5 border-[1.5px] border-dashed border-line rounded-[10px] text-center bg-surface-2">
    <p class="text-[14px] font-medium text-ink-2 mb-[6px]">Extend this entry</p>
    <p class="text-xs text-ink-3 mb-[14px]">
      Append your own notes, attach new sources, or import related material.
      Extension is always user-triggered — nothing happens automatically.
    </p>
    <div class="flex flex-wrap gap-2 justify-center">
      <button
        type="button"
        class="h-8 px-[14px] rounded-[7px] text-xs font-medium border
               bg-ink text-surface border-ink hover:bg-accent hover:border-accent
               flex items-center gap-[5px] transition-colors duration-[120ms]"
        @click="$emit('write-extension')"
      >
        <AppIcon name="plus" :size="13" />
        Write extension
      </button>
      <button
        type="button"
        class="h-8 px-[14px] rounded-[7px] text-xs font-medium border
               bg-surface border-line text-ink-2 hover:border-accent hover:text-accent
               transition-colors duration-[120ms]"
        @click="$emit('attach-file')"
      >Attach file</button>
      <button
        type="button"
        class="h-8 px-[14px] rounded-[7px] text-xs font-medium border
               bg-surface border-line text-ink-2 hover:border-accent hover:text-accent
               transition-colors duration-[120ms]"
        @click="$emit('paste-excerpt')"
      >Paste excerpt</button>
      <button
        type="button"
        class="h-8 px-[14px] rounded-[7px] text-xs font-medium border
               bg-surface border-line text-ink-2 hover:border-accent hover:text-accent
               transition-colors duration-[120ms]"
        @click="$emit('import-url')"
      >Import URL</button>
    </div>
  </div>
</template>
