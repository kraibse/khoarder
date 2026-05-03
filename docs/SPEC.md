# Knowledge Hoarder — Product & Engineering Spec

_Last updated: 2026-05-01 | Phase 1 complete_

---

## 1. Product Vision

Knowledge Hoarder is a self-hosted personal knowledge base. It is designed for a single
power user who collects, organises, and connects knowledge across multiple domains (topics).

**Core idea:** Each top-level topic is its own evolving knowledge base — not just a folder,
but a living collection that can grow through manual curation and AI-assisted extension.

**Not a wiki.** Not a note-taking app. A structured archive with editorial aesthetics and
optional AI augmentation — entirely under user control.

---

## 2. Product Goals

### 2.1 Knowledge organisation
- Topics as first-class containers (Cognitive Science, Climate Systems, etc.)
- Entry types: Article, Note, Paper, Excerpt, Reference
- Tags as cross-cutting metadata (not hierarchical)
- Backlinks: explicit connections between entries within and across topics

### 2.2 Capture & import
- URL import (fetch + metadata extraction + optional AI summarisation)
- Write note (free-form, Markdown)
- Upload file (PDF, EPUB, image — stored in persistent volume)
- Paste text (excerpt/quote with source attribution)

### 2.3 Exploration & reading
- Image-first masonry grid on main page
- Cards show: image, title, excerpt, tags, quick actions
- Article view: long-form reading, read-progress indicator
- Right sidebar: backlinks, related entries, source files, Q&A panel
- Filter by entry type; sort by date/title/backlink count
- Full-text search (PostgreSQL FTS → OpenSearch upgrade path)

### 2.4 AI augmentation (user-triggered only)
- Topic Q&A: ask a question answered from the knowledge base, powered by LM Studio
- Article extension: explicitly request AI to extend an article with additional content
- Both actions are ALWAYS user-triggered. No background AI processing.

### 2.5 Sharing & portability
- Export topic as JSON, Markdown, or ZIP (with files)
- Import previously exported topics
- Persistent file storage in Docker volume (portable between deployments)

---

## 3. Architecture

### 3.1 Service topology

```
[Browser]
    │
    ▼
[frontend: Nginx]        ← Vue 3 SPA, built to /dist
    │ /api/*  proxy_pass
    ▼
[backend: FastAPI]       ← REST API + LM Studio proxy
    │
    ├─── [db: PostgreSQL 16]      ← Entries, topics, tags, backlinks, files metadata
    │
    └─── [storage: bind volume]   ← Uploaded files (PDFs, images, etc.)
         /storage/uploads/
         /storage/exports/
```

Optional future service:
```
[opensearch]    ← Drop-in via services/search.py adapter
```

### 3.2 Frontend (Phase 1+)
- **Framework:** Vue 3 + Vite + TypeScript
- **Styling:** Tailwind CSS 3.4 + CSS custom properties
- **State:** Pinia (topics store, entries store, ui store)
- **Routing:** Vue Router 4 (`/` → HomeView, `/article/:id` → ArticleView)
- **Build:** Vite → static dist/ → served by Nginx
- **Docker:** Multi-stage build (Node build → Nginx serve)

### 3.3 Backend (Phase 2+)
- **Framework:** FastAPI (Python 3.12) with async handlers
- **ORM:** SQLAlchemy 2 + Alembic migrations
- **Validation:** Pydantic v2 schemas
- **File handling:** python-multipart, aiofiles
- **LM Studio client:** openai Python SDK (`base_url` = env var)
- **Docker:** Gunicorn + Uvicorn workers

### 3.4 Database schema (Phase 2 target)

```sql
topics      (id, name, color, description, created_at)
entries     (id, topic_id, type, title, excerpt, body, word_count,
             has_image, image_path, source, created_at, updated_at,
             search_vector tsvector)
tags        (id, name)
entry_tags  (entry_id, tag_id)
backlinks   (from_entry_id, to_entry_id, created_at)
files       (id, entry_id, filename, path, size_bytes, mime_type, created_at)
```

`search_vector` is a generated column (tsvector on title + excerpt + body).
Indexed with GIN for fast FTS queries.

---

## 4. Entry Types

| Type      | Description                                         | Typical image |
|-----------|-----------------------------------------------------|---------------|
| Article   | Long-form written piece (internal or imported)      | Often yes     |
| Note      | Short observation, reading note, idea               | Rarely        |
| Paper     | Academic paper / formal publication                 | Often yes     |
| Excerpt   | Quote or passage extracted from a source            | Sometimes     |
| Reference | Bookmark / URL / citation with minimal annotation   | Sometimes     |

---

## 5. API Design (Phase 2 target)

```
GET    /api/topics                     List all topics
POST   /api/topics                     Create topic
GET    /api/topics/:id/entries         List entries in topic (with filters)
POST   /api/topics/:id/entries         Create entry

GET    /api/entries/:id                Get entry detail
PATCH  /api/entries/:id                Update entry
DELETE /api/entries/:id                Delete entry
POST   /api/entries/:id/extend         User-triggered article extension (LLM)

GET    /api/entries/:id/backlinks      Backlinks to this entry
POST   /api/entries/:id/backlinks      Add backlink

POST   /api/files                      Upload file (multipart)
GET    /api/files/:id                  Download file

GET    /api/search?q=&topic=           Full-text search
POST   /api/qa                         Topic Q&A (proxies to LM Studio)
```

---

## 6. Search Strategy

**MVP (Phase 4):**
- PostgreSQL `tsvector` column on entries (title + excerpt + body, weighted)
- GIN index for fast lookups
- `GET /api/search?q=&topic=&type=` returns ranked results
- Managed via `app/services/search.py` with a clean interface

**Upgrade path (Phase 7+):**
1. Add OpenSearch service to docker-compose.yml
2. Implement `OpenSearchBackend` in `app/services/search.py`
3. Re-index existing entries (one-time migration script)
4. Switch env var `SEARCH_BACKEND=opensearch`
5. No changes to API routes or frontend

---

## 7. LM Studio Integration

LM Studio exposes an OpenAI-compatible API at `http://<host>:<port>/v1`.

**Q&A flow (Phase 5):**
1. User types a question in the Q&A panel
2. Frontend POSTs to `POST /api/qa`
3. Backend retrieves relevant entries (FTS or vector similarity)
4. Builds a grounded prompt: system context + top-N entry excerpts + question
5. Calls LM Studio `POST /v1/chat/completions`
6. Streams or returns the response
7. Frontend displays answer with grounding citation

**Extension flow (Phase 5):**
1. User clicks "Extend article" and confirms
2. Frontend POSTs to `POST /api/entries/:id/extend`
3. Backend reads the entry + related entries + topic context
4. Calls LM Studio with an extension prompt
5. Returns proposed extension text
6. User reviews and confirms before it's saved

**Configuration:**
- `LLM_BASE_URL`: e.g. `http://192.168.1.100:1234/v1`
- `LLM_MODEL`: e.g. `mistral-7b-instruct`
- Both read from environment; backend never hardcodes LM Studio details

---

## 8. Deployment (Phase 6 target)

```yaml
# docker-compose.yml services
frontend:   nginx:alpine   ports: 80:80
backend:    python:3.12    command: gunicorn app.main:app
db:         postgres:16    volume: postgres_data
# storage is a bind mount on host at ./storage/
```

Single `.env` file at project root:
```
POSTGRES_PASSWORD=...
LLM_BASE_URL=http://192.168.x.x:1234/v1
LLM_MODEL=mistral-7b-instruct
SECRET_KEY=...
```

---

## 9. Risks & Decisions

| Risk | Decision |
|------|----------|
| oklch() browser support | 93%+ global coverage (2025). Accepted. Add hex fallbacks in Tailwind config if needed |
| CSS column-count masonry can't control item order | Accepted for MVP. Fallback: Masonry.js or CSS grid subgrid if layout control needed |
| LM Studio on separate device = network dep | Graceful degradation: Q&A panel shows error state when LM Studio unreachable |
| PostgreSQL FTS has no semantic search | Accepted for MVP. Future: pgvector or OpenSearch ML |
| Single-user now, multi-user later | `created_by` FK will be nullable until auth is added. Auth = additive, not rewrite |
| Large file uploads via FastAPI | Acceptable for personal use. Future: pre-signed URLs for direct-to-storage upload |
