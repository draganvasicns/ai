"""Agentic loop using the Claude API that uses the tools exposed by mcp-server.py.

Connects to mcp-server.py over stdio, converts its tools for the Claude tool
runner, and lets Claude decide when to call them while chatting with the user.
"""

import asyncio
import os
import sys
from pathlib import Path

from anthropic import AsyncAnthropic
from anthropic.lib.tools import ToolError
from anthropic.lib.tools.mcp import async_mcp_tool
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

MCP_SERVER_SCRIPT = Path(__file__).parent / "mcp-server.py"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")
MAX_DESCRIPTION_LENGTH = 100

ADAPTIVE_THINKING_MODELS = {
    "claude-fable-5",
    "claude-mythos-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-5",
    "claude-sonnet-4-6",
}


def _install_description_length_hook(tools) -> None:
    """Reject tool calls whose 'description' argument exceeds MAX_DESCRIPTION_LENGTH before they reach the MCP server."""
    for tool in tools:
        original_call = tool.call

        # Default arg binds each closure to its own original_call (late-binding otherwise).
        async def hooked_call(input, _original_call=original_call):
            description = input.get("description") if isinstance(input, dict) else None
            if isinstance(description, str) and len(description) > MAX_DESCRIPTION_LENGTH:
                raise ToolError(
                    f"description is too long ({len(description)} characters); "
                    f"maximum allowed is {MAX_DESCRIPTION_LENGTH} characters. Please shorten it and try again."
                )
            return await _original_call(input)

        tool.call = hooked_call


async def run() -> None:
    client = AsyncAnthropic()
    server_params = StdioServerParameters(command=sys.executable, args=[str(MCP_SERVER_SCRIPT)])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as mcp_session:
            await mcp_session.initialize()

            tools_result = await mcp_session.list_tools()
            tools = [async_mcp_tool(t, mcp_session) for t in tools_result.tools]
            _install_description_length_hook(tools)

            print("Connected to mcp-server.py. Available tools:")
            for t in tools_result.tools:
                print(f"  - {t.name}: {t.description}")

            print("\nType a request (or 'exit' to quit).")
            history = []
            while True:
                query = input("\nYou: ").strip()
                if query.lower() in ("exit", "quit"):
                    break
                if query.lower() in  ("/clear"):
                    history.clear()
                    print("Context cleared")
                    continue
                if not query:
                    continue

                history.append({"role": "user", "content": query})

                extra_params = {}
                if MODEL in ADAPTIVE_THINKING_MODELS:
                    extra_params["thinking"] = {"type": "adaptive"}

                runner = client.beta.messages.tool_runner(
                    model=MODEL,
                    max_tokens=4096,
                    tools=tools,
                    messages=history,
                    **extra_params,
                )

                final_content = []
                async for message in runner:
                    final_content = message.content
                    for block in message.content:
                        if block.type == "text":
                            print(f"\nClaude: {block.text}")
                        elif block.type == "tool_use":
                            print(f"\n[calling tool: {block.name}({block.input})]")

                    if(message.stop_reason):
                        print(f"\n Stop reason: {message.stop_reason}")
                    if message.stop_reason == "end_turn":
                        print("\n[end_turn: Claude je zavrsio odgovor]")

                history.append({"role": "assistant", "content": final_content})
                print(f"[...nbr elements in context {len(history)}]")


if __name__ == "__main__":
    asyncio.run(run())
