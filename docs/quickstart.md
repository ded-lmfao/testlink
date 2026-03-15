---
title: Quick Start
description: A complete walkthrough for building a Discord music bot with RevvLink.
---

# Quick Start

This guide walks you through building a complete Discord music bot with RevvLink from scratch.

## Prerequisites

- Python 3.10+
- RevvLink installed (`pip install revvlink`)
- A running Lavalink v4 server ([see Installation](installation.md))
- A Discord bot token

## Complete Bot Example

```python title="bot.py"
import asyncio
import logging
from typing import cast

import discord
from discord.ext import commands

import revvlink


class MusicBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        discord.utils.setup_logging(level=logging.INFO)
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        # Connect to your Lavalink node(s)
        nodes = [
            revvlink.Node(
                uri="http://localhost:2333",
                password="youshallnotpass",
            )
        ]
        await revvlink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user} ({self.user.id})")

    # ── Events ──────────────────────────────────────────────────────────────────

    async def on_revvlink_node_ready(
        self, payload: revvlink.NodeReadyEventPayload
    ) -> None:
        logging.info("Node connected: %r | Resumed: %s", payload.node, payload.resumed)

    async def on_revvlink_track_start(
        self, payload: revvlink.TrackStartEventPayload
    ) -> None:
        player = payload.player
        if not player or not hasattr(player, "home"):
            return

        track = payload.track
        embed = discord.Embed(
            title="Now Playing 🎵",
            description=f"**{track.title}** by `{track.author}`",
            color=0x8B5CF6,
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        await player.home.send(embed=embed)  # type: ignore

    async def on_revvlink_track_end(
        self, payload: revvlink.TrackEndEventPayload
    ) -> None:
        player = payload.player
        if not player or player.playing:
            return

        # Play the next track in the queue
        if player.queue:
            await player.play(player.queue.get())


bot = MusicBot()


# ── Commands ──────────────────────────────────────────────────────────────────────

@bot.command()
async def join(ctx: commands.Context) -> None:
    """Join your voice channel."""
    if not ctx.author.voice:  # type: ignore
        await ctx.send("You must be in a voice channel.")
        return
    await ctx.author.voice.channel.connect(cls=revvlink.Player)  # type: ignore
    await ctx.send(f"Joined **{ctx.author.voice.channel.name}**!")  # type: ignore


@bot.command()
async def play(ctx: commands.Context, *, query: str) -> None:
    """Search and play a track."""
    if not ctx.guild:
        return

    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)

    if not player:
        if not ctx.author.voice:  # type: ignore
            await ctx.send("Join a voice channel first!")
            return
        player = await ctx.author.voice.channel.connect(cls=revvlink.Player)  # type: ignore

    player.home = ctx.channel  # type: ignore
    player.autoplay = revvlink.AutoPlayMode.enabled

    tracks: revvlink.Search = await revvlink.Playable.search(query)
    if not tracks:
        await ctx.send(f"No results found for `{query}`.")
        return

    if isinstance(tracks, revvlink.Playlist):
        added = await player.queue.put_wait(tracks)
        await ctx.send(f"Added **{tracks.name}** — {added} tracks.")
    else:
        await player.queue.put_wait(tracks[0])
        await ctx.send(f"Added **{tracks[0].title}** to the queue.")

    if not player.playing:
        await player.play(player.queue.get(), volume=80)


@bot.command()
async def skip(ctx: commands.Context) -> None:
    """Skip the current track."""
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return
    await player.skip(force=True)
    await ctx.message.add_reaction("⏭️")


@bot.command(aliases=["pause", "resume"])
async def toggle(ctx: commands.Context) -> None:
    """Pause or resume playback."""
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return
    await player.pause(not player.paused)
    await ctx.message.add_reaction("⏸️" if player.paused else "▶️")


@bot.command()
async def volume(ctx: commands.Context, vol: int) -> None:
    """Set the volume (0–1000)."""
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return
    await player.set_volume(vol)
    await ctx.send(f"Volume set to **{vol}**.")


@bot.command()
async def queue(ctx: commands.Context) -> None:
    """Show the current queue."""
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player or not player.queue:
        await ctx.send("The queue is empty.")
        return

    lines = [f"`{i+1}.` {t.title}" for i, t in enumerate(player.queue[:10])]
    embed = discord.Embed(
        title="Queue",
        description="\n".join(lines),
        color=0x8B5CF6,
    )
    embed.set_footer(text=f"{len(player.queue)} track(s) total")
    await ctx.send(embed=embed)


@bot.command(aliases=["dc"])
async def disconnect(ctx: commands.Context) -> None:
    """Disconnect the bot."""
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return
    await player.disconnect()
    await ctx.send("Disconnected. 👋")


# ── Run ──────────────────────────────────────────────────────────────────────────

async def main() -> None:
    async with bot:
        await bot.start("YOUR_TOKEN_HERE")

asyncio.run(main())
```

## Key Concepts

### Pool & Nodes

`Pool` is the central connection manager. Connect your nodes once in `setup_hook` and RevvLink handles routing, failover, and reconnection automatically.

### Players

`Player` extends `discord.VoiceClient`. Create one by passing `cls=revvlink.Player` to `connect()`. Players persist across commands — store state on the player instance.

### AutoPlay

Set `player.autoplay = revvlink.AutoPlayMode.enabled` to automatically fetch recommended tracks when the queue empties.

### Events

RevvLink fires events on your bot via the standard `on_*` listener pattern. See [Events Guide](guides/events.md) for the full list.

## Next Steps

- [Node & Pool Guide](guides/node-pool.md) — Multi-node setup and failover
- [Filters Guide](guides/filters.md) — Bass boost, nightcore, and more
- [AutoPlay Guide](guides/autoplay.md) — Recommendation engine deep-dive
