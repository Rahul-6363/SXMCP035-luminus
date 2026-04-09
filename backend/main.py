"""
FastAPI entry-point — ERP MCP Host backend.

Routes:
  GET  /health          — liveness check
  GET  /api/items       — all inventory items (used by frontend table)
  GET  /api/bom         — all BOMs
  POST /chat            — natural language → agent → response + shortages
"""

import asyncio
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

from agent import run_agent, run_agent_stream, warmup_llm
from init_db import init_db
from mail_reader import start_mail_poller
from mcp_tools import _engine, _rows

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger("mcp_host")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()           # create tables + seed on first run
    await warmup_llm()  # pre-load LLM into VRAM
    asyncio.create_task(start_mail_poller())  # background IMAP poller
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


# ---------------------------------------------------------------------------
# Shipment routes
# ---------------------------------------------------------------------------

@app.get("/api/shipments")
def get_shipments(status: str = "pending"):
    """Returns shipments filtered by status: pending | approved | rejected | all."""
    try:
        with _engine.connect() as conn:
            if status == "all":
                rows = _rows(conn,
                    "SELECT * FROM pending_shipments ORDER BY created_at DESC LIMIT 50")
            else:
                rows = _rows(conn,
                    "SELECT * FROM pending_shipments WHERE status = :s "
                    "ORDER BY created_at DESC",
                    s=status)
        # parsed_items is stored as JSON string in MySQL — parse it
        for r in rows:
            if isinstance(r.get("parsed_items"), str):
                try:
                    r["parsed_items"] = json.loads(r["parsed_items"])
                except Exception:
                    r["parsed_items"] = []
        return rows
    except Exception as exc:
        logger.exception("get_shipments error")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/shipments/pending-count")
def pending_shipment_count():
    """Lightweight count used by the navbar badge."""
    try:
        with _engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM pending_shipments WHERE status = 'pending'")
            ).scalar()
        return {"count": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/shipments/{shipment_id}/approve")
def approve_shipment(shipment_id: int):
    """Approve a pending shipment → update inventory for each parsed item."""
    try:
        with _engine.connect() as conn:
            rows = _rows(conn,
                "SELECT * FROM pending_shipments WHERE id = :id", id=shipment_id)
        if not rows:
            raise HTTPException(status_code=404, detail="Shipment not found.")
        shipment = rows[0]
        if shipment["status"] != "pending":
            raise HTTPException(status_code=400,
                detail=f"Shipment is already '{shipment['status']}'.")

        items = shipment.get("parsed_items") or []
        if isinstance(items, str):
            items = json.loads(items)

        updated, skipped = [], []
        with _engine.begin() as conn:
            for item in items:
                code = item.get("item_code", "").strip().upper()
                qty  = int(item.get("quantity", 0))
                if not code or qty <= 0:
                    skipped.append(item)
                    continue
                exists = _rows(conn, "SELECT code FROM items WHERE code = :code", code=code)
                if not exists:
                    skipped.append(item)
                    logger.warning("Approve shipment #%d: item %s not in inventory — skipped.", shipment_id, code)
                    continue
                conn.execute(text(
                    "UPDATE items SET quantity = quantity + :qty WHERE code = :code"),
                    {"qty": qty, "code": code})
                updated.append({"item_code": code, "quantity_added": qty})
            # Mark approved
            conn.execute(text(
                "UPDATE pending_shipments SET status = 'approved' WHERE id = :id"),
                {"id": shipment_id})

        logger.info("Shipment #%d approved — %d item(s) updated.", shipment_id, len(updated))
        return {
            "success": True,
            "shipment_id": shipment_id,
            "items_updated": updated,
            "items_skipped": skipped,
            "message": f"Shipment approved. {len(updated)} inventory item(s) updated.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("approve_shipment error")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/shipments/{shipment_id}/reject")
def reject_shipment(shipment_id: int):
    """Reject a pending shipment without touching inventory."""
    try:
        with _engine.begin() as conn:
            rows = _rows(conn,
                "SELECT id, status FROM pending_shipments WHERE id = :id", id=shipment_id)
            if not rows:
                raise HTTPException(status_code=404, detail="Shipment not found.")
            if rows[0]["status"] != "pending":
                raise HTTPException(status_code=400,
                    detail=f"Shipment is already '{rows[0]['status']}'.")
            conn.execute(text(
                "UPDATE pending_shipments SET status = 'rejected' WHERE id = :id"),
                {"id": shipment_id})
        logger.info("Shipment #%d rejected.", shipment_id)
        return {"success": True, "shipment_id": shipment_id,
                "message": "Shipment rejected. Inventory unchanged."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("reject_shipment error")
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

    # Browsers (Chrome/Firefox) buffer SSE until they receive ~1–4 KB.
    # Sending a 2 KB SSE comment at the start forces them to begin reading
    # immediately. SSE comments start with ":" and are silently ignored.
    _FLUSH_PAD = ": " + " " * 2048 + "\n\n"

    async def event_generator():
        # Send flush pad first so browser starts reading right away
        yield _FLUSH_PAD
        await asyncio.sleep(0)
        try:
            async for event in run_agent_stream(payload.text, session_id=payload.session_id):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0)   # hand control back → uvicorn flushes chunk
        except Exception as exc:
            logger.exception("Stream error")
            yield f"data: {json.dumps({'type': 'error', 'text': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",        # disable nginx/proxy buffering
            "Connection":        "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )
