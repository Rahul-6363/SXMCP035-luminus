"""
LangGraph ReAct agent — MCP Host layer.

Execution contract (enforced via system prompt):
  Step 1 → read_schema()
  Step 2 → create_sql_query(user_question + schema)
  Step 3 → check_db(sql)
  Step 4 → return check_db's natural-language summary to the user.

The agent MUST NOT answer the user from its own knowledge;
it MUST always complete all three tool steps.
"""

import textwrap

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from config import get_settings
from mcp_tools import check_db, create_sql_query, read_schema

cfg = get_settings()

# ---------------------------------------------------------------------------
# System prompt — drives agentic discipline
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = textwrap.dedent("""\
    You are a database assistant with access to exactly three tools:

      1. read_schema      — fetches the live database schema (call first, always).
      2. create_sql_query — converts (question + schema) into a raw SQL query.
      3. check_db         — executes SQL and returns a plain-English summary.

    MANDATORY WORKFLOW — follow these steps in order for every user request:
      a) Call read_schema() to obtain the schema.
      b) Call create_sql_query() passing the user's question AND the schema text.
      c) Call check_db() with the SQL produced in step (b).
      d) Return the natural-language answer produced by check_db() verbatim.

    CONSTRAINTS:
      • Never answer from your own knowledge — always run all three tools.
      • Never expose raw SQL or raw data to the user.
      • Never skip or reorder the steps.
      • If a tool returns an error, report it clearly to the user.
""")

# ---------------------------------------------------------------------------
# LLM with tools bound
# ---------------------------------------------------------------------------
_base_llm = ChatOllama(
    base_url=cfg.ollama_base_url,
    model=cfg.ollama_model,
    temperature=0,
)

TOOLS = [read_schema, create_sql_query, check_db]

# create_react_agent handles the tool-call / observe / think loop automatically
graph = create_react_agent(
    model=_base_llm,
    tools=TOOLS,
    prompt=SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# Public interface used by main.py
# ---------------------------------------------------------------------------
def run_agent(user_text: str) -> str:
    """
    Runs the full MCP tool-chain for a user question and returns the
    natural-language answer.
    """
    result = graph.invoke({"messages": [{"role": "user", "content": user_text}]})

    # The last message in the conversation is the final agent response
    messages = result.get("messages", [])
    for msg in reversed(messages):
        # AIMessage with no tool_calls = the final answer
        if hasattr(msg, "tool_calls") and not msg.tool_calls and msg.content:
            return msg.content
        if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
            return msg.content

    return "No response generated."
