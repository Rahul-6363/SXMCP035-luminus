# End-to-End Gap Analysis
**Project:** ERP Assistant — Inventory & BOM Management  
**Date:** 2026-04-08  
**Services:** `backend/` (FastAPI) · `frontend/` (React/Vite) · `erp_mail_system/` (Node/Nodemailer)

---

## Legend
| Symbol | Meaning |
|--------|---------|
| ✅ | Working / connected |
| ❌ | Broken / missing |
| ⚠️ | Partial / needs fix |

---

## 1. Backend → Database

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1.1 | MySQL connection pool | ✅ | SQLAlchemy engine in `mcp_tools.py` |
| 1.2 | `inventory` table | ✅ | Schema created in `schema.sql` |
| 1.3 | `bom` table | ✅ | Schema created in `schema.sql` |
| 1.4 | `bom_items` table | ✅ | Schema created in `schema.sql` |
| 1.5 | `GET /api/items` returns live rows | ✅ | Reads from `inventory` table |
| 1.6 | `GET /api/bom` returns live rows | ✅ | Reads from `bom` table |
| 1.7 | `POST /chat` runs agent + tools | ✅ | LangGraph ReAct with 8 domain tools |
| 1.8 | `available` column in `/api/items` | ✅ | Computed as `quantity - quantity_in_use` |
| 1.9 | `quantity_in_use` updated by `run_bom` | ✅ | Blocked on successful BOM run |
| 1.10 | Config loads from `.env` | ✅ | pydantic-settings |
| 1.11 | `SCHEMA_PATH` still in config.py | ❌ | Leftover field — `schema.sql` is now init-only. Remove from `config.py` to avoid confusion |

---

## 2. Frontend → Backend (Data Layer)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 2.1 | `BACKEND_URL` points to port 8000 | ✅ | Fixed in `constants.js` |
| 2.2 | `useInventory` fetches `/api/items` | ✅ | Falls back to empty array on error |
| 2.3 | Mock data removed | ✅ | `mockInventoryData = []` |
| 2.4 | `InventoryTable` shows `quantity` column | ⚠️ | Shows raw `quantity` — backend now returns `quantity_in_use` and `available` too. Table should show **available** qty and a separate "In Use" badge so users can see blocked stock |
| 2.5 | `KPICards` "Critical Stock" threshold | ⚠️ | Uses `quantity < 10` — should use `available < 10` (blocked stock should not count as safe) |
| 2.6 | `KPICards` "Inventory Valuation" | ⚠️ | Uses `quantity * cost` — should use `available * cost` for true liquid value |
| 2.7 | `KPICards` "System Health" | ❌ | Hardcoded `100%` — never actually calls `GET /health`. Should ping the backend and show real status |
| 2.8 | `Charts` use `quantity` not `available` | ⚠️ | Doughnut + Bar use raw `quantity`. Should reflect available stock so charts aren't misleading after BOM runs |
| 2.9 | `ItemModal` missing `quantity_in_use` / `available` | ❌ | Modal only shows `quantity`. After a BOM run, user has no visibility into how much is blocked vs free |
| 2.10 | **No BOM section in frontend** | ❌ | `Navbar` has Home + Inventory only. No BOM page exists. `GET /api/bom` endpoint exists but nothing calls it |
| 2.11 | **No BOM nav link** | ❌ | `Navbar.jsx` missing "BOM" button and `App.jsx` has no BOM section route |
| 2.12 | Auto-refresh after chat action | ❌ | When the agent updates inventory via `/chat` (e.g. `run_bom`, `update_inventory`), the `InventoryTable` does not re-fetch. User sees stale data until manual refresh |
| 2.13 | `HomeSection` "Database Connection" | ❌ | Hardcoded text "Ready" — not actually verified. Should call `/health` on mount |

---

## 3. Frontend → Agent (Chat Layer)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 3.1 | `AssistantBar` sends text to `POST /chat` | ✅ | Wired up |
| 3.2 | Response displayed below input | ✅ | Response bubble renders |
| 3.3 | Shortage table rendered on shortage | ✅ | Shows item_code, required, available, shortage |
| 3.4 | "Send order email" button on shortage | ✅ | Calls `POST /send-vendor-email` |
| 3.5 | Loading spinner while waiting | ✅ | fa-spinner shown |
| 3.6 | Enter key submits | ✅ | `onKeyDown` handler |
| 3.7 | `VENDOR_EMAIL` hardcoded in component | ⚠️ | `saurav06sept@gmail.com` hardcoded in `AssistantBar.jsx`. Should come from a config or be user-editable |
| 3.8 | No conversation history in UI | ❌ | Each response replaces previous one. No chat thread — user can't scroll through past Q&A |
| 3.9 | Agent has no memory between requests | ❌ | Each `/chat` call is stateless. Follow-up questions like "what about last month?" fail. LangGraph `MemorySaver` needed |
| 3.10 | Error detail shown to user | ⚠️ | On backend 500, `data.detail` (internal exception) is shown to user. Should show a generic message |

---

## 4. Frontend → Mailer

| # | Item | Status | Detail |
|---|------|--------|--------|
| 4.1 | `POST /send-vendor-email` endpoint exists | ✅ | In `erp_mail_system/server.js` |
| 4.2 | CORS enabled on mailer | ✅ | `cors` middleware added |
| 4.3 | Frontend calls mailer on "Yes" click | ✅ | Calls `MAILER_URL/send-vendor-email` |
| 4.4 | `MAILER_URL` constant defined | ✅ | `http://localhost:3000` in `constants.js` |
| 4.5 | Mailer formats shortage email correctly | ✅ | Lists all short items with quantities |
| 4.6 | No confirmation after email sent | ⚠️ | UI appends text to response bubble — works but looks rough. A toast notification would be cleaner |
| 4.7 | Mailer not integrated with agent flow | ⚠️ | Email is triggered only from the web frontend. Discord bot shortages won't trigger email — needs separate handler there |

---

## 5. Discord Bot

| # | Item | Status | Detail |
|---|------|--------|--------|
| 5.1 | `bot.py` exists | ✅ | File present |
| 5.2 | Bot calls FastAPI backend | ❌ | Currently echoes raw message back — never calls `run_agent` or `POST /chat` |
| 5.3 | Bot returns agent answer to Discord | ❌ | Not implemented |
| 5.4 | Shortage flow on Discord | ❌ | When agent detects shortages via Discord, bot has no way to prompt "order from vendor?" and trigger email |

---

## 6. Missing Features (from `read.txt` spec)

| # | Feature | Status |
|---|---------|--------|
| 6.1 | BOM section in frontend UI | ❌ |
| 6.2 | `quantity_in_use` visible to user in table/modal | ❌ |
| 6.3 | Auto-refresh inventory after chat modifies it | ❌ |
| 6.4 | Conversation memory (multi-turn chat) | ❌ |
| 6.5 | Discord bot → agent → Discord response | ❌ |
| 6.6 | Discord shortage → vendor email | ❌ |
| 6.7 | Real backend health check on homepage | ❌ |
| 6.8 | Vendor email configurable (not hardcoded) | ⚠️ |

---

## Priority Fix Order

| Priority | Fix |
|----------|-----|
| **P0** | Add BOM section + nav link to frontend (`App.jsx`, `Navbar.jsx`, new `BomSection.jsx`) |
| **P0** | Auto-refresh `inventoryData` after `/chat` returns (call `refreshData` in `AssistantBar`) |
| **P0** | Wire Discord `bot.py` → `run_agent()` → reply to channel |
| **P1** | Show `available` + `quantity_in_use` in `InventoryTable` and `ItemModal` |
| **P1** | Fix `KPICards` to use `available` not `quantity` |
| **P1** | Fix `Charts` to use `available` not `quantity` |
| **P1** | Add conversation history UI (chat thread in `AssistantBar`) |
| **P2** | Real `/health` check on `HomeSection` + `KPICards` |
| **P2** | Add `MemorySaver` to LangGraph agent for multi-turn memory |
| **P2** | Remove `SCHEMA_PATH` from `config.py` |
| **P3** | Replace hardcoded `VENDOR_EMAIL` with config/env var |
| **P3** | Generic error message to user instead of raw exception |
| **P3** | Toast notification for email sent instead of appended text |
