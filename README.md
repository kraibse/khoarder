<div align="center">
  <h1>Knowledge Hoarder</h1>

  <img width="128" src="assets/khoarder.svg" />

  <br/>

  <img alt="Docker Badge" src="https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Vue%20js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D" />
  <img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue" />

  <br/>

  <img alt="GitHub Actions Workflow Status" src="https://img.shields.io/github/actions/workflow/status/kraibse/khoarder/ci.yml">

  <br/><br/>

  <p>A self-hosted personal knowledge base. Topic-driven, image-first, AI-augmented on demand.</p>
</div>

<br/>

<p align="center">
  <img src="assets/khoarder-preview.png" />
</p>


## Running the app

### Option 1 — Local (no Docker, fastest for development)

Requires: PostgreSQL 16, Python 3.12+, Node.js 22+ with pnpm.

```bash
# 1. Start PostgreSQL (or use an existing instance)
docker run --rm \
  -e POSTGRES_USER=khoarder \
  -e POSTGRES_PASSWORD=dev \
  -e POSTGRES_DB=knowledge_hoarder \
  -p 5432:5432 \
  postgres:16-alpine

# 2. Backend  (auto-creates tables + seeds demo data on first run)
cd backend
pip install -r requirements.txt
DATABASE_URL=postgresql+asyncpg://khoarder:dev@localhost/knowledge_hoarder \
  uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend
pnpm install
pnpm dev
# → http://localhost:5173
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so no extra config is needed.

---

### Option 2 — Docker Compose (development, hot-reload)

Requires: Docker with Compose V2.

```bash
docker compose -f docker-compose.dev.yml up --build
```

| Service   | URL                        |
|-----------|----------------------------|
| Frontend  | http://localhost:5173      |
| Backend   | http://localhost:8000      |
| API docs  | http://localhost:8000/docs |
| Postgres  | localhost:5432             |

Source files are mounted into the containers so changes reload automatically:
- Frontend: any change in `src/` triggers Vite HMR in the browser.
- Backend: any change in `backend/app/` triggers uvicorn to reload.

No `.env` file is needed — dev credentials are hardcoded in the compose file.

---

### Option 3 — Docker Compose (self-hosted / production)

```bash
# 1. Copy and fill in the config
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD and update DATABASE_URL to match

# 2. Build and start
docker compose up -d --build
# → http://localhost (port 80)
```

The frontend is served by nginx on port 80. nginx proxies `/api/` requests to the backend. The backend runs under gunicorn with 2 uvicorn workers.

To change the port: set `FRONTEND_PORT=8080` in `.env`.

---

## Data persistence

All persistent data is stored in Docker volumes:

| Data | Dev compose | Prod compose |
|------|-------------|--------------|
| PostgreSQL | named volume `postgres_data_dev` | named volume `postgres_data` |
| Uploaded files | host directory `./storage/` | named volume `storage` |

In the dev compose, uploaded files land in `./storage/` in the project root so they survive
container rebuilds and are visible on the host. In the prod compose they go into a named volume.

To back up the prod database:
```bash
docker compose exec db pg_dump -U khoarder knowledge_hoarder > backup.sql
```

To back up uploaded files:
```bash
docker run --rm -v knowledge-hoarder_storage:/data -v $(pwd):/backup \
  alpine tar czf /backup/storage-backup.tar.gz /data
```

---

## Project structure

```
knowledge-hoarder/
├── frontend/               Vue 3 + Vite + Tailwind + Pinia
│   ├── src/
│   │   ├── api/            HTTP client + typed API wrappers
│   │   ├── components/     Atoms → Molecules → Organisms (atomic design)
│   │   ├── composables/    useReadProgress, useQA
│   │   ├── data/mock.ts    TypeScript types + SMART_VIEWS constant
│   │   ├── stores/         Pinia: topics, entries, ui
│   │   └── views/          HomeView, ArticleView
│   ├── Dockerfile          Multi-stage: dev (Vite) + prod (nginx)
│   └── nginx.conf          SPA fallback + /api proxy to backend
├── backend/                FastAPI + SQLAlchemy + Alembic
│   └── app/
│       ├── api/            Route handlers (topics, entries, attachments)
│       ├── core/           Pydantic Settings (config.py)
│       ├── db/             Async engine + session factory
│       ├── models/         SQLAlchemy ORM models
│       ├── schemas/        Pydantic response schemas
│       ├── services/       Business logic (no DB calls in routes)
│       └── seed.py         Idempotent demo data seeder
│   └── Dockerfile          Multi-stage: dev (uvicorn --reload) + prod (gunicorn)
├── storage/                Uploaded files when using the dev compose
│   ├── uploads/            {entry_id}/{attachment_id}_{filename}
│   └── exports/            Reserved for future export caching
├── docker-compose.yml      Production / self-hosted stack
├── docker-compose.dev.yml  Development stack (hot-reload, standalone)
├── .env.example            Template for production environment variables
└── docs/SPEC.md            Full product + engineering spec
```

---

## API

Interactive docs at `http://localhost:8000/docs` when the backend is running.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/topics` | List all topics with entry counts |
| GET | `/api/topics/{slug_or_id}` | Single topic |
| POST | `/api/topics` | Create a new topic (name, description, color) |
| PATCH | `/api/topics/{slug_or_id}` | Update topic fields |
| GET | `/api/topics/{slug_or_id}/tags` | Tags used in a topic |
| GET | `/api/topics/{slug_or_id}/export` | Export topic + entries as JSON |
| POST | `/api/topics/{slug_or_id}/import` | Import a previously exported JSON |
| GET | `/api/entries` | List entries (`?topic_id= &type= &sort= &q= &tag=`) |
| GET | `/api/entries/{id}` | Full article detail |
| POST | `/api/entries` | Create a new entry (note, reference, …) |
| PATCH | `/api/entries/{id}` | Update entry fields (title, body, tags, type, …) |
| DELETE | `/api/entries/{id}` | Delete an entry (cascades relations + attachments) |
| POST | `/api/entries/import-url` | Import article from URL (extracts title + excerpt) |
| GET | `/api/entries/{id}/backlinks` | Entries that link to this one (auto-detected from `[[Title]]`) |
| GET | `/api/entries/{id}/related` | Manually related entries |
| GET | `/api/entries/{id}/suggestions` | Tag-overlap suggestions for related entries |
| GET | `/api/entries/{id}/attachments` | Source files attached to entry |
| POST | `/api/entries/{id}/attachments` | Upload a file attachment (multipart/form-data) |
| GET | `/api/attachments/{id}/download` | Download an attachment |
| DELETE | `/api/attachments/{id}` | Delete an attachment |
| POST | `/api/relations` | Link two entries as "related" |
| DELETE | `/api/relations/{id}` | Remove a relation |
| GET | `/api/tags` | All tag names (for sidebar) |
| GET | `/api/qa/status` | Whether LM Studio is configured + model name |
| POST | `/api/qa` | Topic-scoped Q&A with knowledge retrieval |
| POST | `/api/assist/summarize` | Summarize an entry (user-triggered) |
| POST | `/api/assist/tags` | Suggest tags for an entry |
| POST | `/api/assist/related` | Suggest related entries by content similarity |
| POST | `/api/assist/extend` | Draft an article extension (returned, not auto-applied) |
| GET | `/health` | Health check |

When `q` is provided, results are ranked by PostgreSQL `ts_rank_cd` (relevance) instead of date. The `sort` parameter is still respected for non-search queries.

Sort options for `?sort=`: `date_desc` (default), `date_asc`, `title_asc`, `backlinks_desc`

---

## LM Studio integration (Phase 7)

All AI features are strictly user-triggered — nothing runs automatically.

### Setup
1. Install [LM Studio](https://lmstudio.ai) on any device on your local network.
2. Load a model and open **Developer → Local Server → Start server** (default port: 1234).
3. In `.env`, set:
   ```
   LLM_BASE_URL=http://192.168.1.100:1234/v1
   LLM_MODEL=mistral-7b-instruct-v0.2
   ```
4. Restart the backend container or server. The green dot in the Q&A panel will light up.

### Topic Q&A
The **Topic Q&A** panel in the article sidebar lets you ask questions about the active topic. The backend retrieves the most relevant entries using PostgreSQL FTS, assembles them as context, and sends the question + context to LM Studio. Each answer shows the source entries it was grounded in.

### Article assistance
The **AI Assist** section in the article sidebar provides four user-triggered actions:

| Action | What it does |
|--------|-------------|
| **Summarize** | Generates a 2-3 sentence summary of the article body |
| **Suggest tags** | Proposes new tags; click a tag to apply it immediately |
| **Suggest related** | Finds topically similar entries; click "Link" to create a relation |
| **Draft extension** | Generates continuation text; opens the Extend modal pre-filled — you review and save |

### Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_BASE_URL` | LM Studio base URL ending in `/v1` | *(disabled if empty)* |
| `LLM_MODEL` | Model name as shown in LM Studio | `local-model` |
| `LLM_TIMEOUT` | Request timeout in seconds | `60` |
| `LLM_CONTEXT_ENTRIES` | Entries sent as context per Q&A | `5` |

---

## Search (Phase 6)

The search box in the top bar queries the backend via `GET /api/entries?q=...`. Results are ranked by PostgreSQL full-text search (`ts_rank_cd`) with a one-sentence highlighted snippet shown on each card.

### Query syntax (`websearch_to_tsquery`)
| Example | Matches |
|---------|---------|
| `neural network` | entries containing both words |
| `"machine learning"` | the exact phrase |
| `-python` | exclude entries containing "python" |
| `rust OR go` | either word |

### Scope toggle
By default search is scoped to the active topic. The **All topics** button (appears when the search box has text) switches to searching across the entire knowledge base.

### What is searched
Title, excerpt, full body text, and source label — all weighted equally with the title receiving a natural boost (repeated in the search document).

### OpenSearch upgrade path
The search logic lives exclusively in `backend/app/services/search.py` behind a `SearchBackend` abstract class. To swap in OpenSearch:
1. `pip install opensearch-py` and set `OPENSEARCH_URL` env var.
2. Implement `OpenSearchBackend(SearchBackend)` — index entries on write, query via the OpenSearch API, return `(entry_id, highlight)` pairs, load `Entry` objects from Postgres by ID.
3. Replace `_backend = PostgresSearchBackend()` with `_backend = OpenSearchBackend()`.

No route handlers or callers need to change.

---

## Authoring features (Phase 5)

### Topics
Create a topic via the **+** button at the top of the Topics section in the sidebar. Edit an existing topic (name, description, color) by hovering the row and clicking the pencil icon.

### Entries
Open any article and use the sidebar **Edit entry** action to change title, type, body (Markdown), tags, or source URL. The body is stored as plain Markdown and rendered to HTML in the browser.

### Markdown body
The body field accepts standard Markdown (`**bold**`, `# headings`, `> blockquote`, etc). Use `[[Entry Title]]` anywhere in the body to create a wiki-style backlink to another entry in the same topic — these render as highlighted spans in the article view and appear as clickable cards in the Backlinks sidebar panel of the linked entry.

### Extending an article
Use the **Write extension** button at the bottom of an article to append a new content block. The extension is appended after a `---` divider and the full updated body is saved. This is always user-triggered — nothing is added automatically.

### Related entries
Entries sharing at least one tag are shown as **Suggestions** in the article sidebar. Click **Link** to create a permanent relation. Existing related entries can be removed with the ✕ button.

---

## Environment variables

Only needed for the production compose. Copy `.env.example` to `.env` and set these:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Postgres password | — (required) |
| `POSTGRES_DB` | Database name | `knowledge_hoarder` |
| `POSTGRES_USER` | Database user | `khoarder` |
| `DATABASE_URL` | Full async DB URL for the backend | — (required) |
| `STORAGE_PATH` | File upload root inside the container | `/storage` |
| `FRONTEND_PORT` | Host port for the nginx frontend | `80` |
| `LLM_BASE_URL` | LM Studio base URL ending in `/v1` | *(AI disabled if empty)* |
| `LLM_MODEL` | Model name as shown in LM Studio | `local-model` |
| `LLM_TIMEOUT` | LM Studio request timeout (seconds) | `60` |
| `LLM_CONTEXT_ENTRIES` | Entries sent as context per Q&A | `5` |

The dev compose (`docker-compose.dev.yml`) uses hardcoded dev values and does not read `.env`.

---

## Development commands

```bash
# Frontend
cd frontend
pnpm install          # install deps
pnpm dev              # Vite dev server → http://localhost:5173
pnpm type-check       # TypeScript check (0 errors expected)
pnpm build            # production build → dist/

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000   # tables + seed run on startup

# Alembic (future schema migrations)
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## Tech stack

| Layer    | Choice |
|----------|--------|
| Frontend | Vue 3 + Vite + Tailwind CSS + Pinia + Vue Router |
| Backend  | FastAPI + SQLAlchemy 2 (async) + Alembic |
| Database | PostgreSQL 16 |
| Serving  | nginx (frontend) + gunicorn + uvicorn workers (backend) |
| AI       | LM Studio — OpenAI-compatible API (Phase 5) |
| Runtime  | Docker + Docker Compose |

---

## Phase roadmap

- [x] **Phase 1** — UI shell: Vue 3 components, both pages, atomic design system
- [x] **Phase 2** — Backend: FastAPI + PostgreSQL, real data, demo seed content
- [x] **Phase 3** — Entry creation: URL import, note editor, file upload; attachment download; topic JSON export/import
- [x] **Phase 4** — Docker: multi-stage Dockerfiles, dev + prod compose stacks, persistent volumes
- [x] **Phase 5** — Authoring: topic + entry create/edit, Markdown body, backlinks, related entries, article extension
- [x] **Phase 6** — Search: PostgreSQL FTS (tsvector), relevance ranking, highlighted snippets, cross-topic scope toggle
- [x] **Phase 7** — AI: LM Studio Q&A with knowledge retrieval, article summarize/tags/related/extend assist
- [ ] **Phase 8** — Dark mode, mobile layout, OpenSearch upgrade path

---

## Design

Aesthetic: Swiss editorial meets archival calm.
Fonts: DM Serif Display (headings) + DM Sans (UI/body).
Color tokens: oklch-based CSS custom properties in `frontend/src/assets/main.css`.
See `docs/SPEC.md` for full architecture and design decisions.
