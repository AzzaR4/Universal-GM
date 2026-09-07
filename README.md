# 🎲 Universal AI Game Master

An AI-powered Game Master for **any** tabletop RPG. Run atmospheric, persistent
campaigns with a clean four-layer architecture where **the AI narrates but never
controls the game state** — all mechanics are resolved by a deterministic Rules
Engine.

This repository contains the **first vertical slice**: a fully-functional
Generic (rules-light 2d6) ruleset, the complete player-action pipeline with
streaming narration, campaign/character/NPC/location management, export/import,
and a UI-configurable AI provider that works with OpenAI, Ollama, LM Studio,
Groq, and any OpenAI-compatible endpoint.

---

## Architecture (four-layer separation)

1. **Game State** — the source of truth (SQLite). Mutated *only* via typed
   mutation objects.
2. **Rules Engine** — all mechanical resolution (dice, outcomes, damage).
   Stateless and pluggable per ruleset. **The AI is never involved here.**
3. **Narrative Engine** — the *only* component that calls the AI. It receives the
   authoritative mechanical result and streams prose consistent with it.
4. **User Interface** — a React SPA talking to the backend over REST + SSE.

**The action pipeline** (`POST /api/campaigns/{id}/actions`, streamed via SSE):

```
player text → intent parse (AI JSON) → rules resolution (no AI)
            → state mutation (SQLite) → event emission → streaming narration (AI)
```

If no AI provider is configured or reachable, the game **degrades gracefully**:
the mechanical result is shown and you are pointed to Settings.

---

## Quick start (Docker — 3 commands)

```bash
cp .env.example .env          # 1. create your env file (edit SECRET_KEY!)
docker compose build          # 2. build images
docker compose up             # 3. run
```

Then open **http://localhost:5173**. The backend API is at
**http://localhost:8000** (interactive docs at `/docs`).

Development mode with hot-reload:

```bash
docker compose -f docker-compose.dev.yml up
```

---

## Quick start (local, no Docker)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://localhost:8000  (docs at /docs)
```

The SQLite database and tables are created automatically on first run under
`./data/`.

### Frontend

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

The dev server proxies `/api` to `http://localhost:8000`.

---

## Configuration (env vars)

Copy `.env.example` to `.env`:

| Variable       | Default                                             | Purpose                                        |
| -------------- | --------------------------------------------------- | ---------------------------------------------- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/universal_gm.db`        | Async SQLite database location                 |
| `CORS_ORIGINS` | `*`                                                 | Comma-separated allowed origins, or `*`        |
| `SECRET_KEY`   | *(change me)*                                        | Derives the AES key used to encrypt API keys   |
| `DEBUG`        | `true`                                               | Debug flag                                     |

> **Important:** set a real, long random `SECRET_KEY` in production. It is used to
> encrypt AI provider API keys stored in the database.

---

## AI provider setup

Open **Settings** in the UI (top-right). Add a provider, optionally pick a
preset, then **Set Active**. Use **Test Connection** to verify.

| Provider   | Endpoint URL                        | Model example                | API key |
| ---------- | ----------------------------------- | ---------------------------- | ------- |
| OpenAI     | `https://api.openai.com/v1`         | `gpt-4o-mini`                | yes     |
| Ollama     | `http://localhost:11434/v1`         | `llama3.1`                   | no      |
| LM Studio  | `http://localhost:1234/v1`          | *(loaded model name)*        | no      |
| Groq       | `https://api.groq.com/openai/v1`    | `llama-3.3-70b-versatile`    | yes     |
| Custom     | *(your endpoint)*                   | *(your model)*               | maybe   |

You can add multiple providers and switch the active one at any time — handy for
testing local vs. hosted models.

---

## Export / import

- **Export:** from the campaign list or the game header, click **⬇ Export** to
  download a versioned JSON snapshot of the entire campaign (characters, NPCs,
  locations, items, quests, memories).
- **Import:** from the home screen, click **⬆ Import Campaign** and choose an
  exported JSON file. A fresh campaign is created with fully remapped IDs, so
  imports never collide with existing data.

REST equivalents: `GET /api/campaigns/{id}/export` and
`POST /api/campaigns/import`.

---

## Backups

The entire game lives in one SQLite file. To back up, just copy it:

```bash
cp data/universal_gm.db data/universal_gm.backup.db
```

Restore by copying it back. For a portable, human-readable backup of a single
campaign, use the JSON export instead.

---

## Running the tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

The suite (dice parser, Generic ruleset, game-state mutations, export/import
round-trip) runs **without a live LLM** — the AI is never required for the core
mechanics.

---

## Adding a new ruleset

1. Create `backend/app/rulesets/<your_ruleset>/ruleset.py` with a class that
   subclasses `BaseRuleset` (see `app/game/rules/base_ruleset.py`).
2. Implement `default_config`, `character_schema`, `new_character_data`,
   `validate_action`, `resolve_action`, and `system_prompt_fragment`.
3. Register it in `backend/app/rulesets/registry.py` via `register(YourRuleset())`.

No changes to the core engine are needed — it will appear automatically in the
campaign creation wizard.

---

## Project layout

```
universal_gm/
├── backend/        FastAPI + SQLAlchemy async + SQLite
│   ├── app/
│   │   ├── ai/           AI provider abstraction (OpenAI-compatible)
│   │   ├── api/          REST + SSE routers
│   │   ├── core/         event bus, exceptions, encryption
│   │   ├── db/           engine + ORM models
│   │   ├── game/         state, rules, narrative, events, memory
│   │   └── rulesets/     pluggable rulesets (generic implemented)
│   └── tests/       pytest suite
├── frontend/       React 18 + TypeScript + Vite + Tailwind + Zustand
├── docker-compose.yml       production
├── docker-compose.dev.yml   hot-reload development
└── .env.example
```

---

## Tech stack

**Backend:** Python 3.11, FastAPI, SQLAlchemy 2 (async), SQLite, Pydantic v2,
`openai` SDK, `sse-starlette`, `cryptography`.
**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Zustand, TanStack Query,
React Router v6.

---

*Built as the first vertical slice of the Universal AI Game Master design.*
