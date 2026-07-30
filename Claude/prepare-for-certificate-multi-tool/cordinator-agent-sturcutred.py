''' Build for learing/testing purpose. Build by Dragan Vasic with great help from Claude '''

"""Coordinator agent (Claude Agent SDK) with structured subagent output and attribution checks.

Extension of cordinator-agent.py: same coordinator/subagent delegation pattern, but each
research subagent must report its findings as a JSON array that separates content (claim,
evidence_excerpt) from metadata (source, publication_date), and a third 'synthesizer'
subagent combines both subagents' findings while preserving source attribution. Since
Task/Agent calls don't have a native structured-output schema like the raw Messages API,
the JSON shape is enforced by prompting each subagent, not by the SDK.

After each turn, this script captures the raw ToolResultBlock text returned by each
subagent (matched to its Task/Agent call via tool_use_id -- receive_response() otherwise
only shows what was SENT to a subagent, not what it returned), parses the JSON, and
verifies that every source cited by web-researcher/document-analyzer still appears in the
synthesizer's combined output.
"""

import asyncio
import json
import os
import re

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from dotenv import load_dotenv

load_dotenv()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")

COORDINATOR_SYSTEM_PROMPT = """\
You are a research coordinator. You do not do research or writing yourself -- you \
delegate every step to subagents via the Task tool.

For each research request:
1. Delegate initial research to the 'web-researcher' subagent (Task tool, \
   subagent_type="web-researcher"). Its prompt should restate the user's question in full. \
   It reports back a JSON array of findings.
2. Delegate follow-up analysis to the 'document-analyzer' subagent (Task tool, \
   subagent_type="document-analyzer"). Copy web-researcher's actual JSON output (the real \
   text, not a reference like "see above") directly into its prompt, along with the user's \
   question, so it can check the web findings against local documents. It also reports \
   back a JSON array of findings.
3. Delegate to the 'synthesizer' subagent (Task tool, subagent_type="synthesizer"). Copy \
   BOTH web-researcher's and document-analyzer's actual JSON output directly into its \
   prompt -- it has no access to this conversation or to the other subagents' reports \
   unless you paste the real JSON text in.
4. Present the synthesizer's JSON result to the user as a readable answer. You may format \
   it as prose, but do not drop or alter any claim's sources or publication_date.

CRITICAL: subagents run in an isolated context. Each one sees ONLY the prompt text you \
give it -- never this conversation, never another subagent's report.

Never call WebSearch, WebFetch, Read, Grep, or Glob yourself -- always delegate through the \
Task tool.
"""

FINDING_JSON_INSTRUCTIONS = """
Report your findings as a JSON array. Each element must be an object with exactly these \
fields:
- "claim": string -- the factual claim, stated plainly (the content)
- "evidence_excerpt": string -- a short, verbatim excerpt (max ~2 sentences) supporting \
the claim (the content)
- "source": string -- the URL (for web findings) or file name (for document findings) the \
claim came from (the metadata)
- "publication_date": string -- ISO 8601 date (YYYY-MM-DD) if known, otherwise "unknown" \
(the metadata)

Output ONLY the JSON array as your final message -- no prose before or after it, no \
markdown code fences.
"""

WEB_RESEARCHER = AgentDefinition(
    description="Searches the web for current information on a topic and reports back structured findings.",
    prompt=(
        "You are a web research specialist. You receive a research question directly in "
        "your prompt -- you do NOT have access to any conversation that happened before "
        "you were invoked. Use WebSearch (and WebFetch to read promising pages) to gather "
        "current, relevant information. Do not ask clarifying questions -- work only from "
        "the prompt you were given." + FINDING_JSON_INSTRUCTIONS
    ),
    tools=["WebSearch", "WebFetch"],
)

DOCUMENT_ANALYZER = AgentDefinition(
    description="Reads and analyzes local files/documents to extract structured findings relevant to a research question.",
    prompt=(
        "You are a document analysis specialist. You receive a research question and "
        "relevant context directly in your prompt -- you do NOT have access to any "
        "conversation or subagent output that happened before you were invoked, so the "
        "coordinator must have already given you everything you need. Use Read, Grep, and "
        "Glob to search local files/documents for information relevant to that question." + FINDING_JSON_INSTRUCTIONS
    ),
    tools=["Read", "Grep", "Glob"],
)

SYNTHESIZER = AgentDefinition(
    description="Combines structured findings from other subagents into one report while preserving source attribution.",
    prompt=(
        "You are a synthesis specialist. You receive two JSON arrays of findings directly "
        "in your prompt -- one from web research, one from document analysis. Each finding "
        "has \"claim\", \"evidence_excerpt\", \"source\", and \"publication_date\" fields. "
        "You do NOT have access to any conversation that happened before you were invoked -- "
        "work only from the JSON given to you in this prompt.\n\n"
        "Combine related or overlapping findings into a synthesized report, but you MUST "
        "preserve source attribution: every synthesized finding must carry a \"sources\" "
        "field listing every original \"source\" value it draws from, even when multiple "
        "findings from different sources support the same synthesized claim. Never invent "
        "a source that wasn't in the input findings, and never drop a finding's source "
        "silently -- if you choose not to include an original finding in the synthesis, "
        "that's fine, but every finding you DO include must list its real source(s).\n\n"
        "Report your synthesis as a JSON array. Each element must be an object with "
        "exactly these fields:\n"
        '- "claim": string\n'
        '- "evidence_excerpt": string\n'
        '- "sources": array of strings -- every original source this claim draws from\n'
        '- "publication_date": string -- the most relevant/recent date, or "mixed" if the '
        "sources disagree\n\n"
        "Output ONLY the JSON array -- no prose before or after it, no markdown code fences."
    ),
    tools=[],
)


def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=MODEL,
        system_prompt=COORDINATOR_SYSTEM_PROMPT,
        agents={
            "web-researcher": WEB_RESEARCHER,
            "document-analyzer": DOCUMENT_ANALYZER,
            "synthesizer": SYNTHESIZER,
        },
        # "Task" was renamed to "Agent" in Claude Code v2.1.63 -- both are pre-approved here
        # for compatibility. disallowed_tools is a hard deny that overrides a subagent's own
        # `tools` grant, so the subagents' tools must stay out of that list (see
        # cordinator-agent.py for the full explanation of this gotcha).
        allowed_tools=["Task", "Agent", "WebSearch", "WebFetch", "Read", "Grep", "Glob"],
        disallowed_tools=["Write", "Edit", "Bash"],
    )


def _tool_result_text(block: ToolResultBlock) -> str:
    """Flatten a ToolResultBlock's content (str or list of content-block dicts) to plain text."""
    if isinstance(block.content, str):
        return block.content
    if isinstance(block.content, list):
        return "\n".join(part.get("text", "") for part in block.content if isinstance(part, dict))
    return ""


def _extract_json_array(text: str) -> list[dict] | None:
    """Best-effort extraction of a JSON array from a subagent's report text."""
    if not text:
        return None
    stripped = text.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    if fence_match:
        stripped = fence_match.group(1).strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else None


def _verify_attribution(
    web_findings: list[dict] | None,
    doc_findings: list[dict] | None,
    synthesized_findings: list[dict] | None,
) -> None:
    """Check that every source cited by the research subagents survives into the synthesis."""
    print("\n=== Source attribution verification ===")
    if web_findings is None and doc_findings is None:
        print("Could not parse JSON findings from the research subagents -- skipping verification.")
        return
    if synthesized_findings is None:
        print("Could not parse JSON output from the synthesizer -- skipping verification.")
        return

    original_sources = {
        f.get("source") for f in (web_findings or []) + (doc_findings or []) if f.get("source")
    }
    synthesized_sources: set[str] = set()
    for finding in synthesized_findings:
        for source in finding.get("sources") or []:
            synthesized_sources.add(source)

    if not original_sources:
        print("No sources found in the research subagents' findings -- nothing to verify.")
        return

    preserved = original_sources & synthesized_sources
    dropped = original_sources - synthesized_sources
    print(f"Original sources: {len(original_sources)} | preserved: {len(preserved)} | dropped: {len(dropped)}")
    for source in sorted(preserved):
        print(f"  [OK]      {source}")
    for source in sorted(dropped):
        print(f"  [MISSING] {source} -- attribution lost during synthesis!")


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

            # Reset per-turn tracking used for the attribution check below.
            subagent_by_tool_id: dict[str, str] = {}
            raw_report_by_subagent: dict[str, str] = {}

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
                                subagent_by_tool_id[block.id] = subagent
                                print(f"\n[delegating to subagent '{subagent}']")
                                print(f"[prompt sent]:\n{prompt}\n")
                            else:
                                print(f"\n[calling tool: {block.name}({block.input})]")
                elif isinstance(message, UserMessage):
                    content = message.content if isinstance(message.content, list) else []
                    for block in content:
                        if isinstance(block, ToolResultBlock):
                            subagent = subagent_by_tool_id.get(block.tool_use_id)
                            if subagent:
                                raw_report_by_subagent[subagent] = _tool_result_text(block)
                                print(f"\n[subagent '{subagent}' returned]:\n{raw_report_by_subagent[subagent]}\n")
                elif isinstance(message, ResultMessage):
                    print(f"\n[stop: {message.subtype}]")

            if raw_report_by_subagent:
                _verify_attribution(
                    _extract_json_array(raw_report_by_subagent.get("web-researcher", "")),
                    _extract_json_array(raw_report_by_subagent.get("document-analyzer", "")),
                    _extract_json_array(raw_report_by_subagent.get("synthesizer", "")),
                )


async def run() -> None:
    options = _build_options()
    print("Research coordinator ready (subagents: web-researcher, document-analyzer, synthesizer).")
    print("Type a research question (or 'exit' to quit, '/clear' to reset context).")

    while await _chat_session(options):
        pass


if __name__ == "__main__":
    asyncio.run(run())
