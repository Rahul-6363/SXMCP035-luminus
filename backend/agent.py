"""
ERP Agent — optimized single-call architecture.

Optimizations applied
─────────────────────
OPT-1  think=False          gemma4 is a reasoning model; disabling thinking cuts
                             latency from ~39s → ~4s per call.

OPT-2  Keyword pre-router   Trivially deterministic queries (show inventory,
                             search X, ITM code lookup) never reach the LLM.
                             Routed in <1 ms via regex.

OPT-3  num_predict=300      Previous value (120) was cut off during the model's
                             now-disabled thinking phase, causing empty responses.

OPT-4  TTL response cache   Read-only tool results cached for 5 s.
                             Identical repeated queries return instantly.

OPT-5  Async warmup         LLM model loaded into Ollama memory at app startup,
                             eliminating the 15-second cold-start on first user query.

OPT-6  Persistent DB pool   SQLAlchemy pool already created once (pool_size=5).
                             Confirmed no per-request re-creation.

OPT-7  run_in_executor      Blocking LLM.invoke() runs in thread pool so async
                             streams and heartbeats work without blocking the loop.
"""

import asyncio
import json
import logging
import re
import threading
import time
from typing import AsyncGenerator, Callable

import requests as _http
from langchain_ollama import ChatOllama

from config import get_settings
from mcp_tools import (
    check_inventory, insert_inventory, update_inventory, delete_inventory,
    create_bom, get_bom, update_bom, delete_bom,
    run_bom, check_bom_buildability,
)

logger = logging.getLogger("mcp_host.agent")
cfg    = get_settings()


def _do_send_customer_email(bom_name: str, lead_time_days: int, quantity: int) -> None:
    """Actual HTTP call — always runs in a background daemon thread."""
    customer_email = cfg.CUSTOMER_EMAIL
    if not customer_email:
        logger.warning("CUSTOMER_EMAIL not set in .env — skipping customer notification.")
        return
    try:
        resp = _http.post(
            f"{cfg.MAILER_URL}/send-customer-confirmation",
            json={
                "bom_name":       bom_name,
                "lead_time_days": lead_time_days,
                "customer_email": customer_email,
                "quantity":       quantity,
            },
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("Customer confirmation sent to %s for %s × %d", customer_email, bom_name, quantity)
    except _http.exceptions.ConnectionError:
        logger.warning("Customer email failed — mailer unreachable at %s. "
                       "Start it with: cd erp_mail_system && node server.js", cfg.MAILER_URL)
    except _http.exceptions.HTTPError as exc:
        logger.warning("Customer email failed — mailer HTTP %s: %s",
                       exc.response.status_code, exc.response.text[:120])
    except Exception as exc:
        logger.warning("Customer email failed: %s", exc)


def _send_customer_email(bom_name: str, lead_time_days: int, quantity: int) -> None:
    """
    Fire-and-forget: spawns a daemon thread to call the mailer.
    Returns immediately — never blocks the chat response.
    """
    t = threading.Thread(
        target=_do_send_customer_email,
        args=(bom_name, lead_time_days, quantity),
        daemon=True,
    )
    t.start()

# ── OPT-1 + OPT-3: think=False, num_predict=300 ────────────────────────────
# bind(think=False) disables gemma4's chain-of-thought reasoning pass.
# Without this the model generates hundreds of hidden tokens before any output,
# causing empty responses when num_predict was too low.
_llm_base = ChatOllama(
    base_url    = cfg.OLLAMA_BASE_URL,
    model       = cfg.OLLAMA_MODEL,
    temperature = 0,
    num_ctx     = 2048,
    num_predict = 300,
)
_llm = _llm_base.bind(think=False)   # OPT-1

# ── Tool map ────────────────────────────────────────────────────────────────
_TOOL_MAP = {
    "check_inventory":        check_inventory,
    "insert_inventory":       insert_inventory,
    "update_inventory":       update_inventory,
    "delete_inventory":       delete_inventory,
    "create_bom":             create_bom,
    "get_bom":                get_bom,
    "update_bom":             update_bom,
    "delete_bom":             delete_bom,
    "run_bom":                run_bom,
    "check_bom_buildability": check_bom_buildability,
}

# Tool badge metadata for the UI (judges see MCP routing live)
_TOOL_META = {
    "check_inventory":        {"label": "Inventory Lookup",    "icon": "fa-search",      "color": "indigo"},
    "insert_inventory":       {"label": "New Item Insert",     "icon": "fa-plus",        "color": "teal"},
    "update_inventory":       {"label": "Stock Update",        "icon": "fa-edit",        "color": "emerald"},
    "delete_inventory":       {"label": "Item Deletion",       "icon": "fa-trash",       "color": "rose"},
    "create_bom":             {"label": "BOM Creation",        "icon": "fa-plus-circle", "color": "cyan"},
    "get_bom":                {"label": "BOM Detail View",     "icon": "fa-list-alt",    "color": "violet"},
    "update_bom":             {"label": "BOM Update",          "icon": "fa-pencil-alt",  "color": "amber"},
    "delete_bom":             {"label": "BOM Deletion",        "icon": "fa-trash-alt",   "color": "rose"},
    "run_bom":                {"label": "BOM Production Run",  "icon": "fa-play-circle", "color": "green"},
    "check_bom_buildability": {"label": "Buildability Check",  "icon": "fa-check-circle","color": "cyan"},
}

# ── System prompt — kept minimal to reduce tokens processed per call ─────────
# Fewer input tokens = faster prefill on CPU.
_SYSTEM = """\
Output only JSON. No prose. No markdown.

check_inventory        → {"tool":"check_inventory","params":{"item_code":"","search":""}}
insert_inventory       → {"tool":"insert_inventory","params":{"code":"ITMxxx","description":"X","category":"X","uom":"pcs","quantity":1,"standard_cost":0.0,"lead_time":7}}
update_inventory       → {"tool":"update_inventory","params":{"item_code":"X","quantity_change":10,"reason":""}}
delete_inventory       → {"tool":"delete_inventory","params":{"item_code":"X"}}
get_bom                → {"tool":"get_bom","params":{"bom_name":"X"}}
run_bom                → {"tool":"run_bom","params":{"bom_name":"X","quantity":1}}
check_bom_buildability → {"tool":"check_bom_buildability","params":{"bom_name":"X","quantity":1}}
create_bom             → {"tool":"create_bom","params":{"name":"X","description":"X","output_quantity":1,"lead_time_days":14,"items_json":"[]"}}
update_bom             → {"tool":"update_bom","params":{"bom_name":"X","field":"X","value":"X"}}
delete_bom             → {"tool":"delete_bom","params":{"bom_name":"X"}}

BOM names: BOM-LAPTOP-STD, BOM-LAPTOP-FULL, BOM-LAPTOP-BUDGET, BOM-MOUSE-STD
"can I build/check buildable" → check_bom_buildability
"run/order/produce/start"     → run_bom
"show/view/get bom"           → get_bom
"add new item/insert/create item" → insert_inventory
"add/restock/receive"         → update_inventory positive quantity_change
"use/consume/remove/deduct"   → update_inventory negative quantity_change
"laptop full"→BOM-LAPTOP-FULL | "laptop std/assembly/kit/computer/pc"→BOM-LAPTOP-STD | "budget"→BOM-LAPTOP-BUDGET | "mouse"→BOM-MOUSE-STD"""

# ── OPT-2: Keyword pre-router ────────────────────────────────────────────────
# These patterns match with >99% confidence and never need LLM.
# Each tuple: (compiled_regex, tool_name, param_extractor(match, original_text))
_ITM_RE  = re.compile(r'\b(ITM\d{3})\b', re.IGNORECASE)
_NUM_RE  = re.compile(r'\b(\d+)\b')
_BOM_RE  = re.compile(r'\b(BOM-[\w-]+)\b', re.IGNORECASE)

_QUICK_ROUTES: list[tuple[re.Pattern, str, Callable]] = [
    # "show/list/check all inventory" — no params
    (re.compile(r'^\s*(?:show|list|view|check|get|display)\s+(?:all\s+)?inventory\s*$', re.I),
     'check_inventory', lambda m, t: {"item_code": "", "search": ""}),

    # "show inventory" with no extra words
    (re.compile(r'^\s*(?:inventory|stock)\s*$', re.I),
     'check_inventory', lambda m, t: {"item_code": "", "search": ""}),

    # exact ITM code anywhere in short query
    (re.compile(r'^\s*(?:show|check|get|view|find|lookup|what is|how many)?\s*(ITM\d{3})\s*$', re.I),
     'check_inventory', lambda m, t: {"item_code": _ITM_RE.search(t).group(1).upper(), "search": ""}),

    # "search for X" / "search X" / "find X in inventory"
    (re.compile(r'^\s*(?:search|find|look\s*up)\s+(?:for\s+)?(.+?)\s*(?:in\s+inventory)?\s*$', re.I),
     'check_inventory', lambda m, t: {"item_code": "", "search": m.group(1).strip()}),

    # "add N units to ITMXXX" / "restock ITMXXX by N"
    (re.compile(r'\b(?:add|restock|receive|put)\b.*\b(ITM\d{3})\b', re.I),
     'update_inventory', lambda m, t: {
         "item_code": _ITM_RE.search(t).group(1).upper(),
         "quantity_change": int(_NUM_RE.search(t).group(1)) if _NUM_RE.search(t) else 1,
         "reason": "restock",
     }),

    # "remove/use/consume/deduct N from ITMXXX"
    (re.compile(r'\b(?:remove|use|consume|deduct|take)\b.*\b(ITM\d{3})\b', re.I),
     'update_inventory', lambda m, t: {
         "item_code": _ITM_RE.search(t).group(1).upper(),
         "quantity_change": -(int(_NUM_RE.search(t).group(1)) if _NUM_RE.search(t) else 1),
         "reason": "consumption",
     }),
]


def _quick_route(text: str) -> tuple[str, dict] | None:
    """OPT-2: Try to route without LLM. Returns (tool_name, params) or None."""
    for pattern, tool_name, param_fn in _QUICK_ROUTES:
        m = pattern.search(text)
        if m:
            try:
                params = param_fn(m, text)
                logger.info("[ROUTER] Quick-routed to %s (no LLM)", tool_name)
                return tool_name, params
            except Exception:
                pass
    return None


# ── OPT-4: TTL response cache ────────────────────────────────────────────────
# Only caches read-only tools. Mutations (update/delete/create/run) are never cached.
_READ_ONLY = {"check_inventory", "get_bom", "check_bom_buildability"}
_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 5.0  # seconds


def _cache_key(tool_name: str, params: dict) -> str:
    return f"{tool_name}:{json.dumps(params, sort_keys=True)}"


def _cache_get(tool_name: str, params: dict) -> str | None:
    if tool_name not in _READ_ONLY:
        return None
    key = _cache_key(tool_name, params)
    if key in _cache:
        val, ts = _cache[key]
        if time.monotonic() - ts < _CACHE_TTL:
            logger.info("[CACHE] HIT  %s", key[:60])
            return val
        del _cache[key]
    return None


def _cache_set(tool_name: str, params: dict, result: str):
    if tool_name not in _READ_ONLY:
        return
    key = _cache_key(tool_name, params)
    _cache[key] = (result, time.monotonic())
    logger.info("[CACHE] SET  %s", key[:60])


# ── Session context (remembers last BOM + qty for "order it" queries) ────────
_session_ctx: dict[str, dict] = {}
_BOM_NAMES   = ["BOM-LAPTOP-STD", "BOM-LAPTOP-FULL", "BOM-LAPTOP-BUDGET", "BOM-MOUSE-STD"]
_BOM_KW      = {
    "budget":    "BOM-LAPTOP-BUDGET",
    "full":      "BOM-LAPTOP-FULL",
    "mouse":     "BOM-MOUSE-STD",
    "std":       "BOM-LAPTOP-STD",
    "standard":  "BOM-LAPTOP-STD",
    "laptop":    "BOM-LAPTOP-STD",
    # natural-language aliases people actually type
    "assembly":  "BOM-LAPTOP-STD",
    "kit":       "BOM-LAPTOP-STD",
    "notebook":  "BOM-LAPTOP-STD",
    "computer":  "BOM-LAPTOP-STD",
    "pc":        "BOM-LAPTOP-STD",
}
_PRONOUN_RE  = re.compile(r'\b(it|that|this|same|the bom|that bom|that one)\b', re.IGNORECASE)


def _save_ctx(session_id: str, tool_name: str, params: dict):
    ctx = _session_ctx.setdefault(session_id, {})
    if "bom_name" in params: ctx["bom"] = params["bom_name"]
    if "name"     in params: ctx["bom"] = params["name"]
    if "quantity" in params: ctx["qty"] = params["quantity"]


def _bom_from_text(text: str) -> str | None:
    """Extract a BOM name from natural language — checks explicit names first, then keywords."""
    upper = text.upper()
    for b in _BOM_NAMES:
        if b in upper:
            return b
    lower = text.lower()
    # priority order: specific variants before generic "laptop"
    for kw in ("budget", "full", "mouse", "assembly", "kit", "notebook",
                "computer", "pc", "std", "standard", "laptop"):
        if kw in lower and kw in _BOM_KW:
            return _BOM_KW[kw]
    return None


def _resolve_text(text: str, session_id: str) -> str:
    ctx = _session_ctx.get(session_id, {})
    bom = ctx.get("bom")
    qty = ctx.get("qty", 1)

    # 1. Resolve pronouns using session BOM (only when no explicit BOM in text)
    if _PRONOUN_RE.search(text) and not any(b in text.upper() for b in _BOM_NAMES):
        if bom:
            text = _PRONOUN_RE.sub(bom, text)

    # 2. "order X" → "run BOM quantity X"
    #    RULE: extract BOM from the text itself first.
    #    Only fall back to session BOM when the text is an explicit pronoun ("order it").
    if re.search(r'\border\b', text, re.I) and "run" not in text.lower():
        text_bom = _bom_from_text(text)
        is_pronoun = bool(_PRONOUN_RE.search(text))
        resolved_bom = text_bom or (bom if is_pronoun else None)
        if resolved_bom:
            q = int(m.group(1)) if (m := _NUM_RE.search(text)) else qty
            text = f"run {resolved_bom} quantity {q}"
        # If no BOM found in text and not a pronoun reference, let LLM decide

    text = re.sub(r'\band update inventory\b', '', text, flags=re.I).strip()
    return text


def _normalize_bom(name: str) -> str:
    if not name:
        return name
    upper = re.sub(r'[\s_]+', '-', name.strip()).upper()
    if upper in _BOM_NAMES:
        return upper
    lower = name.lower()
    for kw in ("budget", "full", "mouse", "assembly", "kit", "std", "standard", "laptop"):
        if kw in lower and kw in _BOM_KW:
            return _BOM_KW[kw]
    return upper


def _extract_json(text: str) -> dict:
    text  = re.sub(r'```[a-zA-Z]*\n?', '', text).strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON in LLM output: {text!r}")
    parsed = json.loads(match.group())
    params = parsed.get("params", {})
    for key in ("bom_name", "name"):
        if key in params and params[key]:
            params[key] = _normalize_bom(params[key])
    return parsed


# ── Rich Python formatters ───────────────────────────────────────────────────

def _fmt_inventory(rows: list[dict]) -> str:
    if not rows:
        return "No inventory items found."
    lines = []
    for r in rows:
        avail  = r.get("available", r.get("quantity", "?"))
        in_use = r.get("quantity_in_use", 0)
        line   = f"• {r['code']} — {r.get('description','')} | {avail} {r.get('uom','')} available"
        if in_use:
            line += f" ({in_use} reserved)"
        lines.append(line)
    header = f"Found {len(rows)} item(s):\n"
    body   = "\n".join(lines[:25])
    tail   = f"\n… and {len(rows)-25} more." if len(rows) > 25 else ""
    return header + body + tail


def _fmt_bom(raw: str) -> str:
    try:
        data = json.loads(raw)
    except Exception:
        return raw
    bom   = data.get("bom", {})
    comp  = data.get("components", [])
    ok    = [c for c in comp if int(c.get("available", 0)) >= int(c.get("qty_required", 0))]
    short = [c for c in comp if int(c.get("available", 0)) <  int(c.get("qty_required", 0))]
    lines = [
        f"BOM: {bom.get('name')}  —  {bom.get('description', '')}",
        f"Output: {bom.get('output_quantity')} unit(s)  |  Lead time: {bom.get('lead_time_days')} days",
        f"Components: {len(comp)} total  |  {len(ok)} available  |  {len(short)} short",
        "",
    ]
    for c in comp:
        avail  = int(c.get("available", 0))
        needed = int(c.get("qty_required", 0))
        mark   = "OK " if avail >= needed else "LOW"
        lines.append(f"  [{mark}] {c['item_code']} — {c.get('description','')} | need {needed}, have {avail} {c.get('uom','')}")
    return "\n".join(lines)


def _fmt_buildability(raw: str) -> str:
    try:
        data = json.loads(raw)
    except Exception:
        return raw
    status    = data.get("status")
    bom       = data.get("bom_name", "")
    qty       = data.get("quantity", 1)

    if status == "can_build":
        lt    = data.get("lead_time_days", "?")
        weeks = round(int(lt) / 7, 1) if str(lt).isdigit() else "?"
        comps = ", ".join(data.get("components_available", []))
        return (
            f"Yes! {bom} × {qty} can be built from current stock.\n"
            f"All components available. Est. production: {lt} days (~{weeks} weeks).\n"
            f"Components in stock: {comps}"
        )
    if status == "in_stock":
        return data.get("message", raw)
    if status == "shortage":
        shortages   = data.get("shortages", [])
        lt          = data.get("lead_time_days", "?")
        short_names = ", ".join(s["item_code"] for s in shortages)
        lines = [
            f"Cannot build {bom} × {qty} — {len(shortages)} component(s) are short:",
            "",
        ]
        for s in shortages:
            lines.append(
                f"  • {s['item_code']} ({s['description']}): "
                f"need {s['required']}, have {s['available']}, short by {s['shortage']} {s['uom']}"
            )
        lines += [
            "",
            f"If ordered now, {bom} can be built in ~{lt} days.",
            "Reply 'order it' to send a vendor purchase email.",
        ]
        return "\n".join(lines)
    return data.get("message", raw)


def _fmt_run_bom(raw: str) -> tuple[str, list[dict]]:
    try:
        data = json.loads(raw)
    except Exception:
        return raw, []
    status    = data.get("status")
    bom       = data.get("bom_name", "")
    qty       = data.get("quantity", 1)
    shortages = data.get("shortages", [])
    if status == "success":
        blocked = data.get("blocked", [])
        lt      = data.get("lead_time_days", 14)
        summary = ", ".join(f"{b['item_code']}×{b['block_qty']}" for b in blocked[:5])
        if len(blocked) > 5:
            summary += f" +{len(blocked)-5} more"
        # Fire customer notification in background — never blocks the response
        _send_customer_email(bom, int(lt), int(qty))
        weeks = round(int(lt) / 7, 1)
        email_note = (f"📧 Confirmation email dispatched to {cfg.CUSTOMER_EMAIL}."
                      if cfg.CUSTOMER_EMAIL else "")
        return (
            f"Production started! {bom} × {qty} is now running.\n"
            f"Inventory reserved for {len(blocked)} component(s): {summary}.\n"
            f"Expected completion: {lt} days (~{weeks} weeks)."
            + (f"\n{email_note}" if email_note else "")
        ), []
    if status == "shortage":
        names = ", ".join(s["item_code"] for s in shortages)
        return (
            f"Cannot run {bom} × {qty} — {len(shortages)} item(s) short: {names}.\n"
            f"Order from vendor to proceed. See shortage table below."
        ), shortages
    return data.get("message", raw), shortages


def _execute_and_format(tool_name: str, params: dict) -> tuple[str, list[dict]]:
    """OPT-4: Check cache first, then execute tool, then cache result."""
    # Cache read
    cached = _cache_get(tool_name, params)
    if cached is not None:
        # Re-format from cached raw result
        pass  # fall through to format step

    tool = _TOOL_MAP.get(tool_name)
    if not tool:
        return f"Unknown tool '{tool_name}'.", []

    # OPT-4: use cached raw result or call tool
    raw_cached = _cache_get(tool_name, params)
    if raw_cached is None:
        result = tool.invoke(params)
        _cache_set(tool_name, params, result)
    else:
        result = raw_cached

    shortages: list[dict] = []

    if tool_name == "check_inventory":
        try:
            rows = json.loads(result)
            if isinstance(rows, list):
                return _fmt_inventory(rows), []
        except Exception:
            pass
        return result, []

    if tool_name == "insert_inventory":
        return result, []   # tool already returns a formatted string

    if tool_name == "get_bom":
        return _fmt_bom(result), []

    if tool_name == "check_bom_buildability":
        return _fmt_buildability(result), []

    if tool_name == "run_bom":
        return _fmt_run_bom(result)

    return result, []


# ── LLM call (blocking, runs in thread pool) ────────────────────────────────

def _call_llm(text: str) -> tuple[str, dict]:
    """OPT-7: Blocking LLM call — always called via run_in_executor."""
    resp   = _llm.invoke([{"role": "system", "content": _SYSTEM}, {"role": "user", "content": text}])
    raw    = resp.content.strip()
    logger.info("LLM → %s", raw[:120])
    parsed = _extract_json(raw)
    return parsed["tool"], parsed.get("params", {})


# ── Sync agent (Discord bot) ─────────────────────────────────────────────────

def run_agent(user_text: str, session_id: str = "default") -> tuple[str, list[dict]]:
    resolved = _resolve_text(user_text, session_id)

    # OPT-2: try keyword router first
    routed = _quick_route(resolved)
    if routed:
        tool_name, params = routed
    else:
        try:
            tool_name, params = _call_llm(resolved)
        except Exception as exc:
            logger.error("LLM failed: %s", exc)
            return (
                "Couldn't understand that. Try:\n"
                "• 'show all inventory'\n"
                "• 'can I build BOM-LAPTOP-FULL × 10'\n"
                "• 'run BOM-MOUSE-STD quantity 2'", []
            )

    _save_ctx(session_id, tool_name, params)
    logger.info("Tool: %s  params: %s", tool_name, params)
    try:
        return _execute_and_format(tool_name, params)
    except Exception as exc:
        logger.error("Tool '%s' failed: %s", tool_name, exc)
        return f"Tool error: {exc}", []


# ── Async streaming agent (/chat/stream) ─────────────────────────────────────

async def run_agent_stream(
    user_text: str, session_id: str = "default"
) -> AsyncGenerator[dict, None]:
    """
    SSE event types:
      status  {"type":"status","text":"..."}
      tool    {"type":"tool","name":"...","label":"...","icon":"...","color":"..."}
      token   {"type":"token","text":"..."}
      done    {"type":"done","shortages":[...]}
      error   {"type":"error","text":"..."}
    """
    resolved = _resolve_text(user_text, session_id)

    # ── OPT-2: keyword pre-router (instant, no LLM wait) ───────────────────
    routed = _quick_route(resolved)

    if routed:
        tool_name, params = routed
        yield {"type": "status", "text": "Routing…"}
    else:
        # ── OPT-7: LLM in thread pool + heartbeat dots ──────────────────────
        yield {"type": "status", "text": "Thinking…"}
        loop     = asyncio.get_running_loop()
        llm_task = loop.run_in_executor(None, lambda: _call_llm(resolved))

        dots = 0
        while not llm_task.done():
            await asyncio.sleep(1.5)
            if llm_task.done():
                break
            dots = (dots % 3) + 1
            yield {"type": "status", "text": "Thinking" + "." * dots}

        try:
            tool_name, params = await llm_task
        except Exception as exc:
            logger.error("LLM failed: %s", exc)
            yield {"type": "error", "text": (
                "Couldn't parse that. Try:\n"
                "• 'can I build BOM-LAPTOP-FULL × 10'\n"
                "• 'show all inventory'\n"
                "• 'run BOM-MOUSE-STD quantity 2'"
            )}
            return

    _save_ctx(session_id, tool_name, params)

    # ── Tool badge: judges see MCP routing live ─────────────────────────────
    meta = _TOOL_META.get(tool_name, {"label": tool_name, "icon": "fa-cog", "color": "slate"})
    yield {"type": "tool", "name": tool_name, "label": meta["label"],
           "icon": meta["icon"], "color": meta["color"]}

    # ── OPT-4 + OPT-6: execute tool (cached or fresh DB query) ─────────────
    try:
        answer, shortages = await asyncio.to_thread(_execute_and_format, tool_name, params)
    except Exception as exc:
        logger.error("Tool '%s' failed: %s", tool_name, exc)
        yield {"type": "error", "text": f"Tool execution failed: {exc}"}
        return

    # ── OPT-10: word-by-word stream (typewriter effect) ─────────────────────
    # asyncio.sleep(0.03) ensures each word is a separate HTTP chunk visible
    # to the browser before the next word arrives.
    for word in answer.split(" "):
        yield {"type": "token", "text": word + " "}
        await asyncio.sleep(0.03)

    yield {"type": "done", "shortages": shortages}


# ── OPT-5: Async warmup — call on app startup ────────────────────────────────

async def warmup_llm():
    """
    Sends a tiny prompt to Ollama at startup so the model is fully loaded
    into memory before the first user query arrives.
    Eliminates the ~15-second cold-start penalty on the first request.
    """
    try:
        logger.info("Warming up LLM…")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: _llm.invoke(
            [{"role": "user", "content": "ping"}]
        ))
        logger.info("LLM warmup complete.")
    except Exception as exc:
        logger.warning("LLM warmup failed (non-fatal): %s", exc)
