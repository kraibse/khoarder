<script setup lang="ts">
defineProps<{
  label: string
  active?: boolean
}>()

defineEmits<{
  click: []
}>()
</script>

<template>
  <button
    type="button"
    :class="[
      'h-[26px] px-[10px] rounded-full text-[11.5px] font-medium flex items-center gap-[5px]',
      'border transition-colors duration-[120ms]',
      active
        ? 'bg-accent-bg border-accent text-accent'
        : 'bg-surface border-line text-ink-2 hover:bg-surface-2 hover:text-ink',
    ]"
    @click="$emit('click')"
  >
    {{ label }}
  </button>
</template>
