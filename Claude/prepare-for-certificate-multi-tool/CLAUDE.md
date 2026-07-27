# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

A small practice project for Anthropic API / MCP certification prep. It implements one MCP server (a stories CRUD tool) and three ways of talking to it: a raw MCP client, and two agentic chat loops with the same behavior — one on the raw Messages API + `tool_runner`, one on the Claude Agent SDK — kept side by side deliberately, for comparison.

## Setup & running

Dependencies are managed with `uv` (see `uv.lock`, `pyproject.toml`, `requires-python = ">=3.13"`).

```bash
uv sync                      # install dependencies into .venv
uv run mcp-server.py         # run the MCP server standalone (stdio transport)
uv run mcp-client.py         # interactive raw MCP client: lists tools, prompts for args, calls one
uv run agentic-loop.py       # chat loop on raw Messages API + tool_runner
uv run agentic-sdk-loop.py   # same chat loop, built on the Claude Agent SDK instead
```

`agentic-loop.py` and `mcp-client.py` spawn `mcp-server.py` themselves as a subprocess over stdio (via `StdioServerParameters`/`stdio_client`); `agentic-sdk-loop.py` instead hands the same command to `ClaudeAgentOptions.mcp_servers` and lets the Agent SDK's spawned CLI subprocess manage the connection. Either way there is no separate server process to start manually.

Requires a `.env` file (loaded via `python-dotenv` in `agentic-loop.py`) with:
- `ANTHROPIC_API_KEY`
- `CLAUDE_MODEL` (optional, defaults to `claude-opus-4-8`)

There are no automated tests or linters configured in this repo.

See `.claude/rules/` for file-type-specific conventions (e.g. required top comment for `.py` files).

## Architecture

- **`mcp-server.py`** — a `FastMCP` server (`stories-server`) exposing three tools (`add_or_update_story`, `delete_story`, `search_stories`) over a flat-file store, `stories.json`, in the repo root. Stories are keyed by `(title, author)` case-insensitively (`_matches_key`). Every write reloads the whole file, mutates the in-memory list, and rewrites it (`_load_stories`/`_save_stories`) — no concurrency control, fine for single-user local use only.

- **`mcp-client.py`** — minimal manual MCP client: connects over stdio, lists tools, prompts the user for each tool's input-schema arguments on the terminal, and calls the chosen tool directly. Useful for exercising the server without involving the Claude API at all.

- **`agentic-loop.py`** — the raw-SDK agentic loop. Connects to `mcp-server.py` over stdio, converts its tools with `anthropic.lib.tools.mcp.async_mcp_tool` for the Claude SDK's `client.beta.messages.tool_runner`, and runs a REPL where Claude autonomously decides when to call the story tools. Conversation `history` is kept in memory only (list of role/content dicts) and cleared with `/clear`; there is no persistence across runs. If `MODEL` is one of `ADAPTIVE_THINKING_MODELS`, adaptive thinking is enabled via `extra_params["thinking"]`. A `_install_description_length_hook` wraps each tool's `.call` (the instance attribute, not `.func` — `.call()` closes over the original function at construction time via `pydantic.validate_call`, so patching `.func` later has no effect) to reject any tool call whose `description` argument exceeds `MAX_DESCRIPTION_LENGTH`, raising `anthropic.lib.tools.ToolError` before the call ever reaches the MCP server.

- **`agentic-sdk-loop.py`** — the same chat loop, ported to the `claude_agent_sdk` package (`ClaudeSDKClient`/`ClaudeAgentOptions`). No manual `stdio_client`/`ClientSession`/`async_mcp_tool` — the MCP server is just a `mcp_servers` entry, and the SDK's spawned Claude Code CLI subprocess owns the conversation state for as long as the `ClaudeSDKClient` is connected (there is no `history` list to inspect). `/clear` is implemented by exiting the current `async with ClaudeSDKClient(...)` block and letting `run()`'s `while` loop open a brand-new client (`_chat_session` returns `True`/`False` to signal restart-vs-exit) — that's the only way to reset context, since the client has no in-place "clear" method. The description-length guard is the same rule as `agentic-loop.py`, but expressed the SDK-native way: a `PreToolUse` hook (`_validate_description_length`) registered via `HookMatcher`/`ClaudeAgentOptions(hooks=...)`, returning `{"hookSpecificOutput": {"permissionDecision": "deny", ...}}` instead of raising.

  Two non-obvious `ClaudeAgentOptions` gotchas found while building this:
  - `tools=[]` or `tools=["mcp__stories__*"]` does **not** scope the model down to just the MCP tools — it also hides the MCP tools themselves, and Claude will hallucinate a fake tool call as plain text and claim success without ever touching `stories.json`. Leave `tools` unset (the default Claude Code preset) if you want the MCP tools to actually work.
  - `allowed_tools` only pre-approves tools for use — it does **not** hide other tools from the model. Some built-ins (observed: `Read`) run without ever being denied even when absent from `allowed_tools`. To actually prevent Claude from bypassing the MCP server (e.g. reading `stories.json` directly instead of calling `search_stories`), block the specific built-ins with `disallowed_tools=[...]`.

### Tool conventions in `mcp-server.py`

- Tool descriptions are passed explicitly via `@mcp.tool(description="...")`, not via function docstrings — function docstrings are not used and should stay absent. Parameter docs use `Annotated[str, Field(description="...")]` so they show up in the generated `inputSchema` for each argument.
- Business errors are raised, not returned, via `_raise_tool_error(error_category, message, is_retryable=...)`, which raises `mcp.server.fastmcp.exceptions.ToolError` with a JSON payload (`error`, `errorCategory`, `isRetryable`, `message`) as the exception message. This makes FastMCP set `isError=True` on the `CallToolResult`, the standard MCP signal that a tool call failed (as opposed to returning an error string in a normal, `isError=False` response). Note: FastMCP's `Tool.run` wraps any exception it catches (including our own `ToolError`) into another `ToolError` with an `"Error executing tool <name>: "` prefix, so the JSON payload arrives as a substring of the final error message, not the whole message.
- `errorCategory` values in use: `validation` (bad input, not retryable), `permission` (not retryable), `transient` (retryable). `_check_author` demonstrates all three via magic author values (`""` → validation, `"ZABRANJEN-AUTOR"` → permission, `"TRANSIENT"` → transient) — useful for exercising agent error-handling behavior end-to-end.
- `search_stories` returns `list[dict]`, which gives it an auto-generated FastMCP output schema — returning anything other than a list from it will fail output validation, so don't reuse the string-based error helpers there; raising `ToolError` is still fine since it skips output validation entirely.

When adding a new MCP tool, follow the conventions above — no changes are needed in the client scripts since tools are discovered dynamically via `list_tools()`.
