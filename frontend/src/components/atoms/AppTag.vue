<script setup lang="ts">
defineProps<{
  label: string
  variant?: 'default' | 'accent'
}>()
</script>

<template>
  <span
    :class="[
      'inline-flex items-center px-[7px] py-[2px] rounded-full text-[10.5px] border',
      variant === 'accent'
        ? 'bg-accent-bg border-accent text-accent'
        : 'bg-surface-2 border-line text-ink-3',
    ]"
  >
    {{ label }}
  </span>
</template>
