import { ref, onMounted, onUnmounted, type Ref } from 'vue'

export function useReadProgress(scrollEl: Ref<HTMLElement | null>) {
  const progress = ref(0)

  function update() {
    const el = scrollEl.value
    if (!el) return
    const { scrollTop, scrollHeight, clientHeight } = el
    progress.value =
      scrollHeight <= clientHeight
        ? 100
        : Math.round((scrollTop / (scrollHeight - clientHeight)) * 100)
  }

  onMounted(() => {
    scrollEl.value?.addEventListener('scroll', update, { passive: true })
  })

  onUnmounted(() => {
    scrollEl.value?.removeEventListener('scroll', update)
  })

  return { progress }
}
