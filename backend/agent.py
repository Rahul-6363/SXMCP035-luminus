"""
ERP Agent — single LLM call architecture.

Flow (1 LLM call total per query):
  1. LLM receives user text and outputs JSON: {tool, params}
  2. Tool is executed directly (no back-and-forth)
  3. Tool result is formatted in Python and returned

This is ~5x faster than ReAct for local models.
"""

import asyncio
import json
import logging
import re
import textwrap
from typing import AsyncGenerator

from langchain_ollama import ChatOllama

from config import get_settings
from mcp_tools import (
    check_inventory,
    update_inventory,
    create_bom,
    get_bom,
    update_bom,
    delete_bom,
    run_bom,
    check_bom_buildability,
)

logger = logging.getLogger("mcp_host.agent")
cfg = get_settings()

_llm = ChatOllama(base_url=cfg.OLLAMA_BASE_URL, model=cfg.OLLAMA_MODEL, temperature=0)

_TOOL_MAP = {
    "check_inventory":        check_inventory,
    "update_inventory":       update_inventory,
    "create_bom":             create_bom,
    "get_bom":                get_bom,
    "update_bom":             update_bom,
    "delete_bom":             delete_bom,
    "run_bom":                run_bom,
    "check_bom_buildability": check_bom_buildability,
}

_SYSTEM = textwrap.dedent("""\
    You are an ERP tool selector. Given a user request, output ONLY a JSON object — no explanation, no markdown.

    Tools:
    - check_inventory   : {"tool":"check_inventory","params":{"item_code":"","search":"keyword or empty"}}
    - update_inventory  : {"tool":"update_inventory","params":{"item_code":"CODE","quantity_change":10,"reason":"text"}}
    - get_bom           : {"tool":"get_bom","params":{"bom_name":"NAME"}}
    - run_bom           : {"tool":"run_bom","params":{"bom_name":"NAME","quantity":1}}
    - check_bom_buildability: {"tool":"check_bom_buildability","params":{"bom_name":"NAME","quantity":1}}
    - create_bom        : {"tool":"create_bom","params":{"name":"NAME","description":"text","output_quantity":1,"lead_time_days":14,"items_json":"[{\"item_code\":\"X\",\"qty_required\":1}]"}}
    - update_bom        : {"tool":"update_bom","params":{"bom_name":"NAME","field":"description","value":"text"}}
    - delete_bom        : {"tool":"delete_bom","params":{"bom_name":"NAME"}}

    Rules:
    - Use search param for keyword queries (e.g. "cooling fan", "laptop", "mouse").
    - Use item_code only when the exact code is given.
    - Leave item_code and search empty to list all inventory.
    - Output raw JSON only. No prose.
""")


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from LLM output (handles markdown fences)."""
    # Strip markdown fences
    text = re.sub(r"```[a-zA-Z]*\n?", "", text).strip()
    # Find first {...}
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON found in LLM output: {text!r}")


def _format_inventory(rows: list[dict]) -> str:
    """Format a list of inventory rows as readable text."""
    if not rows:
        return "No items found."
    lines = []
    for item in rows:
        avail = item.get("available", item.get("quantity", "?"))
        in_use = item.get("quantity_in_use", 0)
        line = f"• {item['code']} — {item.get('description', '')} | {avail} {item.get('uom', '')} available"
        if in_use:
            line += f" ({in_use} in use)"
        lines.append(line)
    header = f"Found {len(rows)} item(s):\n"
    if len(rows) > 25:
        return header + "\n".join(lines[:25]) + f"\n...and {len(rows)-25} more."
    return header + "\n".join(lines)


def _format_bom(raw: str) -> str:
    """Format get_bom JSON output."""
    try:
        data = json.loads(raw)
    except Exception:
        return raw
    bom = data.get("bom", {})
    components = data.get("components", [])
    lines = [
        f"BOM: {bom.get('name')}",
        f"Description: {bom.get('description', '—')}",
        f"Output qty: {bom.get('output_quantity')} | Lead time: {bom.get('lead_time_days')} days",
        "",
        "Components:",
    ]
    for c in components:
        avail = c.get("available", "?")
        status = "✓" if int(avail) >= int(c.get("qty_required", 0)) else "✗ SHORT"
        lines.append(f"  {status} {c['item_code']} — need {c['qty_required']} {c.get('uom','')} | have {avail}")
    return "\n".join(lines)


def _call_llm(user_text: str) -> tuple[str, str, dict]:
    """
    Calls LLM, parses tool+params.
    Returns: (tool_name, raw_llm_output, params)
    Raises on failure.
    """
    response = _llm.invoke([
        {"role": "system", "content": _SYSTEM},
        {"role": "user",   "content": user_text},
    ])
    raw_llm = response.content.strip()
    logger.info("LLM output: %s", raw_llm)
    intent = _extract_json(raw_llm)
    return intent["tool"], raw_llm, intent.get("params", {})


def _execute_and_format(tool_name: str, params: dict) -> tuple[str, list[dict]]:
    """
    Executes the tool and formats the result.
    Returns: (answer_text, shortages_list)
    """
    tool = _TOOL_MAP.get(tool_name)
    if not tool:
        return f"Unknown tool '{tool_name}'. Please try again.", []

    result = tool.invoke(params)

    shortages: list[dict] = []

    if tool_name == "check_inventory":
        try:
            rows = json.loads(result)
            if isinstance(rows, list):
                return _format_inventory(rows), []
        except Exception:
            pass
        return result, []

    if tool_name == "get_bom":
        return _format_bom(result), []

    try:
        data = json.loads(result)
        if isinstance(data, dict):
            if data.get("status") == "shortage":
                shortages = data.get("shortages", [])
            return data.get("message", result), shortages
    except Exception:
        pass

    return result, []


def run_agent(user_text: str, session_id: str = "default") -> tuple[str, list[dict]]:
    """
    Single LLM call → tool execution → formatted response.
    Returns: (answer_text, shortages_list)
    """
    try:
        tool_name, _, params = _call_llm(user_text)
    except Exception as exc:
        logger.error("LLM/parse failed: %s", exc)
        return "I couldn't understand that request. Try rephrasing it.", []

    logger.info("Calling tool '%s' with params %s", tool_name, params)

    try:
        return _execute_and_format(tool_name, params)
    except Exception as exc:
        logger.error("Tool '%s' failed: %s", tool_name, exc)
        return f"Tool execution failed: {exc}", []


async def run_agent_stream(
    user_text: str, session_id: str = "default"
) -> AsyncGenerator[dict, None]:
    """
    Streaming version: yields SSE-style dicts.
      {"type": "status", "text": "..."}   — progress updates
      {"type": "token",  "text": "..."}   — incremental answer text
      {"type": "done",   "shortages": []} — final event with shortage data
      {"type": "error",  "text": "..."}   — on failure
    """
    yield {"type": "status", "text": "Thinking…"}

    # Step 1: LLM call (blocking → run in thread)
    try:
        tool_name, _, params = await asyncio.to_thread(_call_llm, user_text)
    except Exception as exc:
        logger.error("LLM/parse failed: %s", exc)
        yield {"type": "error", "text": "I couldn't understand that request. Try rephrasing it."}
        return

    yield {"type": "status", "text": f"Running {tool_name.replace('_', ' ')}…"}

    # Step 2: tool execution + format (blocking → run in thread)
    try:
        answer, shortages = await asyncio.to_thread(_execute_and_format, tool_name, params)
    except Exception as exc:
        logger.error("Tool '%s' failed: %s", tool_name, exc)
        yield {"type": "error", "text": f"Tool execution failed: {exc}"}
        return

    # Step 3: stream answer word by word
    words = answer.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == len(words) - 1 else word + " "
        yield {"type": "token", "text": chunk}

    yield {"type": "done", "shortages": shortages}
