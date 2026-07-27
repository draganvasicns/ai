''' this is test file, yea '''

import importlib.util
import json
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

_SPEC = importlib.util.spec_from_file_location(
    "mcp_server", Path(__file__).parent / "mcp-server.py"
)
mcp_server = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mcp_server)


@pytest.fixture(autouse=True)
def isolated_data_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_server, "DATA_FILE", tmp_path / "stories.json")


def _error_payload(exc: ToolError) -> dict:
    return json.loads(str(exc))


def test_matches_key_is_case_insensitive():
    story = {"title": "The Hobbit", "author": "J.R.R. Tolkien"}
    assert mcp_server._matches_key(story, "the hobbit", "j.r.r. tolkien")
    assert not mcp_server._matches_key(story, "the hobbit", "someone else")


def test_check_author_empty_raises_validation_error():
    with pytest.raises(ToolError) as exc_info:
        mcp_server._check_author("")
    payload = _error_payload(exc_info.value)
    assert payload["errorCategory"] == "validation"
    assert payload["isRetryable"] is False


def test_check_author_forbidden_raises_permission_error():
    with pytest.raises(ToolError) as exc_info:
        mcp_server._check_author("ZABRANJEN-AUTOR")
    payload = _error_payload(exc_info.value)
    assert payload["errorCategory"] == "permission"
    assert payload["isRetryable"] is False


def test_check_author_transient_raises_retryable_error():
    with pytest.raises(ToolError) as exc_info:
        mcp_server._check_author("TRANSIENT")
    payload = _error_payload(exc_info.value)
    assert payload["errorCategory"] == "transient"
    assert payload["isRetryable"] is True


def test_check_author_valid_does_not_raise():
    mcp_server._check_author("Isaac Asimov")


def test_add_story_creates_new_entry():
    result = mcp_server.add_or_update_story(
        title="Foundation",
        author="Isaac Asimov",
        description="A galactic empire falls.",
        text="It was a dark and stormy future.",
    )

    assert "added" in result
    stories = mcp_server._load_stories()
    assert len(stories) == 1
    assert stories[0]["title"] == "Foundation"
    assert stories[0]["author"] == "Isaac Asimov"


def test_add_story_updates_existing_entry_by_key():
    mcp_server.add_or_update_story(
        title="Foundation", author="Isaac Asimov", description="v1", text="v1 text"
    )
    result = mcp_server.add_or_update_story(
        title="foundation", author="isaac asimov", description="v2", text="v2 text"
    )

    assert "updated" in result
    stories = mcp_server._load_stories()
    assert len(stories) == 1
    assert stories[0]["description"] == "v2"
    assert stories[0]["text"] == "v2 text"


def test_add_story_propagates_author_validation_error():
    with pytest.raises(ToolError):
        mcp_server.add_or_update_story(
            title="Foundation", author="", description="d", text="t"
        )
    assert mcp_server._load_stories() == []


def test_delete_story_removes_matching_entry():
    mcp_server.add_or_update_story(
        title="Dune", author="Frank Herbert", description="Desert planet.", text="..."
    )

    result = mcp_server.delete_story(title="Dune", author="Frank Herbert")

    assert "deleted" in result
    assert mcp_server._load_stories() == []


def test_delete_story_missing_entry_returns_message_without_raising():
    result = mcp_server.delete_story(title="Nonexistent", author="Nobody")
    assert "No story found" in result


def test_search_stories_filters_by_author_title_and_description():
    mcp_server.add_or_update_story(
        title="Foundation", author="Isaac Asimov", description="A galactic empire falls.", text="..."
    )
    mcp_server.add_or_update_story(
        title="Dune", author="Frank Herbert", description="Desert planet politics.", text="..."
    )

    by_author = mcp_server.search_stories(author="Isaac Asimov")
    assert [s["title"] for s in by_author] == ["Foundation"]

    by_title_part = mcp_server.search_stories(title_part="dun")
    assert [s["title"] for s in by_title_part] == ["Dune"]

    by_description_part = mcp_server.search_stories(description_part="politics")
    assert [s["title"] for s in by_description_part] == ["Dune"]

    combined_no_match = mcp_server.search_stories(author="Isaac Asimov", title_part="dun")
    assert combined_no_match == []

    no_filters = mcp_server.search_stories()
    assert len(no_filters) == 2
