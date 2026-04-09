"""
Discord ERP Bot — mention-triggered assistant.

Commands (after mentioning the bot):
  <any question>    — natural language → ERP agent → reply
  order             — confirm sending vendor email for pending shortages
  order cancel      — cancel the pending vendor order
  help              — show usage

Flow for shortages:
  1. User asks "run BOM-LAPTOP-STD" → agent detects shortage
  2. Bot lists short items and stores them as pending
  3. User types "order" in same channel → vendor email sent via mailer service
"""

import asyncio
import os
import re as _re

import discord
import requests
from dotenv import load_dotenv

from agent import run_agent

load_dotenv()

DISCORD_TOKEN             = os.getenv("DISCORD_TOKEN")
MAILER_URL                = os.getenv("MAILER_URL",    "http://localhost:3001")
VENDOR_EMAIL              = os.getenv("VENDOR_EMAIL",  "vendor@example.com")
BACKEND_URL               = os.getenv("BACKEND_URL",   "http://localhost:8000")
NOTIFY_CHANNEL_ID         = int(os.getenv("DISCORD_NOTIFY_CHANNEL_ID", "0"))

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set in .env")

intents = discord.Intents.default()
intents.message_content = True
client  = discord.Client(intents=intents)

# { channel_id: {"shortages": [...], "bom_name": "..."} }
_pending: dict[int, dict] = {}

# IDs of shipments already notified — avoids duplicate Discord messages
_notified_shipments: set[int] = set()


# ── helpers ──────────────────────────────────────────────────────────────────

def _chunk(text: str, size: int = 1900) -> list[str]:
    """Split text into Discord-safe chunks."""
    return [text[i:i+size] for i in range(0, max(len(text), 1), size)]


def _shipment_embed(shipment_id: int, sender: str, subject: str,
                    items: list[dict]) -> discord.Embed:
    embed = discord.Embed(
        title       = f"📦 Incoming Shipment #{shipment_id}",
        description = (
            f"A vendor reply has been received and parsed.\n"
            f"**From:** {sender}\n"
            f"**Subject:** {subject}"
        ),
        color = discord.Color.gold(),
    )
    if items:
        for item in items[:10]:
            embed.add_field(
                name   = f"`{item.get('item_code') or '?'}` — {item.get('description') or 'Unknown item'}",
                value  = f"Qty: **{item.get('quantity', '?')} {item.get('uom', 'pcs')}**",
                inline = True,
            )
    else:
        embed.add_field(name="⚠ No items parsed",
                        value="Check the raw email — items couldn't be extracted automatically.",
                        inline=False)
    embed.set_footer(text=f"Reply  accept #{shipment_id}  or  reject #{shipment_id}  to action this shipment.")
    return embed


def _shortage_embed(shortages: list[dict], bom_name: str) -> discord.Embed:
    embed = discord.Embed(
        title       = f"⚠️ Stock Shortage — {bom_name or 'BOM Run'}",
        description = "The following items are insufficient to fulfil this production run.",
        color       = discord.Color.orange(),
    )
    for s in shortages:
        embed.add_field(
            name   = f"`{s['item_code']}` — {s['description']}",
            value  = (
                f"Required: **{s['required']} {s['uom']}**  •  "
                f"In Stock: {s['available']}  •  "
                f"Short by: **{s['shortage']} {s['uom']}**"
            ),
            inline = False,
        )
    embed.set_footer(text="Reply `order` to email the vendor · `order cancel` to dismiss")
    return embed


# ── events ───────────────────────────────────────────────────────────────────

async def _shipment_poller():
    """Background task — polls /api/shipments every 30s, posts new pending ones to Discord."""
    await client.wait_until_ready()

    if not NOTIFY_CHANNEL_ID:
        print("[bot] DISCORD_NOTIFY_CHANNEL_ID not set — shipment alerts disabled.")
        return

    # fetch_channel makes an API call — works even before the channel is cached
    try:
        channel = await client.fetch_channel(NOTIFY_CHANNEL_ID)
    except Exception as exc:
        print(f"[bot] Cannot find channel {NOTIFY_CHANNEL_ID}: {exc}")
        return

    print(f"[bot] Shipment poller active → #{channel.name}")
    while not client.is_closed():
        try:
            res = await asyncio.get_event_loop().run_in_executor(
                None, lambda: requests.get(
                    f"{BACKEND_URL}/api/shipments?status=pending", timeout=10))
            if res.ok:
                for s in res.json():
                    sid = s["id"]
                    if sid not in _notified_shipments:
                        _notified_shipments.add(sid)
                        items = s.get("parsed_items") or []
                        await channel.send(embed=_shipment_embed(
                            sid, s.get("sender", ""), s.get("subject", ""), items))
        except Exception as exc:
            print(f"[bot] Shipment poller error: {exc}")
        await asyncio.sleep(30)


@client.event
async def on_ready():
    print(f"[bot] Logged in as {client.user}  |  Servers: {len(client.guilds)}")
    print("[bot] Available text channels:")
    for guild in client.guilds:
        print(f"  Server: {guild.name}")
        for ch in guild.text_channels:
            print(f"    #{ch.name}  →  ID: {ch.id}")
    client.loop.create_task(_shipment_poller())


# Matches: "accept #5", "accept#5", "accept 5", "reject #3" etc.
_SHIP_RE = _re.compile(r'^(accept|reject)\s*#?\s*(\d+)$', _re.IGNORECASE)


async def _handle_shipment_action(text: str, channel) -> bool:
    """
    If text matches accept/reject pattern, execute and reply.
    Returns True if handled, False otherwise.
    """
    m = _SHIP_RE.match(text.strip())
    if not m:
        return False

    action   = m.group(1).lower()           # "accept" or "reject"
    ship_id  = int(m.group(2))
    endpoint = "approve" if action == "accept" else "reject"

    async with channel.typing():
        try:
            res  = requests.post(
                f"{BACKEND_URL}/api/shipments/{ship_id}/{endpoint}", timeout=15)
            data = res.json()
            if res.ok:
                if action == "accept":
                    updated   = data.get("items_updated", [])
                    skipped   = data.get("items_skipped", [])
                    summary   = "\n".join(
                        f"  • `{i['item_code']}` +{i['quantity_added']} units"
                        for i in updated
                    ) or "  (no inventory rows updated)"
                    skip_note = (f"\n⚠ {len(skipped)} item(s) skipped (code not in inventory)."
                                 if skipped else "")
                    await channel.send(
                        f"✅ **Shipment #{ship_id} approved!**\n"
                        f"Inventory updated:\n{summary}{skip_note}"
                    )
                else:
                    await channel.send(
                        f"🗑️ **Shipment #{ship_id} rejected.** Inventory unchanged.")
            else:
                await channel.send(
                    f"❌ {data.get('detail', data.get('error', 'Unknown error'))}")
        except requests.exceptions.ConnectionError:
            await channel.send(
                f"❌ Cannot reach backend at `{BACKEND_URL}`. Is it running?")
        except Exception as exc:
            await channel.send(f"❌ Error: {exc}")
    return True


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    channel_id = message.channel.id
    raw        = message.content.strip()
    lower      = raw.lower()

    # ── accept/reject shipment (standalone — no @mention needed) ────────────
    if await _handle_shipment_action(raw, message.channel):
        return

    # ── "order cancel" ──────────────────────────────────────────────────────
    if lower == "order cancel":
        if channel_id in _pending:
            _pending.pop(channel_id)
            await message.channel.send("🗑️ Pending vendor order cancelled.")
        else:
            await message.channel.send("Nothing to cancel — no pending order in this channel.")
        return

    # ── "order" confirmation ─────────────────────────────────────────────────
    if lower == "order" and channel_id in _pending:
        pending   = _pending.pop(channel_id)
        shortages = pending["shortages"]
        bom_name  = pending.get("bom_name", "")

        async with message.channel.typing():
            try:
                res  = requests.post(
                    f"{MAILER_URL}/send-vendor-email",
                    json    = {"shortages": shortages, "vendor_email": VENDOR_EMAIL, "bom_name": bom_name},
                    timeout = 15,
                )
                data = res.json()
                if res.ok:
                    await message.channel.send(
                        f"✅ **Order email sent** to `{VENDOR_EMAIL}` "
                        f"for **{len(shortages)}** item(s)."
                        + (f"\n> Production plan: **{bom_name}**" if bom_name else "")
                    )
                else:
                    await message.channel.send(f"❌ Mailer error: {data.get('error', 'Unknown error')}")
            except requests.exceptions.ConnectionError:
                await message.channel.send(
                    f"❌ Cannot reach mailer service at `{MAILER_URL}`. "
                    "Run `cd erp_mail_system && node server.js`."
                )
            except Exception as exc:
                await message.channel.send(f"❌ Failed to send email: {exc}")
        return

    # ── Only respond to direct @mentions ─────────────────────────────────────
    if client.user not in message.mentions:
        return

    # Strip the mention to get the actual query
    user_text = (
        raw
        .replace(f"<@{client.user.id}>",  "")
        .replace(f"<@!{client.user.id}>", "")
        .strip()
    )

    if not user_text or user_text.lower() in ("help", "?"):
        help_embed = discord.Embed(
            title       = "ERP Bot — Help",
            description = "I'm connected to your live ERP inventory and BOM system.",
            color       = discord.Color.blurple(),
        )
        help_embed.add_field(name="Check inventory",      value="`@bot show all inventory`",              inline=False)
        help_embed.add_field(name="Search items",         value="`@bot search for cooling fan`",           inline=False)
        help_embed.add_field(name="Restock item",         value="`@bot add 50 units to ITM011`",           inline=False)
        help_embed.add_field(name="View BOM",             value="`@bot show BOM-LAPTOP-STD`",              inline=False)
        help_embed.add_field(name="Run BOM",              value="`@bot run BOM-LAPTOP-STD qty 2`",         inline=False)
        help_embed.add_field(name="Buildability check",   value="`@bot can I build BOM-LAPTOP-STD × 5`",  inline=False)
        help_embed.add_field(name="Confirm vendor order",   value="`order`  (after a shortage is detected)", inline=False)
        help_embed.add_field(name="Cancel vendor order",   value="`order cancel`",                          inline=False)
        help_embed.add_field(name="Approve shipment",      value="`accept #5`  (updates inventory)",         inline=False)
        help_embed.add_field(name="Reject shipment",       value="`reject #5`  (dismisses without update)",  inline=False)
        await message.channel.send(embed=help_embed)
        return

    # ── accept/reject via @mention (e.g. "@bot accept #5") ──────────────────
    if await _handle_shipment_action(user_text, message.channel):
        return

    # Show typing indicator while agent runs
    async with message.channel.typing():
        try:
            answer, shortages = await asyncio.get_event_loop().run_in_executor(
                None, lambda: run_agent(user_text, session_id=str(channel_id))
            )
        except Exception as exc:
            await message.channel.send(f"❌ Agent error: {exc}")
            return

    # Send the answer (chunked if long)
    for chunk in _chunk(answer):
        await message.channel.send(chunk)

    # If there are shortages, show an embed and store for confirmation
    if shortages:
        # Try to extract bom_name from the answer or user_text
        import re
        bom_match = re.search(r"BOM-[\w-]+", user_text.upper())
        bom_name  = bom_match.group(0) if bom_match else ""

        _pending[channel_id] = {"shortages": shortages, "bom_name": bom_name}
        await message.channel.send(embed=_shortage_embed(shortages, bom_name))


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
