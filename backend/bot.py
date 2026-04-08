"""
Discord bot — ERP assistant.

On mention:  runs the agent, replies with the answer.
On shortage: lists short items and asks user to reply 'order' to send vendor email.
On 'order':  calls the mailer service to send the vendor email.
"""

import asyncio
import os

import discord
import requests
from dotenv import load_dotenv

from agent import run_agent

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MAILER_URL    = os.getenv("MAILER_URL", "http://localhost:3000")
VENDOR_EMAIL  = os.getenv("VENDOR_EMAIL", "vendor@example.com")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Pending shortages per channel waiting for 'order' confirmation
_pending_shortages: dict[int, list[dict]] = {}


@client.event
async def on_ready():
    print(f"ERP Bot logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    channel_id = message.channel.id
    text       = message.content.strip()

    # Handle 'order' confirmation
    if text.lower() == "order" and channel_id in _pending_shortages:
        shortages = _pending_shortages.pop(channel_id)
        await message.channel.send("Sending order email to vendor…")
        try:
            res  = requests.post(
                f"{MAILER_URL}/send-vendor-email",
                json={"shortages": shortages, "vendor_email": VENDOR_EMAIL},
                timeout=10,
            )
            data = res.json()
            await message.channel.send(f"✅ {data.get('message', 'Order email sent.')}")
        except Exception as exc:
            await message.channel.send(f"❌ Failed to send email: {exc}")
        return

    # Only respond to direct mentions
    if client.user not in message.mentions:
        return

    user_text = (
        text
        .replace(f"<@{client.user.id}>", "")
        .replace(f"<@!{client.user.id}>", "")
        .strip()
    )
    if not user_text:
        await message.channel.send("Yes? Ask me anything about inventory or BOMs.")
        return

    await message.channel.send("⏳ Working on it…")

    try:
        answer, shortages = await asyncio.get_event_loop().run_in_executor(
            None, lambda: run_agent(user_text, session_id=str(channel_id))
        )
    except Exception as exc:
        await message.channel.send(f"❌ Agent error: {exc}")
        return

    # Send answer (split if > 2000 chars)
    for chunk in [answer[i:i+1900] for i in range(0, len(answer), 1900)]:
        await message.channel.send(chunk)

    if shortages:
        _pending_shortages[channel_id] = shortages
        lines = "\n".join(
            f"• **{s['item_code']}** — need {s['required']} {s['uom']}, "
            f"have {s['available']}, short by **{s['shortage']}**"
            for s in shortages
        )
        await message.channel.send(
            f"⚠️ **Stock shortage detected:**\n{lines}\n\n"
            f"Reply `order` to send a vendor email for these items."
        )


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set in .env")
    client.run(DISCORD_TOKEN)
