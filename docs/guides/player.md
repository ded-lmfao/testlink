---
title: Player
description: Creating and controlling the RevvLink Player.
---

# Player

`Player` extends `discord.VoiceClient` and is your main interface for controlling audio playback.

## Creating a Player

Pass `cls=revvlink.Player` to Discord's `connect()`:

```python
player: revvlink.Player = await ctx.author.voice.channel.connect(cls=revvlink.Player)
```

### Accessing an Existing Player

```python
# From guild
player: revvlink.Player | None = ctx.guild.voice_client  # type: ignore

# Or cast it safely
import typing
player = typing.cast("revvlink.Player", ctx.voice_client)
```

## Playback Controls

```python
# Play a track directly
await player.play(track)

# Play with options
await player.play(track, volume=80, start=5000, end=180000)  # start/end in ms

# Play from queue
await player.play(player.queue.get())

# Skip (stop current, play next via autoplay or queue)
await player.skip(force=True)

# Pause / Resume
await player.pause(True)   # pause
await player.pause(False)  # resume

# Seek to position (milliseconds)
await player.seek(30_000)  # jump to 30 seconds

# Set volume (0–1000, default 100)
await player.set_volume(80)

# Stop entirely and clear queue
await player.stop()
```

## Player State

```python
player.playing        # bool — currently playing audio
player.paused         # bool — currently paused
player.connected      # bool — connected to a voice channel
player.current        # Playable | None — currently playing track
player.position       # int — current position in ms
player.volume         # int — current volume (0–1000)
player.queue          # Queue — the player's queue
player.autoplay       # AutoPlayMode — autoplay mode
```

## Filters

Apply audio filters to the player:

```python
filters: revvlink.Filters = player.filters
filters.timescale.set(pitch=1.2, speed=1.2, rate=1.0)  # Nightcore!
await player.set_filters(filters)

# Reset all filters
await player.set_filters()
```

See [Filters Guide](filters.md) for all available filters.

## Moving Between Channels

```python
# Move to a different voice channel
await player.move_to(new_channel)
```

## Disconnecting

```python
await player.disconnect()
```

!!! note "Cleanup"
    `disconnect()` automatically clears the queue and resets the player state. Always prefer this over manual channel disconnect.

## Custom Player State

You can store arbitrary data on the player instance — it persists for the lifetime of the voice connection:

```python
# On first play command:
player.home = ctx.channel       # type: ignore
player.requester = ctx.author   # type: ignore

# Later in an event:
async def on_revvlink_track_start(payload):
    player = payload.player
    if hasattr(player, "home"):
        await player.home.send(f"Now playing: {payload.track.title}")
```

## Player Lifecycle Example

```python
class Bot(commands.Bot):
    async def on_revvlink_track_end(self, payload: revvlink.TrackEndEventPayload) -> None:
        player = payload.player
        if not player:
            return

        if player.autoplay == revvlink.AutoPlayMode.disabled:
            # Manual queue management
            if not player.queue.is_empty:
                await player.play(player.queue.get())
            else:
                await asyncio.sleep(180)  # Wait 3 min then disconnect
                if not player.playing:
                    await player.disconnect()
```
