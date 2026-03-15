---
title: Instant Start ⚡
description: Get RevvLink playing music in under 5 minutes.
---

# Instant Start ⚡

The fastest path from zero to music. No fluff.

## 1. Install

```bash
pip install revvlink
```

## 2. Start Lavalink

```bash
docker run --rm -p 2333:2333 -e SERVER_PASSWORD=youshallnotpass lavalink/lavalink:4
```

## 3. Bot Code

Copy this, add your token, run it.

```python title="main.py"
import asyncio
import discord
from discord.ext import commands
import revvlink

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

async def setup_hook():
    await revvlink.Pool.connect(
        nodes=[revvlink.Node(uri="http://localhost:2333", password="youshallnotpass")],
        client=bot,
    )
bot.setup_hook = setup_hook

@bot.command()
async def play(ctx, *, query: str):
    if not ctx.author.voice:
        return await ctx.send("Join a voice channel!")
    player = ctx.voice_client or await ctx.author.voice.channel.connect(cls=revvlink.Player)
    tracks = await revvlink.Playable.search(query)
    if not tracks:
        return await ctx.send("No results.")
    await player.queue.put_wait(tracks[0])
    if not player.playing:
        await player.play(player.queue.get())
    await ctx.send(f"Playing **{tracks[0].title}**!")

@bot.command()
async def skip(ctx):
    if ctx.voice_client:
        await ctx.voice_client.skip(force=True)

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

asyncio.run(bot.start("YOUR_TOKEN"))
```

## 4. Test It

```
!play never gonna give you up
!skip
!stop
```

That's it. For the full story see [Quick Start](../quickstart.md).
