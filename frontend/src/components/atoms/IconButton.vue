<script setup lang="ts">
import AppIcon from './AppIcon.vue'

withDefaults(
  defineProps<{
    icon: string
    size?: number
    label?: string
    active?: boolean
  }>(),
  { size: 14 },
)

defineEmits<{
  click: [e: MouseEvent]
}>()
</script>

<template>
  <button
    type="button"
    :aria-label="label"
    :class="[
      'w-8 h-8 flex items-center justify-center rounded-[7px]',
      'transition-colors duration-[120ms]',
      active
        ? 'bg-surface-3 text-ink'
        : 'text-ink-3 hover:bg-surface-2 hover:text-ink',
    ]"
    @click="$emit('click', $event)"
  >
    <AppIcon :name="icon" :size="size" />
  </button>
</template>
