''' Build for learing/testing purpose. Build by Dragan Vasic with great help from Claude '''

"""Coordinator agent (Claude Agent SDK) that delegates research to two subagents.

The coordinator never researches anything itself -- it only calls the Task tool to
delegate to a 'web-researcher' subagent and a 'document-analyzer' subagent, then
synthesizes their reports. Subagents spawned via Task run in an isolated context: they
do NOT automatically inherit this conversation or each other's output, so the
coordinator's system prompt requires it to copy prior findings directly into each
subsequent subagent's Task prompt instead of assuming shared context.
"""

import asyncio
import os

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)
from dotenv import load_dotenv

load_dotenv()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")

COORDINATOR_SYSTEM_PROMPT = """\
You are a research coordinator. You do not do research yourself -- you delegate every \
piece of research work to subagents via the Task tool, then synthesize their reports \
into a final answer for the user.

For each research request:
1. Delegate initial research to the 'web-researcher' subagent (Task tool, \
   subagent_type="web-researcher"). Its prompt should restate the user's question in full.
2. Once web-researcher reports back, delegate follow-up analysis to the \
   'document-analyzer' subagent (Task tool, subagent_type="document-analyzer").

   CRITICAL: subagents run in an isolated context. Each one sees ONLY the prompt text you \
   give it in that Task call -- never this conversation, never another subagent's report. \
   Before calling document-analyzer, copy web-researcher's actual findings (the real text, \
   not a reference like "see above" or "the previous findings") directly into \
   document-analyzer's prompt, along with what you want it to check against local documents.
3. After both subagents report back, synthesize their findings into one final answer for \
   the user, noting which parts came from web research vs. document analysis.

Never call WebSearch, WebFetch, Read, Grep, or Glob yourself -- always delegate through the \
Task tool.
"""

WEB_RESEARCHER = AgentDefinition(
    description="Searches the web for current information on a topic and reports back a concise summary of findings.",
    prompt=(
        "You are a web research specialist. You receive a research question directly in "
        "your prompt -- you do NOT have access to any conversation that happened before "
        "you were invoked. Use WebSearch (and WebFetch to read promising pages) to gather "
        "current, relevant information, then report your findings as a concise, "
        "well-organized summary with the concrete facts and sources you found. Do not ask "
        "clarifying questions -- work only from the prompt you were given."
    ),
    tools=["WebSearch", "WebFetch"],
)

DOCUMENT_ANALYZER = AgentDefinition(
    description="Reads and analyzes local files/documents to extract information relevant to a research question.",
    prompt=(
        "You are a document analysis specialist. You receive a research question and "
        "relevant context directly in your prompt -- you do NOT have access to any "
        "conversation or subagent output that happened before you were invoked, so the "
        "coordinator must have already given you everything you need to know. Use Read, "
        "Grep, and Glob to search local files/documents for information relevant to that "
        "question, then report your findings as a concise, well-organized summary citing "
        "which file each finding came from."
    ),
    tools=["Read", "Grep", "Glob"],
)


def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=MODEL,
        system_prompt=COORDINATOR_SYSTEM_PROMPT,
        agents={
            "web-researcher": WEB_RESEARCHER,
            "document-analyzer": DOCUMENT_ANALYZER,
        },
        # The subagent-delegation tool was renamed from "Task" to "Agent" in Claude Code
        # v2.1.63; tool_use blocks now carry name "Agent" (system:init/permission_denials
        # still say "Task" for back-compat). Without "Agent" pre-approved here, delegation
        # calls have no interactive terminal to request approval from in this headless
        # script and get silently denied -- which is what caused the "Ne mogu da
        # pristupim internetu" reply. Also pre-approve the subagents' own tools: a
        # disallowed_tools entry is a hard deny that overrides an AgentDefinition's own
        # `tools` grant, so WebSearch/WebFetch/Read/Grep/Glob must NOT be disallowed here.
        allowed_tools=["Task", "Agent", "WebSearch", "WebFetch", "Read", "Grep", "Glob"],
        disallowed_tools=["Write", "Edit", "Bash"],
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
                            if block.name in ("Task", "Agent"):
                                subagent = block.input.get("subagent_type", "?")
                                prompt = block.input.get("prompt", "")
                                print(f"\n[delegating to subagent '{subagent}']")
                                print(f"[prompt sent]:\n{prompt}\n")
                            else:
                                print(f"\n[calling tool: {block.name}({block.input})]")
                elif isinstance(message, ResultMessage):
                    print(f"\n[stop: {message.subtype}]")


async def run() -> None:
    options = _build_options()
    print("Research coordinator ready (subagents: web-researcher, document-analyzer).")
    print("Type a research question (or 'exit' to quit, '/clear' to reset context).")

    while await _chat_session(options):
        pass


if __name__ == "__main__":
    asyncio.run(run())
