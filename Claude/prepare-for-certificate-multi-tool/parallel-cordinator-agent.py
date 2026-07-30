''' Build for learing/testing purpose. Build by Dragan Vasic with great help from Claude '''

"""Coordinator agent (Claude Agent SDK) that compares parallel vs. sequential subagent delegation.

Same 'web-researcher' + 'document-analyzer' subagents as cordinator-agent.py, but this
script runs the same research question twice against two different coordinator system
prompts:

- SEQUENTIAL_SYSTEM_PROMPT: delegate to web-researcher, wait for its report, then copy
  those findings into document-analyzer's prompt (a pipeline -- one Task/Agent call per
  coordinator response).
- PARALLEL_SYSTEM_PROMPT: emit Task/Agent calls for BOTH subagents in the same response,
  each working independently from the original question. Claude Code executes multiple
  tool_use blocks emitted in one turn concurrently, so both subagents run at the same time
  instead of one after another.

Wall-clock time for each run is measured with time.perf_counter() so the latency
improvement from parallel delegation can be compared directly.
"""

import asyncio
import os
import sys
import time

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

SEQUENTIAL_SYSTEM_PROMPT = """\
You are a research coordinator. You do not do research yourself -- you delegate every \
piece of research work to subagents via the Task tool, then synthesize their reports \
into a final answer for the user.

For each research request:
1. Delegate initial research to the 'web-researcher' subagent (Task tool, \
   subagent_type="web-researcher"). Its prompt should restate the user's question in full.
2. Once web-researcher reports back, delegate follow-up analysis to the \
   'document-analyzer' subagent (Task tool, subagent_type="document-analyzer") -- in a \
   SEPARATE, later response, only after web-researcher's report has come back.

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

PARALLEL_SYSTEM_PROMPT = """\
You are a research coordinator. You do not do research yourself -- you delegate every \
piece of research work to subagents via the Task tool, then synthesize their reports \
into a final answer for the user.

For each research request, delegate to BOTH subagents AT THE SAME TIME, in a single \
response:
1. 'web-researcher' (Task tool, subagent_type="web-researcher") -- give it the user's \
   question restated in full.
2. 'document-analyzer' (Task tool, subagent_type="document-analyzer") -- give it the SAME \
   user's question restated in full. It works independently and does not need \
   web-researcher's output.

CRITICAL: emit BOTH Task tool calls in the SAME response so they run concurrently -- do \
NOT wait for one subagent to finish before calling the other. Each subagent runs in an \
isolated context and receives only the prompt text you give it, so each prompt must fully \
restate the user's question on its own.

Once both subagents report back, synthesize their findings into one final answer for the \
user, noting which parts came from web research vs. document analysis.

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


def _build_options(system_prompt: str) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=MODEL,
        system_prompt=system_prompt,
        agents={
            "web-researcher": WEB_RESEARCHER,
            "document-analyzer": DOCUMENT_ANALYZER,
        },
        # "Task" was renamed to "Agent" in Claude Code v2.1.63 -- both are pre-approved here
        # for compatibility. disallowed_tools is a hard deny that overrides a subagent's own
        # `tools` grant, so the subagents' tools must stay out of that list (see
        # cordinator-agent.py for the full explanation of this gotcha).
        allowed_tools=["Task", "Agent", "WebSearch", "WebFetch", "Read", "Grep", "Glob"],
        disallowed_tools=["Write", "Edit", "Bash"],
    )


async def _run_once(options: ClaudeAgentOptions, question: str, label: str) -> tuple[float, int]:
    """Run one research query to completion. Returns (elapsed_seconds, max Task/Agent calls seen in a single turn)."""
    max_parallel_delegations = 0
    start = time.perf_counter()
    async with ClaudeSDKClient(options=options) as client:
        await client.query(question)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                delegations_this_turn = 0
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"\n[{label}] Claude: {block.text}")
                    elif isinstance(block, ToolUseBlock):
                        if block.name in ("Task", "Agent"):
                            delegations_this_turn += 1
                            subagent = block.input.get("subagent_type", "?")
                            print(f"\n[{label}] delegating to subagent '{subagent}'")
                        else:
                            print(f"\n[{label}] calling tool: {block.name}({block.input})")
                if delegations_this_turn:
                    print(f"[{label}] {delegations_this_turn} Task/Agent call(s) emitted in this single response")
                max_parallel_delegations = max(max_parallel_delegations, delegations_this_turn)
            elif isinstance(message, ResultMessage):
                print(f"\n[{label}] stop: {message.subtype}")
    elapsed = time.perf_counter() - start
    return elapsed, max_parallel_delegations


async def _compare(question: str) -> None:
    print(f"\n=== Research question: {question} ===")

    print("\n--- Sequential delegation ---")
    seq_elapsed, seq_max_parallel = await _run_once(_build_options(SEQUENTIAL_SYSTEM_PROMPT), question, "sequential")

    print("\n--- Parallel delegation ---")
    par_elapsed, par_max_parallel = await _run_once(_build_options(PARALLEL_SYSTEM_PROMPT), question, "parallel")

    print("\n=== Latency comparison ===")
    print(f"Sequential: {seq_elapsed:.2f}s (max {seq_max_parallel} Task/Agent call(s) in a single response)")
    print(f"Parallel:   {par_elapsed:.2f}s (max {par_max_parallel} Task/Agent call(s) in a single response)")
    if seq_elapsed > 0:
        delta_pct = (seq_elapsed - par_elapsed) / seq_elapsed * 100
        if delta_pct > 0:
            print(f"Parallel delegation was {delta_pct:.1f}% faster than sequential.")
        else:
            print(f"Parallel delegation was {-delta_pct:.1f}% slower than sequential (no improvement this run).")


async def run() -> None:
    print("Parallel vs. sequential subagent delegation benchmark.")
    print("Type a research question (or 'exit' to quit) -- each one runs both modes and compares latency.")

    cli_question = " ".join(sys.argv[1:]).strip()
    if cli_question:
        await _compare(cli_question)
        return

    while True:
        question = input("\nResearch question: ").strip()
        if question.lower() in ("exit", "quit"):
            return
        if not question:
            continue
        await _compare(question)


if __name__ == "__main__":
    asyncio.run(run())
