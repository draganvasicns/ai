# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the application

```bash
./run.sh                                            # convenience wrapper
cd backend && uv run uvicorn app:app --reload --port 8000   # manual start
```

The server serves the frontend at `http://localhost:8000` and exposes the API under `/api/*` (docs at `/docs`). On startup, `app.py` auto-ingests every `.pdf`/`.docx`/`.txt` in `../docs` that isn't already in the ChromaDB collection (it skips duplicates by course title — it does NOT detect content changes, so to reprocess a modified course delete `backend/chroma_db/` first).

Dependencies are managed with `uv` (Python 3.13). Use `uv sync` after pulling, and `uv add <pkg>` to install new ones (never edit `pyproject.toml` by hand for deps). There is no test suite, linter, or formatter configured.

The top-level `main.py` is a leftover stub from `uv init` — the real entry point is `backend/app.py`.

## Environment

`ANTHROPIC_API_KEY` must be set in `.env` at the repo root. `backend/config.py` loads it via `python-dotenv`.

## Architecture

This is a tool-calling RAG system, not a classic retrieve-then-generate pipeline. The flow matters because the search step is driven by Claude, not by the server.

**Request path** (`POST /api/query` → `RAGSystem.query` → `AIGenerator.generate_response`):

1. The user query is sent to Claude (`claude-sonnet-4-6`, configured in `backend/config.py`) with `tools=[search_course_content, get_course_outline]` and the system prompt from `AIGenerator.SYSTEM_PROMPT`.
2. Claude decides whether to call a tool. The system prompt enforces **at most one tool call per query** and tells Claude to skip search for general-knowledge questions.
3. If Claude returns `stop_reason == "tool_use"`, `_handle_tool_execution` runs the tool via `ToolManager`, appends results, and re-invokes Claude *without* tools to force a final text answer.
4. Sources accumulated on the tool instance (`tool.last_sources`) are pulled out by `ToolManager.get_last_sources()` and returned alongside the answer, then reset.

Implication: don't add server-side query rewriting or pre-search — the agentic loop lives inside the AI generator. To add a new retrieval capability, implement `Tool` in `search_tools.py` and register it in `RAGSystem.__init__`.

**Vector store layout** (`backend/vector_store.py`, ChromaDB persisted at `backend/chroma_db/`):

- `course_catalog` — one document per course, ID = course title. Lesson list is stored as a JSON string in metadata (`lessons_json`) because ChromaDB metadata values must be scalars. Used for fuzzy course-name resolution via `_resolve_course_name` (semantic search over titles) and for the outline tool.
- `course_content` — chunked lesson text. Chunk IDs are `{course_title_with_underscores}_{chunk_index}`, so two courses with identical titles will collide.

`search()` is a two-step lookup: first resolve `course_name` to a canonical title against `course_catalog`, then query `course_content` with a `course_title` + optional `lesson_number` filter. Pass `course_name=None` to search across all courses.

**Document ingestion** (`backend/document_processor.py`):

Course docs have a strict header format the parser depends on:

```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <lesson title>
Lesson Link: <url>
<lesson body...>

Lesson 1: ...
```

The first three lines are parsed positionally (title is required, link/instructor are optional but expected in lines 2–3). Lessons are split on `^Lesson \d+:` markers. Chunks are sentence-aware (regex-split) and prefixed with `Course <title> Lesson <n> content:` so the embedding carries course/lesson context. `CHUNK_SIZE=800` / `CHUNK_OVERLAP=100` in `config.py`.

**Session/history**:

`SessionManager` is in-memory only — sessions die with the process. `MAX_HISTORY=2` means only the last 2 question/answer pairs are sent back to Claude as context.

## Frontend

Vanilla JS + HTML/CSS in `frontend/`, served as static files by FastAPI. `app.py` mounts it with no-cache headers (`DevStaticFiles`) so edits show up on refresh without restarting uvicorn — but Python changes still need `--reload` (which is on by default).
