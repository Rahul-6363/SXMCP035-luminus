"""
FastAPI entry-point — MCP Host backend.

POST /chat  {"text": "<user question>"}  →  {"response": "<natural language answer>"}
"""

import logging
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import run_agent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger("mcp_host")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MCP Host — Ollama × SQL",
    description="Connects Gemma 27b (Ollama) to a MySQL database via MCP tools.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, description="User's natural-language question")


class ChatResponse(BaseModel):
    response: str
    elapsed_seconds: float


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    logger.info("Received query: %s", payload.text)
    t0 = time.perf_counter()

    try:
        answer = run_agent(payload.text)
    except Exception as exc:
        logger.exception("Agent error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    elapsed = round(time.perf_counter() - t0, 2)
    logger.info("Responded in %.2fs", elapsed)
    return ChatResponse(response=answer, elapsed_seconds=elapsed)
