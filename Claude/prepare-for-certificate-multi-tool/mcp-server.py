"""Test MCP server for managing short stories (title, description, author, text)."""

import json
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

DATA_FILE = Path(__file__).parent / "stories.json"

mcp = FastMCP("stories-server")


def _load_stories() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_stories(stories: list[dict]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)


def _matches_key(story: dict, title: str, author: str) -> bool:
    return story["title"].lower() == title.lower() and story["author"].lower() == author.lower()


def _raise_tool_error(error_category: str, message: str, *, is_retryable: bool) -> None:
    """Raise a ToolError whose message is a structured JSON payload the agent can act on."""
    raise ToolError(
        json.dumps(
            {
                "error": True,
                "errorCategory": error_category,
                "isRetryable": is_retryable,
                "message": message,
            },
            ensure_ascii=False,
        )
    )


def _check_author(author: str) -> None:
    """Raise a structured ToolError for known bad author values.

    'ZABRANJEN-AUTOR' and 'TRANSIENT' are magic values used to exercise the
    permission-error and transient-error paths respectively (e.g. for agent testing).
    """
    if not author.strip():
        _raise_tool_error("validation", "Author is required and cannot be empty.", is_retryable=False)
    if author == "ZABRANJEN-AUTOR":
        _raise_tool_error(
            "permission", f"Access denied: author '{author}' is not permitted to publish stories.", is_retryable=False
        )
    if author == "TRANSIENT":
        _raise_tool_error(
            "transient", "Temporary storage error while processing the request. Please retry.", is_retryable=True
        )


@mcp.tool(
    description=(
        "Add a new story, or update it if a story with the same title and author already exists. "
        "Raises a validation error if author is empty, a permission error for author 'ZABRANJEN-AUTOR', "
        "or a retryable transient error for author 'TRANSIENT'."
    )
)
def add_or_update_story(
    title: Annotated[str, Field(description="Title of the story.")],
    author: Annotated[str, Field(description="Name of the story's author.")],
    description: Annotated[str, Field(description="Short description or summary of the story.")],
    text: Annotated[str, Field(description="Full text of the story.")],
) -> str:
    _check_author(author)

    stories = _load_stories()

    for story in stories:
        if _matches_key(story, title, author):
            story["description"] = description
            story["text"] = text
            _save_stories(stories)
            return f"Story '{title}' by {author} updated."

    stories.append({
        "title": title,
        "author": author,
        "description": description,
        "text": text,
    })
    _save_stories(stories)
    return f"Story '{title}' by {author} added."


@mcp.tool(
    description=(
        "Delete a story identified by its title and author. "
        "Raises a validation error if author is empty, a permission error for author 'ZABRANJEN-AUTOR', "
        "or a retryable transient error for author 'TRANSIENT'."
    )
)
def delete_story(
    title: Annotated[str, Field(description="Title of the story to delete.")],
    author: Annotated[str, Field(description="Name of the story's author.")],
) -> str:
    _check_author(author)

    stories = _load_stories()
    remaining = [s for s in stories if not _matches_key(s, title, author)]

    if len(remaining) == len(stories):
        return f"No story found with title '{title}' and author '{author}'."

    _save_stories(remaining)
    return f"Story '{title}' by {author} deleted."


@mcp.tool(
    description=(
        "Search stories by author (exact match), or a substring of the title or description. "
        "All filters are optional and combined with AND when more than one is provided."
    )
)
def search_stories(
    author: Annotated[str, Field(description="Exact author name to filter by. Empty means no author filter.")] = "",
    title_part: Annotated[str, Field(description="Substring to search for in the story title. Empty means no title filter.")] = "",
    description_part: Annotated[
        str, Field(description="Substring to search for in the story description. Empty means no description filter.")
    ] = "",
) -> list[dict]:
    stories = _load_stories()
    results = []

    for story in stories:
        if author and story["author"].lower() != author.lower():
            continue
        if title_part and title_part.lower() not in story["title"].lower():
            continue
        if description_part and description_part.lower() not in story["description"].lower():
            continue
        results.append(story)

    return results


if __name__ == "__main__":
    mcp.run()
