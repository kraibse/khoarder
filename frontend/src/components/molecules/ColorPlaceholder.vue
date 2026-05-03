<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    color: string
    height?: number | string
    label?: string
  }>(),
  { label: 'article image' },
)

// Unique pattern ID to avoid SVG id collisions in masonry
const uid = Math.random().toString(36).slice(2, 7)
</script>

<template>
  <div
    :style="{
      background: color,
      height: typeof height === 'number' ? `${height}px` : height,
    }"
    class="relative w-full overflow-hidden flex items-center justify-center"
  >
    <!-- Subtle diagonal stripe texture -->
    <svg
      class="absolute inset-0 w-full h-full opacity-[0.07]"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <pattern
          :id="`stripe-${uid}`"
          width="8"
          height="8"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line x1="0" y1="0" x2="0" y2="8" stroke="white" stroke-width="2" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" :fill="`url(#stripe-${uid})`" />
    </svg>

    <span
      v-if="label"
      class="relative z-10 font-mono text-[10px] opacity-50 text-center px-3"
      style="color: oklch(30% 0.01 60)"
    >
      {{ label }}
    </span>
  </div>
</template>
