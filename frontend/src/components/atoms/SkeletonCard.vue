<script setup lang="ts">
defineProps<{ lines?: number }>()
</script>

<template>
  <div class="skeleton-card">
    <div class="flex items-center justify-between">
      <div class="sk-line" style="width: 50px; height: 8px" />
      <div class="sk-line" style="width: 40px; height: 8px" />
    </div>
    <div class="sk-line" style="width: 85%; height: 13px" />
    <div class="sk-line" style="width: 70%; height: 13px" />
    <div class="sk-line" style="width: 95%" />
    <div class="sk-line" style="width: 60%" />
    <div class="sk-line" style="width: 100%; height: 24px; margin-top: 4px" />
  </div>
</template>

<style scoped>
.skeleton-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 12px;
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sk-line {
  height: 10px;
  background: var(--bg-3);
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}

.sk-line::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, oklch(96% 0.008 65) 50%, transparent 100%);
  animation: skeleton-shimmer 1.4s infinite;
}

@keyframes skeleton-shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}
</style>
