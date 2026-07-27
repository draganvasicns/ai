# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & Commands

```bash
# Create virtual env and activate it
uv venv
source .venv/bin/activate

# Install the package in development mode (installs deps from pyproject.toml)
uv pip install -e .

# Start the MCP server
uv run main.py

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_document.py::TestBinaryDocumentToMarkdown::test_binary_document_to_markdown_with_pdf
```

## Architecture

This is an MCP (Model Context Protocol) server exposing document-processing tools to AI assistants, built with `mcp[cli]` (`FastMCP`).

- `main.py` — entry point. Creates the `FastMCP("docs")` server instance and registers tools via `mcp.tool()(function)`. This is the wiring point: every new tool must be imported and registered here to be exposed.
- `tools/` — plain Python functions implementing tool logic, decoupled from MCP registration. Each tool is a standalone function (not a class), registered in `main.py`.
  - `tools/document.py` — `binary_document_to_markdown`: converts binary document data (PDF, DOCX, etc.) to markdown using `markitdown`. Takes raw bytes plus a file extension string, wraps the bytes in a `BytesIO`/`StreamInfo` pair for `MarkItDown().convert(...)`.
  - `tools/math.py` — `add`: example tool showing the expected documentation style (see below).
- `tests/` — pytest tests, one test file per tool module. Binary fixtures (sample `.docx`/`.pdf`) live in `tests/fixtures/` and are read from disk in tests rather than mocked.

## Tool definition conventions

Tools are plain functions registered with `mcp.tool()(fn)`. Parameters use `pydantic.Field` for descriptions, since these descriptions are surfaced to the calling AI assistant as part of the tool schema:

```python
from pydantic import Field

def my_tool(
    param1: str = Field(description="Detailed description of this parameter"),
    param2: int = Field(description="Explain what this parameter does")
) -> ReturnType:
    """Comprehensive docstring here"""
```

Docstrings should (see `tools/math.py::add` for the canonical example):
- Begin with a one-line summary
- Provide a detailed explanation of functionality
- Explain when to use (and not use) the tool
- Include usage examples with expected input/output
