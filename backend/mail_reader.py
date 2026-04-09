"""
Mail Reader — polls Gmail IMAP for vendor shipment reply emails.

Flow:
  1. Every IMAP_POLL_INTERVAL seconds: connect to Gmail IMAP, look for
     UNSEEN emails whose subject contains "Purchase Order".
  2. Parse each email body with LLM to extract shipment items
     [{item_code, description, quantity, uom}].
  3. Insert a pending_shipments row (status='pending').
  4. Call discord_notify_fn so the bot can post an alert embed.

Approval / rejection is handled by the API endpoints in main.py.
"""

import asyncio
import email
import imaplib
import json
import logging
import re
from email.header import decode_header

from langchain_ollama import ChatOllama
from sqlalchemy import text

from config import get_settings
from mcp_tools import _engine, _rows

logger = logging.getLogger("mcp_host.mail_reader")
cfg    = get_settings()

# ── LLM parse prompt ─────────────────────────────────────────────────────────
_PARSE_PROMPT = """\
Extract shipment items from this vendor email. Output ONLY a JSON array.
Each element must have: item_code (string, e.g. "ITM022" or ""), description (string), quantity (number), uom (string, e.g. "pcs").
If you cannot find specific items, return [].

Email:
{body}

JSON array only:"""


# ── Email utilities ───────────────────────────────────────────────────────────

def _decode_str(value: str) -> str:
    parts = decode_header(value or "")
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(chunk)
    return " ".join(out)


def _body_text(msg) -> str:
    """Extract best plain-text part from an email.Message object."""
    if msg.is_multipart():
        for part in msg.walk():
            if (part.get_content_type() == "text/plain"
                    and "attachment" not in str(part.get("Content-Disposition", ""))):
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
        # fallback: first text/html stripped of tags
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                charset = part.get_content_charset() or "utf-8"
                html = part.get_payload(decode=True).decode(charset, errors="replace")
                return re.sub(r'<[^>]+>', ' ', html)
    else:
        charset = msg.get_content_charset() or "utf-8"
        return msg.get_payload(decode=True).decode(charset, errors="replace")
    return ""


# ── Item extraction ───────────────────────────────────────────────────────────

def _regex_extract(body: str) -> list[dict]:
    """Fast regex pass — picks up explicit ITMxxx codes with a quantity."""
    items = []
    # e.g. "ITM022 — CPU Processor: 5 pcs" or "ITM022 x 5"
    pattern = re.findall(
        r'\b(ITM\d{3})\b[^0-9\n]{0,60}?(\d+)\s*(?:pcs?|units?|nos?|pieces?|sets?)',
        body, re.IGNORECASE,
    )
    seen = set()
    for code, qty in pattern:
        code = code.upper()
        if code not in seen:
            seen.add(code)
            items.append({"item_code": code, "description": "", "quantity": int(qty), "uom": "pcs"})
    return items


def _llm_extract(body: str) -> list[dict]:
    """LLM fallback — parses free-form vendor prose."""
    try:
        llm = ChatOllama(
            base_url=cfg.OLLAMA_BASE_URL,
            model=cfg.OLLAMA_MODEL,
            temperature=0,
            num_ctx=1024,
            num_predict=400,
        ).bind(think=False)
        prompt = _PARSE_PROMPT.format(body=body[:2000])
        resp = llm.invoke([{"role": "user", "content": prompt}])
        raw  = resp.content.strip()
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            if isinstance(parsed, list):
                return parsed
    except Exception as exc:
        logger.warning("LLM item extraction failed: %s", exc)
    return []


def parse_shipment_items(body: str) -> list[dict]:
    items = _regex_extract(body)
    if not items:
        items = _llm_extract(body)
    # Normalise keys
    cleaned = []
    for item in items:
        cleaned.append({
            "item_code":   str(item.get("item_code", "")).strip().upper(),
            "description": str(item.get("description", "")).strip(),
            "quantity":    int(item.get("quantity", 0)),
            "uom":         str(item.get("uom", "pcs")).strip(),
        })
    return [i for i in cleaned if i["quantity"] > 0]


# ── DB helpers ────────────────────────────────────────────────────────────────

def _already_seen(uid: str) -> bool:
    with _engine.connect() as conn:
        return bool(_rows(conn,
            "SELECT id FROM pending_shipments WHERE email_uid = :uid", uid=uid))


def _insert_shipment(uid: str, sender: str, subject: str,
                     body: str, items: list[dict]) -> int:
    with _engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO pending_shipments
                (email_uid, sender, subject, received_at, raw_excerpt, parsed_items, status)
            VALUES (:uid, :sender, :subject, NOW(), :excerpt, :items, 'pending')
        """), {
            "uid":     uid,
            "sender":  sender,
            "subject": subject,
            "excerpt": body[:1200],
            "items":   json.dumps(items),
        })
        return _rows(conn, "SELECT LAST_INSERT_ID() AS id")[0]["id"]


# ── IMAP poll ─────────────────────────────────────────────────────────────────

def poll_once(discord_notify_fn=None) -> int:
    """
    Connects to IMAP, fetches unread Purchase Order reply emails,
    saves them as pending_shipments. Returns count of new shipments.
    """
    if not cfg.IMAP_USER or not cfg.IMAP_PASS:
        return 0

    new_count = 0
    try:
        mail = imaplib.IMAP4_SSL(cfg.IMAP_HOST)
        mail.login(cfg.IMAP_USER, cfg.IMAP_PASS)
        mail.select("INBOX")

        # Match both subject formats the mailer can produce.
        # No UNSEEN filter — rely on email_uid DB dedup instead,
        # because vendor replies may have been opened in Gmail already.
        _, d1 = mail.search(None, '(SUBJECT "Purchase Order")')
        _, d2 = mail.search(None, '(SUBJECT "Replenishment Order")')
        uids  = list({u for u in d1[0].split() + d2[0].split() if u})
        if not uids:
            mail.logout()
            return 0

        logger.info("Mail reader: %d unread Purchase Order email(s) found.", len(uids))

        for uid_bytes in uids:
            uid_str = uid_bytes.decode()
            if _already_seen(uid_str):
                continue

            _, msg_data = mail.fetch(uid_bytes, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subject = _decode_str(msg.get("Subject", ""))
            sender  = _decode_str(msg.get("From",    ""))
            body    = _body_text(msg)

            # Skip emails sent by our own mailer (outbound purchase orders)
            if cfg.IMAP_USER.lower() in sender.lower():
                logger.debug("Skipping outbound email from self: %s", subject)
                continue

            items = parse_shipment_items(body)
            shipment_id = _insert_shipment(uid_str, sender, subject, body, items)
            new_count += 1

            logger.info("New shipment #%d from %s — %d item(s).", shipment_id, sender, len(items))

            if discord_notify_fn:
                try:
                    discord_notify_fn(shipment_id, sender, subject, items, body[:600])
                except Exception as exc:
                    logger.warning("Discord notify failed: %s", exc)

        mail.logout()

    except imaplib.IMAP4.error as exc:
        logger.error("IMAP error: %s", exc)
    except OSError as exc:
        logger.error("IMAP connection error: %s", exc)
    except Exception as exc:
        logger.error("Mail poll unexpected error: %s", exc)

    return new_count


# ── Background async task ─────────────────────────────────────────────────────

async def start_mail_poller(discord_notify_fn=None):
    """
    Long-running async task — call from FastAPI lifespan.
    Polls IMAP every cfg.IMAP_POLL_INTERVAL seconds.
    """
    interval = cfg.IMAP_POLL_INTERVAL
    user     = cfg.IMAP_USER or "not configured"
    logger.info("Mail poller started — user: %s, interval: %ds", user, interval)

    while True:
        try:
            count = await asyncio.to_thread(poll_once, discord_notify_fn)
            if count:
                logger.info("Mail poller: %d new shipment(s) stored.", count)
        except Exception as exc:
            logger.error("Mail poller iteration error: %s", exc)
        await asyncio.sleep(interval)
