"""
FastAPI entry-point — ERP MCP Host backend.

Routes:
  GET  /health          — liveness check
  GET  /api/items       — all inventory items (used by frontend table)
  GET  /api/bom         — all BOMs
  POST /chat            — natural language → agent → response + shortages
"""

import json
import logging
import time
from contextlib import asynccontextmanager

import requests as http_requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from agent import run_agent, run_agent_stream
from init_db import init_db
from mcp_tools import _engine, _rows

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger("mcp_host")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()   # create tables + seed on first run
    yield

app = FastAPI(title="ERP MCP Host", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1)
    session_id: str = "default"


class ShortageItem(BaseModel):
    item_code: str
    description: str
    uom: str
    required: int
    available: int
    shortage: int


class ChatResponse(BaseModel):
    response: str
    shortages: list[ShortageItem] = []
    elapsed_seconds: float


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/test-llm")
def test_llm():
    """Sends a minimal prompt directly to Ollama — bypasses the agent entirely."""
    from config import get_settings
    from langchain_ollama import ChatOllama
    cfg = get_settings()
    try:
        llm = ChatOllama(base_url=cfg.OLLAMA_BASE_URL, model=cfg.OLLAMA_MODEL, temperature=0)
        response = llm.invoke([{"role": "user", "content": "Reply with just the word: WORKING"}])
        return {"status": "ok", "model": cfg.OLLAMA_MODEL, "reply": response.content}
    except Exception as exc:
        return {"status": "error", "model": cfg.OLLAMA_MODEL, "error": str(exc)}


@app.get("/api/status")
def status():
    """Checks DB connection, row counts, and Ollama availability."""
    from config import get_settings
    cfg = get_settings()
    result = {}

    # 1. Database
    try:
        with _engine.connect() as conn:
            inv_count = conn.execute(text("SELECT COUNT(*) FROM items")).scalar()
            bom_count = conn.execute(text("SELECT COUNT(*) FROM bom")).scalar()
        result["database"] = {
            "connected": True,
            "inventory_rows": inv_count,
            "bom_rows": bom_count,
        }
    except Exception as exc:
        result["database"] = {"connected": False, "error": str(exc)}

    # 2. Ollama / LLM
    try:
        r = http_requests.get(f"{cfg.OLLAMA_BASE_URL}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        result["ollama"] = {
            "reachable": True,
            "model_loaded": cfg.OLLAMA_MODEL in models,
            "model": cfg.OLLAMA_MODEL,
            "available_models": models,
        }
    except Exception as exc:
        result["ollama"] = {"reachable": False, "error": str(exc)}

    return result


@app.get("/api/items")
def get_items():
    """Returns all inventory rows for the frontend table."""
    try:
        with _engine.connect() as conn:
            rows = _rows(conn,
                "SELECT *, (quantity - quantity_in_use) AS available "
                "FROM items ORDER BY category, code")
        return rows
    except Exception as exc:
        logger.exception("get_items error")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/bom")
def get_boms():
    """Returns all BOMs with their component counts."""
    try:
        with _engine.connect() as conn:
            rows = _rows(conn, """
                SELECT b.*, COUNT(bi.id) AS component_count
                FROM bom b
                LEFT JOIN bom_items bi ON bi.bom_id = b.id
                GROUP BY b.id
                ORDER BY b.name
            """)
        return rows
    except Exception as exc:
        logger.exception("get_boms error")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/bom/{bom_name}")
def get_bom_detail(bom_name: str):
    """Returns a single BOM with all components and their live stock status."""
    try:
        with _engine.connect() as conn:
            bom = _rows(conn, "SELECT * FROM bom WHERE name = :name", name=bom_name)
            if not bom:
                raise HTTPException(status_code=404, detail=f"BOM '{bom_name}' not found.")
            components = _rows(conn, """
                SELECT bi.item_code, bi.qty_required,
                       i.description, i.uom, i.standard_cost,
                       i.quantity, i.quantity_in_use,
                       (i.quantity - i.quantity_in_use) AS available
                FROM bom_items bi
                JOIN items i ON i.code = bi.item_code
                WHERE bi.bom_id = :bom_id
            """, bom_id=bom[0]["id"])
        return {"bom": bom[0], "components": components}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_bom_detail error")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    logger.info("Query: %s", payload.text)
    t0 = time.perf_counter()

    try:
        answer, shortages = run_agent(payload.text, session_id=payload.session_id)
    except Exception as exc:
        logger.exception("Agent error")
        raise HTTPException(status_code=500, detail=str(exc))

    elapsed = round(time.perf_counter() - t0, 2)
    logger.info("Done in %.2fs | shortages=%d", elapsed, len(shortages))

    return ChatResponse(
        response=answer,
        shortages=[ShortageItem(**s) for s in shortages],
        elapsed_seconds=elapsed,
    )


@app.post("/chat/stream")
async def chat_stream(payload: ChatRequest):
    """SSE streaming endpoint — yields events as the agent progresses."""
    logger.info("Stream query: %s", payload.text)

    async def event_generator():
        try:
            async for event in run_agent_stream(payload.text, session_id=payload.session_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            logger.exception("Stream error")
            yield f"data: {json.dumps({'type': 'error', 'text': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
