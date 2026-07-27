"""Simple interactive MCP client for mcp-server.py.

Lists the tools exposed by the server and lets the user call one of them.
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = Path(__file__).parent / "mcp-server.py"


def _prompt_for_arguments(input_schema: dict) -> dict:
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))
    arguments = {}

    for name, schema in properties.items():
        label = f"{name}{' (required)' if name in required else ' (optional, Enter to skip)'}"
        value = input(f"  {label}: ")
        if not value and name not in required:
            continue
        arguments[name] = value

    return arguments


async def run() -> None:
    server_params = StdioServerParameters(command=sys.executable, args=[str(SERVER_SCRIPT)])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tools = tools_result.tools

            while True:
                print("\nAvailable tools:")
                for i, tool in enumerate(tools, start=1):
                    print(f"  {i}. {tool.name} - {tool.description}")
                print("  0. Exit")

                choice = input("\nChoose a tool to call: ").strip()
                if choice == "0":
                    break

                try:
                    tool = tools[int(choice) - 1]
                except (ValueError, IndexError):
                    print("Invalid choice.")
                    continue

                print(f"Arguments for '{tool.name}':")
                arguments = _prompt_for_arguments(tool.inputSchema)

                result = await session.call_tool(tool.name, arguments)
                for content in result.content:
                    if content.type == "text":
                        print(f"\nResult:\n{content.text}")
                    else:
                        print(f"\nResult ({content.type}):\n{json.dumps(content.model_dump(), ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    asyncio.run(run())
