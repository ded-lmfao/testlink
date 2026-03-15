---
title: AutoPlay
description: Configure RevvLink's intelligent track recommendation engine.
---

# AutoPlay

AutoPlay keeps your music bot playing continuously by fetching recommended tracks when the queue empties.

## Modes

| Mode | Behavior |
|---|---|
| `AutoPlayMode.enabled` | Plays next in queue. When queue empties, fetches recommendations. |
| `AutoPlayMode.partial` | Plays next in queue. **Does not** fetch recommendations when empty. |
| `AutoPlayMode.disabled` | No automatic playback. You manage everything manually. |

## Enabling AutoPlay

```python
player.autoplay = revvlink.AutoPlayMode.enabled
```

Set it before the first `play()` call — typically in your play command:

```python
@bot.command()
async def play(ctx: commands.Context, *, query: str) -> None:
    player = await ctx.author.voice.channel.connect(cls=revvlink.Player)
    player.autoplay = revvlink.AutoPlayMode.enabled  # Set once

    tracks = await revvlink.Playable.search(query)
    await player.queue.put_wait(tracks[0])

    if not player.playing:
        await player.play(player.queue.get())
```

## How Recommendations Work

When AutoPlay is `enabled` and the queue is empty, RevvLink:

1. Looks at the last played track (`player.queue.history`)
2. Calls Lavalink's `loadRecommended` endpoint
3. Adds the recommended track to the queue
4. Plays it automatically

Recommended tracks have `track.recommended == True`.

## Detecting Recommended Tracks

```python
async def on_revvlink_track_start(payload: revvlink.TrackStartEventPayload) -> None:
    track = payload.track
    if track.recommended:
        await player.home.send(
            f"🤖 AutoPlay: **{track.title}** (recommended via {track.source})"
        )
```

## Disabling Mid-Session

```python
@bot.command()
async def autoplay(ctx: commands.Context) -> None:
    player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return

    if player.autoplay == revvlink.AutoPlayMode.enabled:
        player.autoplay = revvlink.AutoPlayMode.disabled
        await ctx.send("AutoPlay **disabled**.")
    else:
        player.autoplay = revvlink.AutoPlayMode.enabled
        await ctx.send("AutoPlay **enabled**.")
```

## AutoPlay with Partial Mode

Use `partial` when you want seamless queue progression but no AI recommendations:

```python
player.autoplay = revvlink.AutoPlayMode.partial
```

This is useful when your bot manages the queue externally (e.g. a custom recommendation engine).

## Queue History

AutoPlay uses the history queue to seed recommendations. You can read it:

```python
if player.queue.history:
    seed_track = player.queue.history.peek(0)
    print(f"Recommendations seeded from: {seed_track.title}")
```

!!! tip "Source Compatibility"
    Recommendations work best with YouTube and YouTube Music tracks. Spotify tracks (via LavaSrc) may fall back to YouTube recommendations.
