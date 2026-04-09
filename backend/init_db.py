"""
Auto-initialises the database on startup.
- Adds quantity_in_use column to existing `items` table if missing.
- Creates `bom` and `bom_items` tables if they don't exist.
- Does NOT touch or seed the `items` table data.
"""

import logging
from sqlalchemy import text
from mcp_tools import _engine

logger = logging.getLogger("mcp_host.init_db")


def init_db():
    try:
        with _engine.begin() as conn:

            # Add quantity_in_use to items table if it doesn't already exist
            existing_cols = conn.execute(text(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'items' "
                "AND COLUMN_NAME = 'quantity_in_use'"
            )).fetchall()

            if not existing_cols:
                conn.execute(text(
                    "ALTER TABLE items ADD COLUMN quantity_in_use INT DEFAULT 0"
                ))
                logger.info("Added quantity_in_use column to items table.")

            # Create bom table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bom (
                    id              INT AUTO_INCREMENT PRIMARY KEY,
                    name            VARCHAR(100) UNIQUE NOT NULL,
                    description     TEXT,
                    output_quantity INT          DEFAULT 1,
                    lead_time_days  INT          DEFAULT 14,
                    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """))

            # Create bom_items table referencing items.code
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bom_items (
                    id           INT AUTO_INCREMENT PRIMARY KEY,
                    bom_id       INT         NOT NULL,
                    item_code    VARCHAR(50) NOT NULL,
                    qty_required INT         NOT NULL DEFAULT 1,
                    FOREIGN KEY (bom_id)    REFERENCES bom(id)    ON DELETE CASCADE,
                    FOREIGN KEY (item_code) REFERENCES items(code) ON DELETE RESTRICT
                )
            """))

            # Create pending_shipments table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pending_shipments (
                    id           INT AUTO_INCREMENT PRIMARY KEY,
                    email_uid    VARCHAR(200) UNIQUE NOT NULL,
                    sender       VARCHAR(255),
                    subject      VARCHAR(500),
                    received_at  DATETIME,
                    raw_excerpt  TEXT,
                    parsed_items JSON,
                    status       ENUM('pending','approved','rejected') DEFAULT 'pending',
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

        logger.info("Database ready — items, bom, bom_items, pending_shipments tables verified.")
    except Exception as exc:
        logger.error("DB init failed: %s", exc)
        raise
