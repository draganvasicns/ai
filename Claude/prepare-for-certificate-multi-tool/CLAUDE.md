# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

A small practice project for Anthropic API / MCP certification prep. It implements one MCP server (a stories CRUD tool) and two ways of talking to it: a raw MCP client, and an agentic loop that wires the MCP tools into the Claude API's tool runner.

## Setup & running

Dependencies are managed with `uv` (see `uv.lock`, `pyproject.toml`, `requires-python = ">=3.13"`).

```bash
uv sync                      # install dependencies into .venv
uv run mcp-server.py         # run the MCP server standalone (stdio transport)
uv run mcp-client.py         # interactive raw MCP client: lists tools, prompts for args, calls one
uv run agentic-loop.py       # chat loop where Claude decides when to call the MCP tools
```

`agentic-loop.py` and `mcp-client.py` both spawn `mcp-server.py` themselves as a subprocess over stdio (via `StdioServerParameters`/`stdio_client`) — there is no separate server process to start manually when using either client.

Requires a `.env` file (loaded via `python-dotenv` in `agentic-loop.py`) with:
- `ANTHROPIC_API_KEY`
- `CLAUDE_MODEL` (optional, defaults to `claude-opus-4-8`)

There are no automated tests or linters configured in this repo.

## Architecture

- **`mcp-server.py`** — a `FastMCP` server (`stories-server`) exposing three tools (`add_or_update_story`, `delete_story`, `search_stories`) over a flat-file store, `stories.json`, in the repo root. Stories are keyed by `(title, author)` case-insensitively (`_matches_key`). Every write reloads the whole file, mutates the in-memory list, and rewrites it (`_load_stories`/`_save_stories`) — no concurrency control, fine for single-user local use only.

- **`mcp-client.py`** — minimal manual MCP client: connects over stdio, lists tools, prompts the user for each tool's input-schema arguments on the terminal, and calls the chosen tool directly. Useful for exercising the server without involving the Claude API at all.

- **`agentic-loop.py`** — the actual agentic piece. Connects to `mcp-server.py` over stdio, converts its tools with `anthropic.lib.tools.mcp.async_mcp_tool` for the Claude SDK's `client.beta.messages.tool_runner`, and runs a REPL where Claude autonomously decides when to call the story tools. Conversation `history` is kept in memory only (list of role/content dicts) and cleared with `/clear`; there is no persistence across runs. If `MODEL` is one of `ADAPTIVE_THINKING_MODELS`, adaptive thinking is enabled via `extra_params["thinking"]`.

### Tool conventions in `mcp-server.py`

- Tool descriptions are passed explicitly via `@mcp.tool(description="...")`, not via function docstrings — function docstrings are not used and should stay absent. Parameter docs use `Annotated[str, Field(description="...")]` so they show up in the generated `inputSchema` for each argument.
- Business errors are raised, not returned, via `_raise_tool_error(error_category, message, is_retryable=...)`, which raises `mcp.server.fastmcp.exceptions.ToolError` with a JSON payload (`error`, `errorCategory`, `isRetryable`, `message`) as the exception message. This makes FastMCP set `isError=True` on the `CallToolResult`, the standard MCP signal that a tool call failed (as opposed to returning an error string in a normal, `isError=False` response). Note: FastMCP's `Tool.run` wraps any exception it catches (including our own `ToolError`) into another `ToolError` with an `"Error executing tool <name>: "` prefix, so the JSON payload arrives as a substring of the final error message, not the whole message.
- `errorCategory` values in use: `validation` (bad input, not retryable), `permission` (not retryable), `transient` (retryable). `_check_author` demonstrates all three via magic author values (`""` → validation, `"ZABRANJEN-AUTOR"` → permission, `"TRANSIENT"` → transient) — useful for exercising agent error-handling behavior end-to-end.
- `search_stories` returns `list[dict]`, which gives it an auto-generated FastMCP output schema — returning anything other than a list from it will fail output validation, so don't reuse the string-based error helpers there; raising `ToolError` is still fine since it skips output validation entirely.

When adding a new MCP tool, follow the conventions above — no changes are needed in the client scripts since tools are discovered dynamically via `list_tools()`.
