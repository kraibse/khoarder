import { ref, onMounted, onUnmounted, type Ref } from 'vue'

export function useReadProgress(scrollEl: Ref<HTMLElement | null>, startOffset: Ref<number> = ref(0)) {
  const progress = ref(0)

  function update() {
    const el = scrollEl.value
    if (!el) return
    const { scrollTop, scrollHeight, clientHeight } = el
    const start = startOffset.value
    const readable = scrollHeight - clientHeight - start
    if (readable <= 0) {
      progress.value = scrollTop > start ? 100 : 0
      return
    }
    if (scrollTop <= start) {
      progress.value = 0
      return
    }
    progress.value = Math.min(100, Math.round(((scrollTop - start) / readable) * 100))
  }

  onMounted(() => {
    scrollEl.value?.addEventListener('scroll', update, { passive: true })
  })

  onUnmounted(() => {
    scrollEl.value?.removeEventListener('scroll', update)
  })

  return { progress }
}
