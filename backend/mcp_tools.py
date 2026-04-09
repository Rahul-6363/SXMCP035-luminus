"""
MCP Domain Tools for ERP — Inventory & BOM management.

Tools:
  check_inventory         — view inventory items
  insert_inventory        — add a brand-new inventory item
  update_inventory        — adjust stock quantity
  delete_inventory        — remove an inventory item
  create_bom              — define a new Bill of Materials
  get_bom                 — view BOM with component stock status
  update_bom              — modify BOM header fields
  delete_bom              — remove a BOM
  run_bom                 — execute BOM: block inventory or return shortages
  check_bom_buildability  — read-only check if BOM can be built
"""

import json
import logging
from typing import Any
from urllib.parse import quote_plus

from langchain_core.tools import tool
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from config import get_settings

logger = logging.getLogger("mcp_host.tools")
cfg = get_settings()

_engine = create_engine(
    f"mysql+pymysql://{quote_plus(cfg.DB_USER)}:{quote_plus(cfg.DB_PASSWORD)}"
    f"@{cfg.DB_HOST}:{cfg.DB_PORT}/{cfg.DB_NAME}",
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)


def _rows(conn, sql: str, **params) -> list[dict]:
    result = conn.execute(text(sql), params)
    return [dict(r._mapping) for r in result]


# ---------------------------------------------------------------------------
# Tool 1 — check_inventory
# ---------------------------------------------------------------------------
@tool
def check_inventory(item_code: str = "", search: str = "") -> str:
    """
    Returns inventory details.
    - item_code: exact code lookup (e.g. 'ITM011')
    - search: keyword search across description and category (e.g. 'cooling fan')
    - both empty: returns all items

    Args:
        item_code: Exact inventory item code.
        search:    Keyword to search in description or category.
    """
    try:
        with _engine.connect() as conn:
            if item_code:
                rows = _rows(conn,
                    "SELECT *, (quantity - quantity_in_use) AS available "
                    "FROM items WHERE code = :code",
                    code=item_code)
                if not rows:
                    return f"No inventory item found with code '{item_code}'."
            elif search:
                rows = _rows(conn,
                    "SELECT *, (quantity - quantity_in_use) AS available "
                    "FROM items WHERE description LIKE :s OR category LIKE :s "
                    "ORDER BY category, code",
                    s=f"%{search}%")
                if not rows:
                    return f"No items found matching '{search}'."
            else:
                rows = _rows(conn,
                    "SELECT *, (quantity - quantity_in_use) AS available "
                    "FROM items ORDER BY category, code")
        return json.dumps(rows, default=str)
    except SQLAlchemyError as exc:
        logger.error("check_inventory error: %s", exc)
        return f"DATABASE ERROR: {exc}"


# ---------------------------------------------------------------------------
# Tool 2 — insert_inventory
# ---------------------------------------------------------------------------
@tool
def insert_inventory(
    code: str,
    description: str,
    category: str,
    uom: str,
    quantity: int,
    standard_cost: float = 0.0,
    lead_time: int = 7,
) -> str:
    """
    Inserts a brand-new inventory item into the ERP system.

    Field reference (what to provide and their data types):
      code          : str   — Unique item code. Convention: 'ITMxxx' (e.g. 'ITM031').
                              Must not already exist in the system.
      description   : str   — Human-readable item name (e.g. 'USB-C Charging Cable 1m').
      category      : str   — Item category (e.g. 'Cables', 'Electronics', 'Cooling',
                              'Packaging', 'Accessories').
      uom           : str   — Unit of measure: 'pcs', 'kg', 'm', 'litre', 'set', etc.
      quantity      : int   — Opening stock count (e.g. 100).
      standard_cost : float — Cost per unit in INR (optional, default 0.0).
      lead_time     : int   — Procurement lead time in days (optional, default 7).

    If any required field is missing the tool returns a schema hint so the user
    knows exactly what to supply.

    Args:
        code:          Unique item code (e.g. 'ITM031').
        description:   Item name / description.
        category:      Inventory category.
        uom:           Unit of measure.
        quantity:      Opening stock quantity.
        standard_cost: Cost per unit (INR).
        lead_time:     Procurement lead time in days.
    """
    # Guard: surface schema if critical fields are empty
    missing = [f for f, v in [("code", code), ("description", description),
                               ("category", category), ("uom", uom)] if not v]
    if missing or quantity is None:
        return (
            "Cannot insert — the following required fields are missing or empty:\n"
            f"  Missing: {', '.join(missing) if missing else 'quantity'}\n\n"
            "Please provide all required fields:\n"
            "  code          : str   — unique item code, e.g. 'ITM031'\n"
            "  description   : str   — item name, e.g. 'USB-C Cable 1m'\n"
            "  category      : str   — e.g. 'Cables', 'Electronics', 'Cooling'\n"
            "  uom           : str   — 'pcs', 'kg', 'm', 'litre', 'set'\n"
            "  quantity      : int   — opening stock count, e.g. 50\n"
            "  standard_cost : float — cost per unit in INR (optional, default 0)\n"
            "  lead_time     : int   — procurement days (optional, default 7)\n\n"
            "Example: 'add new item ITM031 USB-C Cable category Cables uom pcs qty 100 cost 120 lead 5'"
        )

    code = code.strip().upper()

    try:
        with _engine.begin() as conn:
            existing = _rows(conn, "SELECT code FROM items WHERE code = :code", code=code)
            if existing:
                return (
                    f"Item '{code}' already exists. "
                    f"Use update_inventory to adjust its stock quantity, or choose a different code."
                )

            conn.execute(text(
                "INSERT INTO items "
                "(code, description, category, uom, quantity, quantity_in_use, standard_cost, lead_time) "
                "VALUES (:code, :desc, :cat, :uom, :qty, 0, :cost, :lt)"
            ), {
                "code": code,
                "desc": description.strip(),
                "cat":  category.strip(),
                "uom":  uom.strip(),
                "qty":  int(quantity),
                "cost": float(standard_cost),
                "lt":   int(lead_time),
            })

        msg = (
            f"New inventory item created successfully!\n"
            f"  Code        : {code}\n"
            f"  Description : {description}\n"
            f"  Category    : {category}\n"
            f"  UOM         : {uom}\n"
            f"  Stock       : {quantity}\n"
            f"  Cost/unit   : ₹{standard_cost:.2f}\n"
            f"  Lead time   : {lead_time} day(s)"
        )
        logger.info("insert_inventory: created %s — %s (qty %s)", code, description, quantity)
        return msg
    except SQLAlchemyError as exc:
        logger.error("insert_inventory error: %s", exc)
        return f"DATABASE ERROR: {exc}"


# ---------------------------------------------------------------------------
# Tool — update_inventory
# ---------------------------------------------------------------------------
@tool
def update_inventory(item_code: str, quantity_change: int, reason: str = "") -> str:
    """
    Adjusts the stock quantity for an inventory item.
    Use positive quantity_change to add stock, negative to subtract.

    Args:
        item_code:       Inventory item code.
        quantity_change: Amount to add (positive) or remove (negative).
        reason:          Optional reason for the adjustment.
    """
    try:
        with _engine.begin() as conn:
            rows = _rows(conn,
                "SELECT quantity, quantity_in_use FROM items WHERE code = :code",
                code=item_code)
            if not rows:
                return f"No inventory item found with code '{item_code}'."

            current = rows[0]["quantity"]
            new_qty = current + quantity_change
            if new_qty < 0:
                return (f"Cannot reduce quantity below 0. "
                        f"Current stock: {current}, change requested: {quantity_change}.")

            conn.execute(text(
                "UPDATE items SET quantity = :qty WHERE code = :code"),
                {"qty": new_qty, "code": item_code})

        msg = f"Inventory updated for '{item_code}': {current} → {new_qty}."
        if reason:
            msg += f" Reason: {reason}."
        logger.info(msg)
        return msg
    except SQLAlchemyError as exc:
        logger.error("update_inventory error: %s", exc)
        return f"DATABASE ERROR: {exc}"


# ---------------------------------------------------------------------------
# Tool 3 — delete_inventory
# ---------------------------------------------------------------------------
@tool
def delete_inventory(item_code: str, reason: str = "") -> str:
    """
    Permanently removes an inventory item from the system.
    Will fail if the item is referenced by any BOM.

    Args:
        item_code: Exact item code to delete (e.g. 'ITM011').
        reason:    Optional reason for deletion.
    """
    try:
        with _engine.begin() as conn:
            rows = _rows(conn, "SELECT code, description FROM items WHERE code = :code", code=item_code)
            if not rows:
                return f"No inventory item found with code '{item_code}'."

            # Check if any BOM references this item
            refs = _rows(conn, "SELECT bom_id FROM bom_items WHERE item_code = :code", code=item_code)
            if refs:
                return (f"Cannot delete '{item_code}' — it is used in {len(refs)} BOM(s). "
                        f"Remove it from those BOMs first.")

            conn.execute(text("DELETE FROM items WHERE code = :code"), {"code": item_code})

        msg = f"Inventory item '{item_code}' ({rows[0]['description']}) deleted successfully."
        if reason:
            msg += f" Reason: {reason}."
        logger.info(msg)
        return msg
    except SQLAlchemyError as exc:
        logger.error("delete_inventory error: %s", exc)
        return f"DATABASE ERROR: {exc}"


# ---------------------------------------------------------------------------
# Tool 4 — create_bom
# ---------------------------------------------------------------------------
@tool
def create_bom(
    name: str,
    description: str,
    output_quantity: int,
    lead_time_days: int,
    items_json: str,
) -> str:
    """
    Creates a new Bill of Materials with its component items.

    Args:
        name:            Unique BOM name (e.g. 'BOM-CONTROLLER-V1').
        description:     What this BOM produces.
        output_quantity: How many units this BOM produces per run.
        lead_time_days:  Expected days to produce.
        items_json:      JSON array of components, e.g.:
                         '[{"item_code": "MCU-32F103", "qty_required": 2}]'
    """
    try:
        items: list[dict] = json.loads(items_json)
    except json.JSONDecodeError:
        return "ERROR: items_json must be a valid JSON array."

    try:
        with _engine.begin() as conn:
            # Check BOM doesn't already exist
            existing = _rows(conn, "SELECT id FROM bom WHERE name = :name", name=name)
            if existing:
                return f"BOM '{name}' already exists. Use update_bom to modify it."

            # Validate all item codes exist
            for item in items:
                code = item.get("item_code", "")
                found = _rows(conn, "SELECT code FROM items WHERE code = :code", code=code)
                if not found:
                    return f"ERROR: Item code '{code}' not found in inventory."

            # Insert BOM header
            conn.execute(text(
                "INSERT INTO bom (name, description, output_quantity, lead_time_days) "
                "VALUES (:name, :desc, :oqty, :lt)"),
                {"name": name, "desc": description, "oqty": output_quantity, "lt": lead_time_days})

            bom_row = _rows(conn, "SELECT id FROM bom WHERE name = :name", name=name)
            bom_id = bom_row[0]["id"]

            # Insert BOM items
            for item in items:
                conn.execute(text(
                    "INSERT INTO bom_items (bom_id, item_code, qty_required) "
                    "VALUES (:bom_id, :code, :qty)"),
                    {"bom_id": bom_id, "code": item["item_code"], "qty": item["qty_required"]})

        logger.info("Created BOM '%s' with %d items.", name, len(items))
        return f"BOM '{name}' created successfully with {len(items)} component(s)."
    except SQLAlchemyError as exc:
        logger.error("create_bom error: %s", exc)
        return f"DATABASE ERROR: {exc}"


# ---------------------------------------------------------------------------
# Tool 4 — get_bom
# ---------------------------------------------------------------------------
@tool
def get_bom(bom_name: str) -> str:
    """
    Returns a BOM's details along with each component's current stock status
    (quantity on hand, quantity in use, available quantity).

    Args:
        bom_name: Name of the BOM to fetch.
    """
    try:
        with _engine.connect() as conn:
            bom_rows = _rows(conn,
                "SELECT * FROM bom WHERE name = :name", name=bom_name)
            if not bom_rows:
                return f"No BOM found with name '{bom_name}'."

            bom = bom_rows[0]
            items = _rows(conn, """
                SELECT bi.item_code, bi.qty_required,
                       i.description, i.uom,
                       i.quantity, i.quantity_in_use,
                       (i.quantity - i.quantity_in_use) AS available
                FROM bom_items bi
                JOIN items i ON i.code = bi.item_code
                WHERE bi.bom_id = :bom_id
            """, bom_id=bom["id"])

        return json.dumps({"bom": bom, "components": items}, default=str)
    except SQLAlchemyError as exc:
        logger.error("get_bom error: %s", exc)
        return f"DATABASE ERROR: {exc}"


# ---------------------------------------------------------------------------
# Tool 5 — update_bom
# ---------------------------------------------------------------------------
@tool
def update_bom(bom_name: str, field: str, value: str) -> str:
    """
    Updates a single field on an existing BOM header.
    Allowed fields: description, output_quantity, lead_time_days.

    Args:
        bom_name: Name of the BOM to update.
        field:    Field to update (description | output_quantity | lead_time_days).
        value:    New value as a string.
    """
    allowed = {"description", "output_quantity", "lead_time_days"}
    if field not in allowed:
        return f"ERROR: '{field}' is not updatable. Choose from: {', '.join(allowed)}."

    try:
        with _engine.begin() as conn:
            rows = _rows(conn, "SELECT id FROM bom WHERE name = :name", name=bom_name)
            if not rows:
                return f"No BOM found with name '{bom_name}'."
            conn.execute(
                text(f"UPDATE bom SET `{field}` = :val WHERE name = :name"),
                {"val": value, "name": bom_name})

        return f"BOM '{bom_name}' updated: {field} = '{value}'."
    except SQLAlchemyError as exc:
        logger.error("update_bom error: %s", exc)
        return f"DATABASE ERROR: {exc}"


# ---------------------------------------------------------------------------
# Tool 6 — delete_bom
# ---------------------------------------------------------------------------
@tool
def delete_bom(bom_name: str) -> str:
    """
    Deletes a BOM and all its component lines.

    Args:
        bom_name: Name of the BOM to delete.
    """
    try:
        with _engine.begin() as conn:
            rows = _rows(conn, "SELECT id FROM bom WHERE name = :name", name=bom_name)
            if not rows:
                return f"No BOM found with name '{bom_name}'."
            conn.execute(text("DELETE FROM bom WHERE name = :name"), {"name": bom_name})

        logger.info("Deleted BOM '%s'.", bom_name)
        return f"BOM '{bom_name}' deleted successfully."
    except SQLAlchemyError as exc:
        logger.error("delete_bom error: %s", exc)
        return f"DATABASE ERROR: {exc}"


# ---------------------------------------------------------------------------
# Tool 7 — run_bom
# ---------------------------------------------------------------------------
@tool
def run_bom(bom_name: str, quantity: int) -> str:
    """
    Executes a BOM run for the given quantity.

    - If all required inventory is available: blocks (marks in_use) the exact
      quantities needed and returns a success confirmation.
    - If any item is short: returns a structured shortage list WITHOUT modifying
      inventory. The calling system will offer to send a vendor order email.

    Args:
        bom_name: Name of the BOM to run.
        quantity: Number of BOM output units to produce.
    """
    try:
        with _engine.connect() as conn:
            bom_rows = _rows(conn, "SELECT * FROM bom WHERE name = :name", name=bom_name)
            if not bom_rows:
                return json.dumps({"status": "error", "message": f"BOM '{bom_name}' not found."})

            bom = bom_rows[0]
            items = _rows(conn, """
                SELECT bi.item_code, bi.qty_required,
                       i.description, i.uom,
                       i.quantity, i.quantity_in_use,
                       (i.quantity - i.quantity_in_use) AS available
                FROM bom_items bi
                JOIN items i ON i.code = bi.item_code
                WHERE bi.bom_id = :bom_id
            """, bom_id=bom["id"])

        shortages = []
        to_block: list[dict[str, Any]] = []

        for item in items:
            needed = item["qty_required"] * quantity
            available = int(item["available"])
            if available < needed:
                shortages.append({
                    "item_code":   item["item_code"],
                    "description": item["description"],
                    "uom":         item["uom"],
                    "required":    needed,
                    "available":   available,
                    "shortage":    needed - available,
                })
            else:
                to_block.append({"item_code": item["item_code"], "block_qty": needed})

        if shortages:
            result = {
                "status": "shortage",
                "bom_name": bom_name,
                "quantity": quantity,
                "lead_time_days": bom["lead_time_days"],
                "shortages": shortages,
                "message": (
                    f"Cannot run BOM '{bom_name}' × {quantity}. "
                    f"{len(shortages)} item(s) are short. "
                    f"Order from vendor to proceed."
                ),
            }
            logger.warning("BOM '%s' × %d has shortages: %s", bom_name, quantity, shortages)
            return json.dumps(result, default=str)

        # All available — block inventory
        with _engine.begin() as conn:
            for b in to_block:
                conn.execute(text(
                    "UPDATE items SET quantity_in_use = quantity_in_use + :qty "
                    "WHERE code = :code"),
                    {"qty": b["block_qty"], "code": b["item_code"]})

        blocked_summary = [f"{b['item_code']} × {b['block_qty']}" for b in to_block]
        result = {
            "status": "success",
            "bom_name": bom_name,
            "quantity": quantity,
            "lead_time_days": bom["lead_time_days"],
            "blocked": to_block,
            "message": (
                f"BOM '{bom_name}' × {quantity} is running. "
                f"Inventory blocked: {', '.join(blocked_summary)}. "
                f"Expected lead time: {bom['lead_time_days']} days."
            ),
        }
        logger.info("BOM '%s' × %d started. Blocked: %s", bom_name, quantity, blocked_summary)
        return json.dumps(result, default=str)

    except SQLAlchemyError as exc:
        logger.error("run_bom error: %s", exc)
        return json.dumps({"status": "error", "message": f"DATABASE ERROR: {exc}"})


# ---------------------------------------------------------------------------
# Tool 8 — check_bom_buildability
# ---------------------------------------------------------------------------
@tool
def check_bom_buildability(bom_name: str, quantity: int) -> str:
    """
    Read-only check: can we fulfil <quantity> units of <bom_name>?
    Does NOT block any inventory.

    Step 1 — Check if <bom_name> exists as a finished good in inventory with
              enough available stock. If yes, report immediately (no component
              check needed).
    Step 2 — If not in stock as a finished good, look up the BOM definition
              and check whether all required components are available.
              Returns buildable + lead time, or a shortage list.

    Args:
        bom_name: Name of the BOM (also checked as an inventory item code).
        quantity: Number of output units needed.
    """
    try:
        with _engine.connect() as conn:
            # ── Step 1: check finished-good stock ──────────────────────────
            finished = _rows(conn,
                "SELECT code, description, quantity, quantity_in_use, "
                "(quantity - quantity_in_use) AS available "
                "FROM items WHERE code = :code",
                code=bom_name)

            if finished:
                avail = int(finished[0]["available"])
                if avail >= quantity:
                    return json.dumps({
                        "status": "in_stock",
                        "bom_name": bom_name,
                        "quantity": quantity,
                        "message": (
                            f"'{bom_name}' is available as a finished good in inventory. "
                            f"Available: {avail} unit(s) — requested {quantity}. "
                            f"No production needed."
                        ),
                    })
                # Finished good exists but not enough — fall through to component check

            # ── Step 2: component-level BOM check ──────────────────────────
            bom_rows = _rows(conn, "SELECT * FROM bom WHERE name = :name", name=bom_name)
            if not bom_rows:
                return json.dumps({"status": "error", "message": f"BOM '{bom_name}' not found in inventory or BOM definitions."})

            bom = bom_rows[0]
            items = _rows(conn, """
                SELECT bi.item_code, bi.qty_required,
                       i.description, i.uom, i.lead_time,
                       i.quantity, i.quantity_in_use,
                       (i.quantity - i.quantity_in_use) AS available
                FROM bom_items bi
                JOIN items i ON i.code = bi.item_code
                WHERE bi.bom_id = :bom_id
            """, bom_id=bom["id"])

        shortages = []
        sufficient = []

        for item in items:
            needed = item["qty_required"] * quantity
            available = int(item["available"])
            if available < needed:
                shortages.append({
                    "item_code":   item["item_code"],
                    "description": item["description"],
                    "uom":         item["uom"],
                    "required":    needed,
                    "available":   available,
                    "shortage":    needed - available,
                    "item_lead_time_days": item["lead_time"],
                })
            else:
                sufficient.append(item["item_code"])

        sufficient_names = ", ".join(sufficient) if sufficient else "none"
        weeks = round(bom["lead_time_days"] / 7, 1)

        if not shortages:
            return json.dumps({
                "status": "can_build",
                "bom_name": bom_name,
                "quantity": quantity,
                "lead_time_days": bom["lead_time_days"],
                "components_available": sufficient,
                "message": (
                    f"All components for '{bom_name}' × {quantity} are present in inventory: "
                    f"{sufficient_names}. "
                    f"'{bom_name}' can be built in approximately {weeks} week(s) "
                    f"({bom['lead_time_days']} days)."
                ),
            }, default=str)

        max_procurement = max(s["item_lead_time_days"] for s in shortages)
        total_days = bom["lead_time_days"] + max_procurement
        total_weeks = round(total_days / 7, 1)
        short_names = ", ".join(s["item_code"] for s in shortages)
        return json.dumps({
            "status": "shortage",
            "bom_name": bom_name,
            "quantity": quantity,
            "shortages": shortages,
            "lead_time_days": bom["lead_time_days"],
            "message": (
                f"'{bom_name}' × {quantity} cannot be built yet. "
                f"Components {short_names} are short. "
                f"If ordered now, '{bom_name}' can be built in approximately "
                f"{total_weeks} week(s) ({total_days} days total including procurement)."
            ),
        }, default=str)

    except SQLAlchemyError as exc:
        logger.error("check_bom_buildability error: %s", exc)
        return json.dumps({"status": "error", "message": f"DATABASE ERROR: {exc}"})
