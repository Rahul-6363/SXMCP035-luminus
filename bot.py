import discord

TOKEN = "REDACTED"

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user in message.mentions:
        user_text = message.content
        await message.channel.send(f"Processing: {user_text}")

client.run(TOKEN)