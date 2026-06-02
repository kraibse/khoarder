<script setup lang="ts">
withDefaults(
  defineProps<{
    name: string
    size?: number
  }>(),
  { size: 16 },
)

// SVG inner HTML keyed by icon name.
// Stroke icons use currentColor stroke (SVG-level fill="none").
// Filled icons explicitly set fill="currentColor" and stroke="none" on their elements.
const icons: Record<string, string> = {
  // ── Navigation ──────────────────────────────────────────────────────────────
  home: `<path d="M2 6.5L8 2l6 4.5V14a1 1 0 01-1 1H3a1 1 0 01-1-1V6.5z"/><path d="M6 15v-6h4v6"/>`,
  inbox: `<path d="M2 10h3l1.5 2h3L11 10h3V4a1 1 0 00-1-1H3a1 1 0 00-1 1v6z"/>`,
  book: `<path d="M3 2h8a1 1 0 011 1v10a1 1 0 01-1 1H3"/><path d="M3 2a1 1 0 00-1 1v10a1 1 0 001 1"/><path d="M6 6h4M6 9h4"/>`,
  star: `<polygon points="8,2 10,6 14,6.5 11,9.5 12,14 8,11.5 4,14 5,9.5 2,6.5 6,6"/>`,
  'star-filled': `<polygon points="8,2 10,6 14,6.5 11,9.5 12,14 8,11.5 4,14 5,9.5 2,6.5 6,6" fill="currentColor" stroke="none"/>`,
  tag: `<path d="M9 2H14v5l-7 7-5-5 7-7z"/><circle cx="12" cy="4.5" r="0.75" fill="currentColor" stroke="none"/>`,
  settings: `<circle cx="8" cy="8" r="2.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41"/>`,
  download: `<path d="M8 2v8M5 7l3 3 3-3"/><path d="M2 12h12"/>`,
  upload: `<path d="M8 10V2M5 5l3-3 3 3"/><path d="M2 12h12"/>`,
  clock: `<circle cx="8" cy="8" r="6"/><path d="M8 5v3.5l2 2"/>`,
  link: `<path d="M6.5 9.5a4.24 4.24 0 006 0l2-2a4.24 4.24 0 00-6-6l-1 1"/><path d="M9.5 6.5a4.24 4.24 0 00-6 0l-2 2a4.24 4.24 0 006 6l1-1"/>`,
  'file-x': `<path d="M9 2H4a1 1 0 00-1 1v10a1 1 0 001 1h8a1 1 0 001-1V6l-4-4z"/><path d="M9 2v4h4"/><path d="M6 9l4 3M10 9l-4 3"/>`,
  'tag-off': `<path d="M9 2H14v5l-7 7-5-5 4-4"/><line x1="2" y1="2" x2="14" y2="14"/>`,
  // ── Topbar ──────────────────────────────────────────────────────────────────
  menu: `<path d="M2 4h12M2 8h12M2 12h12"/>`,
  search: `<circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14"/>`,
  plus: `<path d="M8 3v10M3 8h10"/>`,
  'chevron-right': `<path d="M6 4l4 4-4 4"/>`,
  'chevron-down': `<path d="M4 6l4 4 4-4"/>`,
  // ── Grid density ────────────────────────────────────────────────────────────
  'grid-2': `<rect x="1" y="1" width="5" height="12" rx="1" fill="currentColor" stroke="none"/><rect x="8" y="1" width="5" height="12" rx="1" fill="currentColor" stroke="none"/>`,
  'grid-3': `<rect x="1" y="1" width="3.5" height="12" rx="0.8" fill="currentColor" stroke="none"/><rect x="5.25" y="1" width="3.5" height="12" rx="0.8" fill="currentColor" stroke="none"/><rect x="9.5" y="1" width="3.5" height="12" rx="0.8" fill="currentColor" stroke="none"/>`,
  'grid-4': `<rect x="0.5" y="1" width="2.5" height="12" rx="0.7" fill="currentColor" stroke="none"/><rect x="3.83" y="1" width="2.5" height="12" rx="0.7" fill="currentColor" stroke="none"/><rect x="7.17" y="1" width="2.5" height="12" rx="0.7" fill="currentColor" stroke="none"/><rect x="10.5" y="1" width="2.5" height="12" rx="0.7" fill="currentColor" stroke="none"/>`,
  // ── Cards ───────────────────────────────────────────────────────────────────
  'three-dots': `<circle cx="4" cy="8" r="1.2" fill="currentColor" stroke="none"/><circle cx="8" cy="8" r="1.2" fill="currentColor" stroke="none"/><circle cx="12" cy="8" r="1.2" fill="currentColor" stroke="none"/>`,
  // ── Article page ─────────────────────────────────────────────────────────────
  'arrow-left': `<path d="M10 4L6 8l4 4"/>`,
  copy: `<path d="M11 4H3v10h8V4zM5 4V2h8v10h-2"/>`,
  share: `<path d="M10 2l4 4-4 4M14 6H6a4 4 0 000 8h1"/>`,
  edit: `<path d="M11 2l3 3-9 9H2v-3L11 2z"/>`,
  send: `<path d="M2 8l12-6-6 12V8H2z"/>`,
  trash: `<path d="M3 4h10M5 4V3h6v1M6 7v5M10 7v5M4 4l1 9h6l1-9"/>`,
  file: `<path d="M9 2H4a1 1 0 00-1 1v10a1 1 0 001 1h8a1 1 0 001-1V6l-4-4zM9 2v4h4"/>`,
  'file-plus': `<path d="M9 2H4a1 1 0 00-1 1v10a1 1 0 001 1h8a1 1 0 001-1V6l-4-4zM9 2v4h4"/><path d="M6 10h4M8 8v4"/>`,
  // ── Misc ─────────────────────────────────────────────────────────────────────
  alert: `<path d="M8 2L1 14h14L8 2z"/><line x1="8" y1="7" x2="8" y2="10"/><circle cx="8" cy="12.5" r="0.6" fill="currentColor" stroke="none"/>`,
  server: `<rect x="2" y="2" width="12" height="5" rx="1"/><rect x="2" y="9" width="12" height="5" rx="1"/><circle cx="11.5" cy="4.5" r="0.8" fill="currentColor" stroke="none"/><circle cx="11.5" cy="11.5" r="0.8" fill="currentColor" stroke="none"/>`,
  globe: `<circle cx="8" cy="8" r="6"/><path d="M8 2c-2 2-3 3.6-3 6s1 4 3 6M8 2c2 2 3 3.6 3 6s-1 4-3 6"/><path d="M2.5 6h11M2.5 10h11"/>`,
  filter: `<path d="M2 4h12M4 8h8M6 12h4"/>`,
  sort: `<path d="M2 5h12M4 8h8M6 11h4"/>`,
  x: `<path d="M4 4l8 8M12 4l-8 8"/>`,
  'external-link': `<path d="M9 2h5v5"/><path d="M14 2L7 9"/><path d="M12 9v4a1 1 0 01-1 1H3a1 1 0 01-1-1V5a1 1 0 011-1h4"/>`,
  sparkle: `<path d="M5 2l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2z"/><path d="M11 8l1 1.5 1.5 1-1.5 1-1 1.5-1-1.5-1.5-1 1.5-1 1-1.5z"/>`,
  refresh: `<path d="M2 8a6 6 0 0112 0"/><path d="M14 8l-2-2 2-2"/>`,
}
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    v-html="icons[name] ?? icons.book"
  />
</template>
