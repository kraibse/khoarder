export type EntryType = 'Article' | 'Note' | 'Paper' | 'Excerpt' | 'Reference'

export interface Topic {
  id: string
  slug: string
  name: string
  color: string
  description: string
  count: number
}

export interface Entry {
  id: string
  topicId: string | null
  type: EntryType
  hasImg: boolean
  imgUrl?: string
  imgH?: number
  imgColor?: string
  isStarred: boolean
  title: string
  excerpt: string
  tags: string[]
  date: string
  source?: string
  backlinkCount?: number
  headline?: string  // FTS snippet with <mark> highlights, present only in search results
}

export interface ArticleDetail extends Entry {
  body: string
  wordCount: number
  readTime: string
  imgColor: string
  imgUrl?: string
  source: string
  isStarred: boolean
}

export interface Backlink {
  id: string
  relationId: string
  title: string
  type: EntryType
  refs: number
}

export interface RelatedEntry {
  id: string
  relationId: string
  title: string
  type: EntryType
  imgColor: string
}

export interface SourceFile {
  id: string
  name: string
  ext: string
  size: string
  date: string
}

export interface QAMessage {
  role: 'user' | 'assistant'
  text: string
  sources?: Array<{ id: string; title: string; type: string; snippet: string }>
}

export const SMART_VIEWS = [
  { id: 'recent', name: 'Recently Added', icon: 'clock' },
  { id: 'untagged', name: 'Untagged', icon: 'tag-off' },
  { id: 'no-excerpt', name: 'Missing Excerpt', icon: 'file-x' },
  { id: 'backlinked', name: 'Most Backlinked', icon: 'link' },
] as const
