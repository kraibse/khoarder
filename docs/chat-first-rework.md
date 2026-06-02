# Chat-First Rework — Transformation Roadmap

> Goal: Transform Knowledge Hoarder from a "browse-and-read" knowledge base into a **chat-first deep research tool** where conversations become structured knowledge. Inspired by [memory-os](https://github.com/ClaudioDrews/memory-os), but lean and responsive.

## Design Decisions (Locked)

| Decision | Choice | Rationale |
|---|---|---|
| Conversation granularity | Per-topic + global unscoped | Topics are the natural research boundary; global chats for cross-topic synthesis |
| Message → Entry linking | Manual "Save as note/article" with one-click | Keeps user agency; auto-extraction optional later |
| Memory scope | Per-topic + global system memory | Topic memories for domain context; global for user preferences and cross-cutting facts |
| Vector search | **Deferred** to Phase E | Postgres FTS + proper context assembly is sufficient for A-D; pgvector can be added later without schema breakage |
| Ground truth hierarchy | **Adopted** from memory-os Layer 7 | Retrieved context explicitly ranked above model assumptions in all prompts |
| Auto-categorization | Keep existing `_classify_entry()` | Already works when `topic_id=null` on entry creation |

## What Already Works (Don't Rebuild)

| Component | What It Does | Reuse Plan |
|---|---|---|
| `QAPanel` + `useQA` | Topic-scoped Q&A with source citations | Evolve into persistent `ChatView`; keep citation blocks |
| `AssistPanel` | Summarize / tags / related / extend | Wire actions into chat output ("Should I summarize these 3 entries?") |
| Postgres FTS (`SearchBackend`) | Full-text search with `<mark>` highlights, `ts_headline` fragments | Keep as primary retrieval; vector backend can be swapped later |
| URL import ladder | Static → playwright → camoufox → browserless | Unchanged — still the primary content acquisition pipeline |
| `Entry` / `Topic` / `Relation` / `Tag` | Structured knowledge graph with backlinks | Extend with `conversation_id` FK; don't replace |
| `FindMoreSidebar` | Multi-provider discovery (Wikipedia, arXiv, Semantic Scholar, OpenAlex, HN) | Unchanged |
| `Config` table | Runtime key-value store for LLM settings | Extend with chat-related config (`chat_context_entries`, `chat_temperature`) |

## What's Missing (The Work)

### 1. Persistent Conversations
**Current:** `QAPanel` messages are `ref<QAMessage[]>` — in-memory, lost on unmount.
**Needed:** Backend `Conversation` and `Message` tables with full CRUD lifecycle.

### 2. Multi-Turn Context
**Current:** `ask_question()` is single-shot — no conversation history sent to LM Studio.
**Needed:** `send_message()` loads full conversation history, prepends it to the LLM context window.

### 3. Chat-to-Entry Pipeline
**Current:** `assist_extend` returns text for manual append. No auto-save workflow.
**Needed:** After a chat turn, offer "Save as note/article" → creates `Entry` with `conversation_id` FK. Optionally auto-extract facts on save.

### 4. LLM Memory / Long-Term Context
**Current:** System prompt is the only persistent context. No fact store.
**Needed:** A `Memory` model (per-topic or global) that the LLM can read/write during conversations.

### 5. Overview Article Generation
**Current:** No automated "build me an overview from these entries" feature.
**Needed:** A user-triggered "Generate overview" action that feeds selected/top entries to LM Studio with a synthesis prompt, creates a new `Entry`, and auto-links related entries.

### 6. Ground Truth Hierarchy
**Current:** Q&A prompt doesn't explicitly rank retrieved context above model assumptions.
**Needed:** Update `qa.py` prompts with memory-os Layer 7 pattern: "You MUST rely on the provided context. Do not hallucinate beyond it."

---

## Implementation Phases

### Phase A: Persistent Chat Foundation
**Goal:** Conversations survive reloads. Multi-turn chat with full history as LLM context.

1. **Backend models** (`backend/app/models/`)
   - `Conversation` — `id` (UUID PK), `topic_id` (FK → Topic, nullable for global), `title`, `created_at`, `updated_at`
   - `Message` — `id` (UUID PK), `conversation_id` (FK → Conversation, cascade delete), `role` (`user` | `assistant` | `system`), `content`, `created_at`, `entry_id` (FK → Entry, nullable — links generated content)
   - Alembic migration

2. **Backend schemas** (`backend/app/schemas/`)
   - `ConversationCreate`, `ConversationOut`, `ConversationListOut`
   - `MessageCreate`, `MessageOut`, `ConversationWithMessagesOut`

3. **Backend service** (`backend/app/services/chat.py`)
   - `create_conversation(db, topic_id=None, title="New Conversation")`
   - `get_conversation(db, conversation_id)` — with messages eager-loaded
   - `list_conversations(db, topic_id=None)` — ordered by `updated_at` desc
   - `send_message(db, conversation_id, content)` — loads all prior messages + topic entries via FTS → assembles context → calls LM Studio with full history → saves user + assistant messages → returns `MessageOut` + sources
   - `delete_message(db, message_id)` — cascade within conversation
   - `update_conversation(db, conversation_id, title=None)` — rename
   - `delete_conversation(db, conversation_id)`

4. **Backend API** (`backend/app/api/`)
   - `POST /api/conversations` — create
   - `GET /api/conversations` — list (optionally filter by `topic_id` query param)
   - `GET /api/conversations/{id}` — get with messages
   - `PATCH /api/conversations/{id}` — rename
   - `DELETE /api/conversations/{id}` — delete
   - `POST /api/conversations/{id}/messages` — send message
   - `DELETE /api/conversations/{id}/messages/{message_id}` — delete message

5. **Frontend store** (`frontend/src/stores/conversations.ts`)
   - Pinia store: `conversations`, `activeConversation`, `messages`
   - `loadConversations(topicId?)`, `createConversation(topicId?)`, `loadConversation(id)`, `sendMessage(conversationId, content)`, `deleteMessage(id)`, `deleteConversation(id)`

6. **Frontend view** (`frontend/src/views/ChatView.vue`)
   - Full-page chat UI (not sidebar panel)
   - Route: `/chat/:topicId?` — if `topicId` is absent, global chat
   - Message list with user/assistant styling (reuse QAPanel patterns)
   - Input box at bottom with send button
   - Citation blocks for assistant messages (reuse `CitationBlock`)
   - Sidebar: conversation list for current topic (or all conversations if global)
   - "New conversation" button
   - Loading states, error handling (503 when LM Studio not configured)

7. **Frontend routing** (`frontend/src/router/index.ts`)
   - Add `/chat/:topicId?` → `ChatView`
   - Add nav link in `AppSidebar`

8. **Update `AppSidebar`**
   - Add "Chat" nav item with conversation count badge per topic

### Phase B: Chat-to-Entry Capture
**Goal:** Save chat output as structured entries. Optional fact extraction.

1. **Backend**
   - Add `conversation_id` nullable FK to `Entry` model
   - `POST /api/entries/from-chat` — accepts `message_id` or `conversation_id`, creates `Entry` (type=`Note` or `Article`), pre-fills title/body from message content, links back to conversation
   - Update `qa.py` / `chat.py` to support `ground_truth_hierarchy` — inject instruction that retrieved context is authoritative

2. **Frontend**
   - "Save as note" / "Save as article" buttons on each assistant message in `ChatView`
   - Pre-fills `EntryEditModal` with chat content; user edits before save
   - Toast notification on successful save with link to new entry

3. **Optional: Fact extraction service** (`backend/app/services/extract.py`)
   - `extract_facts(db, entry_id)` — sends entry body to LM Studio with extraction prompt, writes `Fact` rows
   - `Fact` model: `id`, `entry_id`, `content`, `type` (`entity` | `relation` | `claim` | `question`), `trust_score` (default 1.0), `created_at`
   - Triggered manually via "Extract facts" button on saved entries, or optionally on every chat-save

### Phase C: Overview Generation & Expansion
**Goal:** One-click synthesis of topic knowledge into a coherent overview article with automatic backlinking.

1. **Backend**
   - `POST /api/topics/{id}/generate-overview` — service in `backend/app/services/overview.py`
     - Load top N entries for topic (by `is_starred`, recency, or user selection)
     - Assemble synthesis prompt with ground truth hierarchy
     - Call LM Studio → get markdown overview
     - Create `Entry` with type=`Article`, title=`Overview: {Topic Name}`, body=overview
     - Run backlink detection on new body
     - Return `EntryOut` with related entries
   - `POST /api/entries/{id}/suggest-related` — LLM suggests `Relation` edges to existing entries; user confirms batch

2. **Frontend**
   - "Generate overview" button in `HomeView` topic strip and `ChatView` header
   - Progress modal while LLM works
   - Result opens in `ArticleView` with "Suggested links" panel — user clicks to approve each suggested `Relation`

### Phase D: Memory Layer (Ground Truth)
**Goal:** Persistent facts the LLM recalls across sessions.

1. **Backend**
   - `Memory` model: `id`, `topic_id` (nullable), `content`, `type` (`fact` | `preference` | `context`), `trust_score`, `created_at`, `updated_at`
   - `memory.py` service: `recall_memories(db, topic_id, query, limit)` — FTS on memory content, returns ranked list
   - `POST /api/memories` — create (manually or from chat)
   - `GET /api/memories` — list (topic-scoped or global)
   - `PATCH /api/memories/{id}` — edit
   - `DELETE /api/memories/{id}`
   - Update `chat.py` to inject recalled memories into system prompt
   - Update `qa.py` to inject recalled memories + rank as authoritative

2. **Frontend**
   - "Memories" panel in `ChatView` sidebar — shows what the LLM "remembers" about this topic
   - Pin / edit / delete memory actions
   - "Add memory" button from any assistant message ("Remember this fact")

### Phase E: Vector Search (Deferred)
**Goal:** Semantic similarity beyond keyword matching.

- Add `embedding` column (vector) to `Entry` via pgvector
- Implement `VectorSearchBackend(SearchBackend)` in `services/search.py`
- Background job to compute embeddings for existing entries
- Swap `_backend` to hybrid (vector + FTS fallback)

---

## Prompt Engineering Patterns (Adopted from memory-os)

### Ground Truth Hierarchy
Inject into every LLM call that uses retrieved context:

```
You are a research assistant with access to the user's knowledge base.
The context provided below comes from the user's own curated sources.
You MUST rely on this context as ground truth. Do not contradict it.
If the context does not answer the question, say so explicitly.
```

### Context Assembly (chat.py)
For each `send_message` call:
1. Load all prior messages in conversation (ordered by `created_at`)
2. If `topic_id` is set: run FTS on topic entries with the user's message as query → top-N results
3. If global chat: run FTS across all entries
4. Assemble `system` message with ground truth hierarchy + retrieved context
5. Prepend conversation history as `user`/`assistant` pairs
6. Append current user message
7. Call LM Studio
8. Save assistant response

### Context Budget
- Max conversation history: 10 most recent messages (configurable via `chat_context_entries` in Config table)
- Max retrieved entries: 5 (configurable)
- Max memory injection: 3 per-topic memories + 3 global memories
- Total token budget enforced by `_chat()` helper; truncate oldest history if exceeded

---

## Files to Create / Modify

### New Files
```
backend/app/models/conversation.py
backend/app/models/message.py
backend/app/models/fact.py
backend/app/models/memory.py
backend/app/schemas/conversation.py
backend/app/schemas/message.py
backend/app/services/chat.py
backend/app/services/extract.py
backend/app/services/overview.py
backend/app/services/memory.py
backend/app/api/conversations.py
frontend/src/stores/conversations.ts
frontend/src/views/ChatView.vue
frontend/src/composables/useChat.ts
frontend/src/components/molecules/ChatMessage.vue
frontend/src/components/organisms/ChatSidebar.vue
```

### Modified Files
```
backend/app/models/entry.py          # add conversation_id FK
backend/app/models/__init__.py        # import new models
backend/app/schemas/entry.py          # add conversation_id field
backend/app/services/qa.py            # ground truth hierarchy, memory injection
backend/app/api/router.py             # mount conversations router
backend/app/api/entries.py            # add from-chat endpoint
backend/app/api/topics.py           # add generate-overview endpoint
backend/app/core/config.py          # add chat_context_entries, chat_temperature
frontend/src/router/index.ts        # add /chat route
frontend/src/components/organisms/AppSidebar.vue  # add Chat nav
frontend/src/stores/entries.ts      # add from-chat creation helper
frontend/src/views/HomeView.vue     # add Generate overview button
frontend/src/views/ArticleView.vue  # add Suggested links panel
```

---

## Rollback Plan

If any phase breaks existing functionality:
1. Conversation/Message tables are additive — no migration touches existing Entry/Topic data
2. `conversation_id` on Entry is nullable — existing entries unaffected
3. New routes (`/chat`, `/api/conversations`) are isolated — old routes untouched
4. Ground truth hierarchy is a prompt change, not a schema change — easily reverted

---

## Success Criteria

- [ ] Phase A: Conversations persist across reloads; multi-turn chat feels natural; LM Studio context includes history
- [ ] Phase B: Any assistant message can be saved as an Entry in ≤ 2 clicks; saved entries link back to their conversation
- [ ] Phase C: "Generate overview" produces a coherent markdown article from topic entries; suggested backlinks are ≥ 70% relevant
- [ ] Phase D: LLM recalls pinned memories in new conversations; memory panel is editable
- [ ] Phase E: (Deferred) Vector search returns semantically relevant results beyond keyword matches

---

*Started: 2026-06-02*
