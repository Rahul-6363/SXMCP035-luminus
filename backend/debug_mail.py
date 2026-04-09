"""
Run this directly to debug the mail reader:
  cd backend
  python debug_mail.py
"""

import email
import imaplib
import json
import sys
from email.header import decode_header
from dotenv import load_dotenv
import os

load_dotenv()

IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASS = os.getenv("IMAP_PASS", "")


def decode_str(value):
    parts = decode_header(value or "")
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(chunk)
    return " ".join(out)


def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if (part.get_content_type() == "text/plain"
                    and "attachment" not in str(part.get("Content-Disposition", ""))):
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
    else:
        charset = msg.get_content_charset() or "utf-8"
        return msg.get_payload(decode=True).decode(charset, errors="replace")
    return ""


print("=" * 60)
print("MAIL READER DEBUG")
print("=" * 60)

# Step 1: Check credentials
print(f"\n[1] IMAP credentials:")
print(f"    HOST : {IMAP_HOST}")
print(f"    USER : {IMAP_USER}")
print(f"    PASS : {'set (' + str(len(IMAP_PASS)) + ' chars)' if IMAP_PASS else 'NOT SET'}")

if not IMAP_USER or not IMAP_PASS:
    print("\nERROR: IMAP_USER or IMAP_PASS not set in .env")
    sys.exit(1)

# Step 2: Connect
print(f"\n[2] Connecting to {IMAP_HOST}...")
try:
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    print("    Connected OK")
except Exception as e:
    print(f"    FAILED: {e}")
    sys.exit(1)

# Step 3: Login
print(f"\n[3] Logging in as {IMAP_USER}...")
try:
    mail.login(IMAP_USER, IMAP_PASS)
    print("    Login OK")
except Exception as e:
    print(f"    FAILED: {e}")
    print("    Hint: make sure you're using a Gmail App Password, not your real password.")
    sys.exit(1)

# Step 4: Select inbox
mail.select("INBOX")
print("\n[4] Inbox selected.")

# Step 5: Count ALL unread emails
_, data = mail.search(None, "UNSEEN")
all_unseen = data[0].split()
print(f"\n[5] Total UNSEEN emails in inbox: {len(all_unseen)}")

# Step 6: Search for both subject patterns (UNSEEN)
print("\n[6] Searching UNSEEN emails with 'Purchase Order' or 'Replenishment Order' in subject...")
_, d1 = mail.search(None, '(UNSEEN SUBJECT "Purchase Order")')
_, d2 = mail.search(None, '(UNSEEN SUBJECT "Replenishment Order")')
po_unseen = list({u for u in d1[0].split() + d2[0].split() if u})
print(f"    Found: {len(po_unseen)}")

# Step 7: Search ALL (including read) for both patterns
print("\n[7] Searching ALL emails (read+unread) for both order subjects...")
_, d3 = mail.search(None, '(SUBJECT "Purchase Order")')
_, d4 = mail.search(None, '(SUBJECT "Replenishment Order")')
po_all = list({u for u in d3[0].split() + d4[0].split() if u})
print(f"    Found: {len(po_all)}")

if not po_all:
    # Step 8: List most recent 5 emails regardless of subject
    print("\n[8] Showing last 5 emails in inbox (any subject):")
    _, all_ids = mail.search(None, "ALL")
    all_list = all_ids[0].split()
    recent = all_list[-5:] if len(all_list) >= 5 else all_list
    for uid in reversed(recent):
        _, hdr = mail.fetch(uid, "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
        hdr_msg = email.message_from_bytes(hdr[0][1])
        print(f"    Subject : {decode_str(hdr_msg.get('Subject', '(none)'))}")
        print(f"    From    : {decode_str(hdr_msg.get('From', '(none)'))}")
        print(f"    Date    : {hdr_msg.get('Date', '(none)')}")
        print()
else:
    # Step 9: Show matching emails
    print(f"\n[8] Showing matching emails:")
    for uid in po_all[-5:]:
        _, msg_data = mail.fetch(uid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        subject = decode_str(msg.get("Subject", ""))
        sender  = decode_str(msg.get("From", ""))
        body    = get_body(msg)

        print(f"\n  UID     : {uid.decode()}")
        print(f"  Subject : {subject}")
        print(f"  From    : {sender}")
        print(f"  Body snippet:\n    {body[:300].strip()}")

        # Check if already in DB
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(__file__))
            from mcp_tools import _engine, _rows
            with _engine.connect() as conn:
                exists = _rows(conn,
                    "SELECT id, status FROM pending_shipments WHERE email_uid = :uid",
                    uid=uid.decode())
                if exists:
                    print(f"  DB status: already stored as shipment #{exists[0]['id']} ({exists[0]['status']})")
                else:
                    print(f"  DB status: NOT yet in pending_shipments")
        except Exception as exc:
            print(f"  DB check failed: {exc}")

        # Try parsing items
        try:
            from mail_reader import parse_shipment_items
            items = parse_shipment_items(body)
            print(f"  Parsed items: {json.dumps(items, indent=4)}")
        except Exception as exc:
            print(f"  Parse error: {exc}")

mail.logout()
print("\n" + "=" * 60)
print("Debug complete.")
print("=" * 60)
