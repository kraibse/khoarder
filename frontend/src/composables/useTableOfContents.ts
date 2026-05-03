import { ref, computed, onMounted, onUnmounted } from 'vue'

export interface Heading {
  level: number
  text: string
  slug: string
}

export function useTableOfContents(bodyRef: { value: string | undefined }) {
  const headings = computed<Heading[]>(() => {
    const body = bodyRef.value ?? ''
    const result: Heading[] = []
    const seenSlugs = new Set<string>()

    for (const line of body.split('\n')) {
      const match = line.match(/^(#{1,6})\s+(.+)$/)
      if (!match) continue
      const level = match[1].length
      const text = match[2].trim()
      let slug = text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-')
        .substring(0, 64)
      let uniqueSlug = slug
      let counter = 1
      while (seenSlugs.has(uniqueSlug)) {
        uniqueSlug = `${slug}-${counter}`
        counter++
      }
      seenSlugs.add(uniqueSlug)
      result.push({ level, text, slug: uniqueSlug })
    }

    return result
  })

  const activeSlug = ref<string | null>(null)
  let observer: IntersectionObserver | null = null

  function observe(container: HTMLElement) {
    if (observer) observer.disconnect()

    const headingElements = container.querySelectorAll('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]')
    if (headingElements.length === 0) return

    observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible.length > 0) {
          activeSlug.value = visible[0].target.id
        }
      },
      {
        root: container,
        rootMargin: '-10% 0px -70% 0px',
        threshold: 0,
      }
    )

    headingElements.forEach((el) => observer!.observe(el))
  }

  onUnmounted(() => {
    if (observer) observer.disconnect()
  })

  function scrollTo(slug: string, container: HTMLElement) {
    const el = container.querySelector(`[id="${slug}"]`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return { headings, activeSlug, observe, scrollTo }
}
