<script setup lang="ts">
import AppIcon from '@/components/atoms/AppIcon.vue'

defineProps<{
  title: string
  meta: string
  icon?: string
}>()
</script>

<template>
  <div class="bg-surface-2 border border-line rounded-lg px-4 py-[14px] my-6 flex gap-[14px] items-start">
    <div class="w-8 h-8 rounded-[7px] bg-surface-3 flex-shrink-0 flex items-center justify-center">
      <AppIcon :name="icon ?? 'file'" :size="14" class="text-ink-3" />
    </div>
    <div class="flex-1 min-w-0">
      <div class="text-[13px] font-medium text-ink mb-[3px]">{{ title }}</div>
      <div class="text-[11.5px] text-ink-3">{{ meta }}</div>
    </div>
  </div>
</template>
