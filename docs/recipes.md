---
title: Recipes
description: Practical code recipes for common Discord music bot patterns.
---

# Recipes

Ready-to-use code patterns for common music bot features.

## Now Playing Embed

```python
async def on_revvlink_track_start(payload: revvlink.TrackStartEventPayload) -> None:
    player = payload.player
    if not player or not hasattr(player, "home"):
        return

    track = payload.track
    position = "0:00"
    duration = f"{track.length // 60000}:{(track.length // 1000) % 60:02d}"

    embed = discord.Embed(color=0x8B5CF6)
    embed.set_author(name="Now Playing 🎵")
    embed.title = track.title
    embed.url = track.uri or discord.Embed.Empty
    embed.description = f"by **{track.author}**"

    if track.artwork:
        embed.set_thumbnail(url=track.artwork)

    embed.add_field(name="Duration", value=f"`{duration}`")
    embed.add_field(name="Source", value=f"`{track.source}`")

    if track.album.name:
        embed.add_field(name="Album", value=track.album.name)

    if track.recommended:
        embed.set_footer(text=f"🤖 Recommended via {track.source}")

    await player.home.send(embed=embed)  # type: ignore
```

---

## Queue Paginator

```python
@bot.command()
async def queue(ctx: commands.Context) -> None:
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player or player.queue.is_empty:
        return await ctx.send("Queue is empty.")

    per_page = 10
    pages = [list(player.queue)[i:i+per_page] for i in range(0, len(player.queue), per_page)]

    embeds = []
    for i, page in enumerate(pages):
        lines = [f"`{j+1+i*per_page}.` **{t.title}** — {t.author}" for j, t in enumerate(page)]
        embed = discord.Embed(
            title="🎵 Queue",
            description="\n".join(lines),
            color=0x8B5CF6,
        )
        embed.set_footer(text=f"Page {i+1}/{len(pages)} · {len(player.queue)} tracks")
        embeds.append(embed)

    # Send first page (add buttons for full pagination)
    await ctx.send(embed=embeds[0])
```

---

## Volume Lock (Per-Guild Settings)

```python
MAX_VOLUME = 200  # Set your limit

@bot.command()
async def volume(ctx: commands.Context, vol: int) -> None:
    if not 0 <= vol <= MAX_VOLUME:
        return await ctx.send(f"Volume must be between 0 and {MAX_VOLUME}.")

    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return

    await player.set_volume(vol)
    bar = "█" * (vol // 10) + "░" * (MAX_VOLUME // 10 - vol // 10)
    await ctx.send(f"🔊 `{bar}` **{vol}%**")
```

---

## Filter Preset Menu

```python
PRESETS = {
    "nightcore": lambda f: f.timescale.set(pitch=1.2, speed=1.2, rate=1.0),
    "bassboost": lambda f: f.equalizer.set(bands=[
        {"band": 0, "gain": 0.4}, {"band": 1, "gain": 0.3}, {"band": 2, "gain": 0.2}
    ]),
    "8d":        lambda f: f.rotation.set(rotation_hz=0.2),
    "vaporwave": lambda f: (f.timescale.set(pitch=0.85, speed=0.85, rate=1.0),
                            f.low_pass.set(smoothing=20.0)),
    "karaoke":   lambda f: f.karaoke.set(level=1.0, mono_level=1.0,
                                          filter_band=220.0, filter_width=100.0),
}

@bot.command()
async def filter(ctx: commands.Context, preset: str) -> None:
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return await ctx.send("Not connected.")

    preset = preset.lower()
    if preset not in PRESETS:
        opts = ", ".join(f"`{k}`" for k in PRESETS)
        return await ctx.send(f"Unknown preset. Available: {opts}")

    f = player.filters
    PRESETS[preset](f)
    await player.set_filters(f)
    await ctx.send(f"✅ Applied **{preset}** filter.")
```

---

## Auto-Disconnect on Empty Channel

```python
import asyncio

@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
) -> None:
    if member.bot:
        return

    guild = member.guild
    player: revvlink.Player | None = guild.voice_client  # type: ignore
    if not player:
        return

    # If the bot is the only one left in the channel
    channel = player.channel
    if len([m for m in channel.members if not m.bot]) == 0:
        await asyncio.sleep(30)  # Wait 30 seconds
        # Check again after waiting
        if len([m for m in channel.members if not m.bot]) == 0:
            await player.disconnect()
```

---

## Seek Command with Progress Bar

```python
@bot.command()
async def seek(ctx: commands.Context, timestamp: str) -> None:
    """Seek to a timestamp. Format: 1:30 or 90 (seconds)."""
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player or not player.current:
        return await ctx.send("Nothing is playing.")

    # Parse timestamp
    try:
        if ":" in timestamp:
            parts = timestamp.split(":")
            ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
        else:
            ms = int(timestamp) * 1000
    except ValueError:
        return await ctx.send("Invalid timestamp. Use `1:30` or `90`.")

    track = player.current
    if ms > track.length:
        return await ctx.send("Timestamp is beyond the track length.")

    await player.seek(ms)

    def fmt(t: int) -> str:
        s = t // 1000
        return f"{s // 60}:{s % 60:02d}"

    await ctx.send(f"⏩ Seeked to `{fmt(ms)}` / `{fmt(track.length)}`")
```

---

## Skip Vote

```python
from collections import defaultdict

vote_skips: dict[int, set[int]] = defaultdict(set)  # guild_id -> set of user_ids

@bot.command()
async def voteskip(ctx: commands.Context) -> None:
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player or not player.current:
        return await ctx.send("Nothing playing.")

    channel = player.channel
    listeners = [m for m in channel.members if not m.bot]
    required = max(1, len(listeners) // 2 + 1)  # Majority

    vote_skips[ctx.guild.id].add(ctx.author.id)
    votes = len(vote_skips[ctx.guild.id] & {m.id for m in listeners})

    if votes >= required:
        vote_skips[ctx.guild.id].clear()
        await player.skip(force=True)
        await ctx.send(f"✅ Skip vote passed! ({votes}/{required})")
    else:
        await ctx.send(f"🗳️ Skip vote: **{votes}/{required}** votes")
```
