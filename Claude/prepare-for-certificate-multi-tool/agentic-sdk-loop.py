"""Agentic loop using the Claude Agent SDK, connected to mcp-server.py's tools.

Same behavior as agentic-loop.py (chat loop backed by the stories MCP server),
but built on claude_agent_sdk instead of the raw Messages API + tool_runner,
and implements the description-length guard as a PreToolUse hook instead of
wrapping tool.call().
"""

import asyncio
import os
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)
from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_SCRIPT = Path(__file__).parent / "mcp-server.py"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")
MAX_DESCRIPTION_LENGTH = 100
MCP_SERVER_NAME = "stories"


async def _validate_description_length(input_data, _tool_use_id, _context):
    """PreToolUse hook: deny any stories-tool call whose 'description' argument is too long."""
    tool_input = input_data.get("tool_input") or {}
    description = tool_input.get("description")
    if isinstance(description, str) and len(description) > MAX_DESCRIPTION_LENGTH:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"description is too long ({len(description)} characters); "
                    f"maximum allowed is {MAX_DESCRIPTION_LENGTH} characters. Please shorten it and try again."
                ),
            }
        }
    return {}


def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=MODEL,
        # Note: restricting `tools` to just the MCP pattern (or `[]`) also hides the MCP
        # tools themselves here, causing Claude to hallucinate a fake tool call instead of
        # invoking the real one. So we keep Claude Code's default built-in toolset (`tools`
        # left unset) and instead block the specific built-ins that would let Claude bypass
        # the MCP server (e.g. reading stories.json directly) via `disallowed_tools`.
        disallowed_tools=["Read", "Write", "Edit", "Bash"],
        mcp_servers={
            MCP_SERVER_NAME: {"command": sys.executable, "args": [str(MCP_SERVER_SCRIPT)]},
        },
        allowed_tools=[f"mcp__{MCP_SERVER_NAME}__*"],
        hooks={
            "PreToolUse": [
                HookMatcher(matcher=f"^mcp__{MCP_SERVER_NAME}__", hooks=[_validate_description_length]),
            ]
        },
    )


async def _chat_session(options: ClaudeAgentOptions) -> bool:
    """Run one client session until 'exit' or '/clear'. Returns True if the caller should start a fresh session."""
    async with ClaudeSDKClient(options=options) as client:
        while True:
            query = input("\nYou: ").strip()
            if query.lower() in ("exit", "quit"):
                return False
            if query.lower() == "/clear":
                print("Context cleared")
                return True
            if not query:
                continue

            await client.query(query)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(f"\nClaude: {block.text}")
                        elif isinstance(block, ToolUseBlock):
                            print(f"\n[calling tool: {block.name}({block.input})]")
                elif isinstance(message, ResultMessage):
                    print(f"\n[stop: {message.subtype}]")


async def run() -> None:
    options = _build_options()
    print(f"Connected via Claude Agent SDK (MCP server: {MCP_SERVER_NAME}).")
    print("Type a request (or 'exit' to quit, '/clear' to reset context).")

    while await _chat_session(options):
        pass


if __name__ == "__main__":
    asyncio.run(run())
