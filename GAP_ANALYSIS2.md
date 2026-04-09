# GAP_ANALYSIS2.md — Buyer / Seller / Vendor Expansion

**Date:** 2026-04-09  
**Current state:** Inventory + BOM management with AI assistant and vendor shortage email.  
**Goal:** Introduce a full buyer (client) and seller (vendor) layer to the platform.

---

## 1. WHERE TO PLACE THEM IN THE WEBSITE

### Option A — Two new top-level nav sections (Recommended)

```
Home | Inventory | BOM | Sales | Procurement
```

| Section | Who uses it | What it shows |
|---------|-------------|---------------|
| **Sales** | Internal team / Client-facing | Buyer orders for finished goods (ITM001 = Laptop), quote generation, order status |
| **Procurement** | Internal team / Vendor-facing | Vendor list, purchase orders sent, acknowledgment status, incoming stock tracking |

**Why this works:**
- Mirrors real ERP structure (Sales = outbound, Procurement = inbound)
- Keeps Inventory and BOM as the production layer between them
- Clean mental model: `Vendor → Procurement → Inventory → BOM → Production → Sales → Client`

---

### Option B — Stakeholders tab with sub-tabs

```
Home | Inventory | BOM | Stakeholders
                              ├── Clients
                              └── Vendors
```

Simpler if you want one section, but less scalable.

---

### Option C — Embedded in existing sections

- Vendor panel inside BOM section: "Who supplies this component?"
- Buyer panel inside Inventory section: "Who ordered this product?"

Less discoverable but lower dev effort.

---

## 2. BUYER / CLIENT SIDE — Feature Ideas

### 2a. Client (Sales) Section

**New DB table: `clients`**
```sql
id, name, email, phone, company, address, created_at
```

**New DB table: `sales_orders`**
```sql
id, client_id, item_code (finished good), quantity, 
status (pending/confirmed/shipped/cancelled),
total_cost, notes, created_at
```

**UI Features:**
- Client list table (name, email, total orders, last order date)
- "New Sales Order" form — select client, select finished good item, quantity → auto-calculates cost from `standard_cost`
- Sales order status tracker (Kanban-style or table with status badges)
- "Check if buildable" — auto-triggers `check_bom_buildability` for the ordered item
- If not enough stock: "Trigger Production Run" button → `run_bom`

**MCP Tool additions:**
- `create_sales_order(client_name, item_code, quantity)`
- `get_sales_orders(status=None)` — list orders by status
- `update_sales_order_status(order_id, status)`

**Discord bot commands:**
```
@bot new order: client Acme Corp wants 3 laptops
@bot show pending sales orders
@bot confirm sales order #5
```

---

## 3. SELLER / VENDOR SIDE — Feature Ideas

### 3a. Vendor (Procurement) Section

**Current state:** Vendor email is hardcoded to one email address (`VENDOR_EMAIL` in `.env`). No tracking, no vendor records.

**New DB table: `vendors`**
```sql
id, name, email, phone, company, 
items_supplied (JSON array of item codes),
lead_time_days, reliability_score, created_at
```

**New DB table: `purchase_orders`**
```sql
id, vendor_id, item_code, quantity_ordered, 
unit_cost, total_cost, status (sent/acknowledged/received/cancelled),
expected_delivery_date, notes, created_at
```

**UI Features:**
- Vendor list table (name, email, items they supply, avg lead time)
- "Add Vendor" form — link vendor to specific item codes
- Purchase order history (what was ordered, from whom, when, current status)
- "Mark as Received" button → auto calls `update_inventory` to add stock
- Per-vendor order email instead of one hardcoded VENDOR_EMAIL
- Shortage-to-vendor smart matching: when BOM shortage occurs, auto-select the right vendor per item

**MCP Tool additions:**
- `get_vendors(item_code=None)` — list vendors, optionally filtered by item
- `create_purchase_order(vendor_id, item_code, quantity)`
- `mark_order_received(purchase_order_id)` — calls update_inventory internally

**Discord bot commands:**
```
@bot show all vendors
@bot who supplies ITM022 (CPU Processor)?
@bot mark purchase order #3 as received
@bot add vendor: TechParts Ltd, email tech@parts.com, supplies ITM022 ITM021
```

---

## 4. MAILER UPGRADE IDEAS

**Current:** One hardcoded `VENDOR_EMAIL`, sends to a single address.

**Proposed:**
- Per-item vendor routing — `mailer.js` receives `vendor_email` per shortage item from the `vendors` table
- Email to client on sales order confirmation
- Email to client when order is ready to ship

**New mailer endpoints:**
```
POST /send-vendor-email        (already exists — upgrade to use DB vendors)
POST /send-client-confirmation (new — confirm sales order to buyer)
POST /send-shipment-notice     (new — tell buyer their order shipped)
```

---

## 5. DISCORD BOT EXPANSION

New commands to add:

| Command | Action |
|---------|--------|
| `@bot show sales orders` | Lists all open sales orders |
| `@bot client [name] wants [N] [item]` | Creates a sales order |
| `@bot show vendors` | Lists all vendors |
| `@bot who supplies [item]` | Shows vendor(s) for that item |
| `@bot receive order #[id]` | Marks PO as received, updates inventory |

The bot already has the shortage → order email flow. Extend it with:
- On `check_bom_buildability` shortage: show which vendor to order from (not just generic email)
- On `mark_order_received`: trigger `update_inventory` directly

---

## 6. PRODUCTION FLOW — COMPLETE PICTURE

```
Client places order (Sales section)
        ↓
check_bom_buildability (can we make it?)
        ↓
   YES → run_bom → inventory blocked → production starts
        ↓
   NO  → shortage detected → smart vendor match → purchase_order created → email sent
        ↓
Vendor ships → mark_order_received → inventory updated
        ↓
run_bom again → production runs → sales order marked "ready to ship"
        ↓
Client notified by email
```

---

## 7. SUGGESTED BUILD ORDER

1. **Vendor table + Procurement UI** (highest value — fixes the hardcoded email problem)
2. **Purchase order tracking** (close the loop on the existing shortage email flow)
3. **Client table + Sales UI** (new outbound flow)
4. **Sales order management** (status tracking, auto BOM check)
5. **Smart vendor routing in mailer** (per-item vendor emails)
6. **Discord bot commands** for all of the above

---

## 8. TECHNICAL GAPS (Non-buyer/seller)

| Gap | Impact | Fix |
|-----|--------|-----|
| Streaming not truly token-by-token | UX feels laggy | Use `_llm.astream()` for response generation (2nd LLM call) |
| Manual refresh after DB changes | Poor UX | Auto-poll `/api/items` every 8s + immediate refresh after chat action |
| No purchase order history | Shortages are lost after email | `purchase_orders` table stores every PO |
| Vendor email hardcoded | Can't route per-item | `vendors` table + per-item routing |
| No sales order concept | Can't track client demand | `sales_orders` table |
