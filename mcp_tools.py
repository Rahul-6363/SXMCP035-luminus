"""
MCP Tools — read_schema, create_sql_query, check_db.

Agentic autonomy guarantee:
  - Raw database rows never leave check_db.
  - The agent only ever receives the natural-language summary produced here.
"""

import re
import textwrap
import traceback
from typing import Any

import pymysql
import pymysql.cursors
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from config import get_settings

cfg = get_settings()

# ---------------------------------------------------------------------------
# Shared helper: one Ollama client reused across tools
# ---------------------------------------------------------------------------
_llm = ChatOllama(base_url=cfg.ollama_base_url, model=cfg.ollama_model, temperature=0)


def _db_connection() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=cfg.db_host,
        port=cfg.db_port,
        user=cfg.db_user,
        password=cfg.db_password,
        database=cfg.db_name,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )


# ---------------------------------------------------------------------------
# Tool 1 – read_schema
# ---------------------------------------------------------------------------
@tool
def read_schema() -> str:
    """
    Reads and returns the SQL database schema.
    Always call this first before generating any SQL query.
    """
    try:
        with open(cfg.schema_path, "r", encoding="utf-8") as fh:
            schema = fh.read().strip()
        return f"DATABASE SCHEMA:\n{schema}"
    except FileNotFoundError:
        return f"ERROR: Schema file '{cfg.schema_path}' not found."


# ---------------------------------------------------------------------------
# Tool 2 – create_sql_query
# ---------------------------------------------------------------------------
@tool
def create_sql_query(prompt: str) -> str:
    """
    Converts a natural-language request (which MUST include the schema) into
    a raw SQL query.

    Args:
        prompt: Natural language question combined with the database schema.

    Returns:
        A single raw SQL statement — no markdown, no explanation.
    """
    system = textwrap.dedent("""\
        You are a precise SQL generator.
        Rules you MUST follow:
          1. Output ONLY the raw SQL statement — nothing else.
          2. No markdown fences (no ```sql), no explanations, no comments.
          3. The query must be valid MySQL syntax.
          4. Use only tables and columns defined in the schema provided.
          5. If the request is ambiguous, produce the most reasonable query.
    """)

    response = _llm.invoke([
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ])

    sql = response.content.strip()
    # Strip accidental markdown fences if the model disobeys
    sql = re.sub(r"^```[a-zA-Z]*\n?", "", sql)
    sql = re.sub(r"\n?```$", "", sql)
    return sql.strip()


# ---------------------------------------------------------------------------
# Tool 3 – check_db
# ---------------------------------------------------------------------------
@tool
def check_db(sql_query: str) -> str:
    """
    Executes a SQL query against the database and returns a natural-language
    summary of the results.  Raw rows are NEVER exposed outside this function.

    Args:
        sql_query: A valid MySQL SELECT statement.

    Returns:
        A human-readable summary of the query results.
    """
    # Safety: allow only SELECT statements
    normalised = sql_query.strip().upper()
    if not normalised.startswith("SELECT"):
        return "ERROR: Only SELECT queries are permitted."

    try:
        conn = _db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                rows: list[dict[str, Any]] = cur.fetchall()
    except pymysql.Error as exc:
        return f"DATABASE ERROR: {exc}"
    except Exception:
        return f"UNEXPECTED ERROR:\n{traceback.format_exc()}"

    if not rows:
        return "The query returned no results."

    # -----------------------------------------------------------------------
    # Summarise — the LLM sees only a compact JSON-like representation,
    # which is immediately converted to prose before being returned.
    # -----------------------------------------------------------------------
    max_rows = 50  # cap to avoid enormous prompts
    truncated = len(rows) > max_rows
    sample = rows[:max_rows]

    summary_prompt = textwrap.dedent(f"""\
        The following data was returned by a database query.
        Summarise the findings in clear, concise natural language for a
        business user.  Do NOT list every row; highlight patterns, totals,
        notable values, or anomalies instead.
        {"(Note: only the first 50 of " + str(len(rows)) + " rows are shown.)" if truncated else ""}

        DATA:
        {sample}
    """)

    summary_response = _llm.invoke([
        {"role": "system", "content": "You are a helpful data analyst who explains query results in plain English."},
        {"role": "user", "content": summary_prompt},
    ])

    return summary_response.content.strip()
