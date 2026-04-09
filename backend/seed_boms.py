"""
Seed sample BOMs using real inventory items (ITM001–ITM030).

BOMs created:
  BOM-LAPTOP-STD    — Standard Laptop Assembly (core build)
  BOM-LAPTOP-FULL   — Full Laptop Kit (with packaging + accessories)
  BOM-LAPTOP-BUDGET — Budget Laptop Build (minimal components)
  BOM-MOUSE-STD     — Standard Mouse Assembly

Run once: python seed_boms.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from mcp_tools import _engine, _rows

BOMS = [
    {
        "name":            "BOM-LAPTOP-STD",
        "description":     "Standard Laptop Assembly — core electronics and mechanical build",
        "output_quantity": 1,
        "lead_time_days":  10,
        "items": [
            # Electronics core
            ("ITM002", 1),  # Laptop Motherboard
            ("ITM003", 1),  # Laptop Battery
            ("ITM004", 1),  # Laptop Screen 15.6 inch
            ("ITM005", 1),  # Keyboard Module
            ("ITM009", 1),  # SSD 512GB
            ("ITM010", 1),  # RAM 16GB DDR4
            ("ITM011", 1),  # Cooling Fan
            ("ITM012", 1),  # Thermal Paste
            ("ITM014", 2),  # USB-C Port Module
            ("ITM015", 1),  # WiFi Card
            ("ITM016", 1),  # Bluetooth Module
            ("ITM021", 1),  # GPU Chipset
            ("ITM022", 1),  # CPU Processor
            ("ITM025", 1),  # Touchpad Module
            ("ITM026", 1),  # Camera Module
            ("ITM027", 1),  # Speakers Pair
            ("ITM028", 1),  # Microphone Unit
            ("ITM030", 1),  # HDMI Port Module
            # Mechanical
            ("ITM007", 1),  # Plastic Casing
            ("ITM008", 1),  # Aluminum Frame
            ("ITM023", 1),  # Heat Sink
            ("ITM020", 1),  # Screws Set
            ("ITM029", 4),  # Rubber Feet Set
        ],
    },
    {
        "name":            "BOM-LAPTOP-FULL",
        "description":     "Full Laptop Kit — standard build + power adapter + packaging",
        "output_quantity": 1,
        "lead_time_days":  12,
        "items": [
            ("ITM002", 1),  # Laptop Motherboard
            ("ITM003", 1),  # Laptop Battery
            ("ITM004", 1),  # Laptop Screen 15.6 inch
            ("ITM005", 1),  # Keyboard Module
            ("ITM009", 1),  # SSD 512GB
            ("ITM010", 1),  # RAM 16GB DDR4
            ("ITM011", 1),  # Cooling Fan
            ("ITM012", 1),  # Thermal Paste
            ("ITM014", 2),  # USB-C Port Module
            ("ITM015", 1),  # WiFi Card
            ("ITM016", 1),  # Bluetooth Module
            ("ITM021", 1),  # GPU Chipset
            ("ITM022", 1),  # CPU Processor
            ("ITM025", 1),  # Touchpad Module
            ("ITM026", 1),  # Camera Module
            ("ITM027", 1),  # Speakers Pair
            ("ITM028", 1),  # Microphone Unit
            ("ITM030", 1),  # HDMI Port Module
            ("ITM007", 1),  # Plastic Casing
            ("ITM008", 1),  # Aluminum Frame
            ("ITM023", 1),  # Heat Sink
            ("ITM020", 1),  # Screws Set
            ("ITM029", 4),  # Rubber Feet Set
            # Accessories + packaging
            ("ITM013", 1),  # Power Adapter 65W
            ("ITM017", 1),  # Packaging Box
            ("ITM018", 1),  # Instruction Manual
            ("ITM019", 1),  # Sticker Branding
        ],
    },
    {
        "name":            "BOM-LAPTOP-BUDGET",
        "description":     "Budget Laptop Build — reduced spec, no GPU, basic storage",
        "output_quantity": 1,
        "lead_time_days":  7,
        "items": [
            ("ITM002", 1),  # Laptop Motherboard
            ("ITM003", 1),  # Laptop Battery
            ("ITM004", 1),  # Laptop Screen 15.6 inch
            ("ITM005", 1),  # Keyboard Module
            ("ITM009", 1),  # SSD 512GB
            ("ITM010", 1),  # RAM 16GB DDR4
            ("ITM011", 1),  # Cooling Fan
            ("ITM012", 1),  # Thermal Paste
            ("ITM014", 1),  # USB-C Port Module (1 only)
            ("ITM015", 1),  # WiFi Card
            ("ITM025", 1),  # Touchpad Module
            ("ITM022", 1),  # CPU Processor
            ("ITM007", 1),  # Plastic Casing
            ("ITM023", 1),  # Heat Sink
            ("ITM020", 1),  # Screws Set
            ("ITM029", 4),  # Rubber Feet Set
            ("ITM013", 1),  # Power Adapter 65W
            ("ITM017", 1),  # Packaging Box
            ("ITM018", 1),  # Instruction Manual
        ],
    },
    {
        "name":            "BOM-MOUSE-STD",
        "description":     "Standard Mouse Assembly — optical mouse with USB receiver",
        "output_quantity": 1,
        "lead_time_days":  3,
        "items": [
            ("ITM016", 1),  # Bluetooth Module (wireless receiver)
            ("ITM007", 1),  # Plastic Casing (mouse shell)
            ("ITM020", 1),  # Screws Set
            ("ITM029", 4),  # Rubber Feet Set
            ("ITM019", 1),  # Sticker Branding
            ("ITM017", 1),  # Packaging Box
            ("ITM018", 1),  # Instruction Manual
        ],
    },
]


def seed():
    created = 0
    skipped = 0

    with _engine.begin() as conn:
        for bom in BOMS:
            # Skip if already exists
            existing = conn.execute(
                text("SELECT id FROM bom WHERE name = :name"), {"name": bom["name"]}
            ).fetchone()
            if existing:
                print(f"  SKIP  {bom['name']} (already exists)")
                skipped += 1
                continue

            # Insert header
            conn.execute(text(
                "INSERT INTO bom (name, description, output_quantity, lead_time_days) "
                "VALUES (:name, :desc, :oqty, :lt)"
            ), {"name": bom["name"], "desc": bom["description"],
                "oqty": bom["output_quantity"], "lt": bom["lead_time_days"]})

            bom_id = conn.execute(
                text("SELECT id FROM bom WHERE name = :name"), {"name": bom["name"]}
            ).scalar()

            # Insert components
            for item_code, qty in bom["items"]:
                # Verify item exists
                exists = conn.execute(
                    text("SELECT 1 FROM items WHERE code = :code"), {"code": item_code}
                ).fetchone()
                if not exists:
                    print(f"  WARN  {bom['name']}: item {item_code} not found — skipping component")
                    continue
                conn.execute(text(
                    "INSERT INTO bom_items (bom_id, item_code, qty_required) "
                    "VALUES (:bom_id, :code, :qty)"
                ), {"bom_id": bom_id, "code": item_code, "qty": qty})

            print(f"  OK    {bom['name']} — {len(bom['items'])} components")
            created += 1

    print(f"\nDone: {created} BOM(s) created, {skipped} skipped.")


if __name__ == "__main__":
    print("Seeding BOMs...")
    seed()
