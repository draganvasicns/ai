"""Test MCP server for managing short stories (title, description, author, text)."""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

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


@mcp.tool()
def add_or_update_story(title: str, author: str, description: str, text: str) -> str:
    """Add a new story, or update it if a story with the same title and author already exists."""
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


@mcp.tool()
def delete_story(title: str, author: str) -> str:
    """Delete a story identified by its title and author."""
    stories = _load_stories()
    remaining = [s for s in stories if not _matches_key(s, title, author)]

    if len(remaining) == len(stories):
        return f"No story found with title '{title}' and author '{author}'."

    _save_stories(remaining)
    return f"Story '{title}' by {author} deleted."


@mcp.tool()
def search_stories(author: str = "", title_part: str = "", description_part: str = "") -> list[dict]:
    """Search stories by author (exact match), or a substring of the title or description.

    All filters are optional and combined with AND when more than one is provided.
    """
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
