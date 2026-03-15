---
title: Events
description: Complete reference for all RevvLink events and their payloads.
---

# Events

RevvLink fires events through the standard `discord.py` event system. Listen with `@bot.event` or `async def on_*` methods on your `Bot` subclass.

## Event Quick Reference

| Event | When |
|---|---|
| `on_revvlink_node_ready` | A node successfully connects / resumes |
| `on_revvlink_node_disconnected` | A node loses connection |
| `on_revvlink_node_closed` | A node is permanently closed |
| `on_revvlink_track_start` | A track begins playing |
| `on_revvlink_track_end` | A track finishes (any reason) |
| `on_revvlink_track_exception` | A track fails with an error |
| `on_revvlink_track_stuck` | A track stalls and cannot continue |
| `on_revvlink_websocket_closed` | The voice WebSocket closes |
| `on_revvlink_player_update` | Periodic player state update (position, ping) |
| `on_revvlink_stats_update` | Periodic node performance statistics |
| `on_revvlink_inactive_player` | Player has been idle with no real listeners |
| `on_revvlink_extra_event` | Any custom event from a Lavalink plugin |

---

## Node Events

### `on_revvlink_node_ready`

```python
async def on_revvlink_node_ready(payload: revvlink.NodeReadyEventPayload) -> None:
    payload.node     # Node — the connected node
    payload.resumed  # bool — True if this is a session resume
```

### `on_revvlink_node_disconnected`

```python
async def on_revvlink_node_disconnected(
    payload: revvlink.NodeDisconnectedEventPayload
) -> None:
    payload.node  # Node — the disconnected node
```

### `on_revvlink_node_closed`

Fired when a node has permanently failed (exhausted retries):

```python
async def on_revvlink_node_closed(payload: revvlink.NodeClosedEventPayload) -> None:
    payload.node  # Node — the closed node
```

---

## Track Events

### `on_revvlink_track_start`

```python
async def on_revvlink_track_start(payload: revvlink.TrackStartEventPayload) -> None:
    payload.player    # Player — the player
    payload.track     # Playable — the track that started
    payload.original  # Playable | None — original track before redirect (e.g. Spotify → YouTube)
```

**Common use:** Send a "Now Playing" embed.

```python
async def on_revvlink_track_start(payload: revvlink.TrackStartEventPayload) -> None:
    player = payload.player
    if not player or not hasattr(player, "home"):
        return

    track = payload.track
    embed = discord.Embed(title="Now Playing", description=f"**{track.title}** by {track.author}", color=0x8B5CF6)
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)
    await player.home.send(embed=embed)  # type: ignore
```

### `on_revvlink_track_end`

```python
async def on_revvlink_track_end(payload: revvlink.TrackEndEventPayload) -> None:
    payload.player  # Player — the player
    payload.track   # Playable — the track that ended
    payload.reason  # TrackEndReason — why the track ended
```

**`TrackEndReason` values:**

| Value | Meaning |
|---|---|
| `FINISHED` | Track played to completion |
| `LOAD_FAILED` | Track failed to load |
| `STOPPED` | Stopped manually |
| `REPLACED` | Replaced by another track |
| `CLEANUP` | Player cleanup |

**Common use:** Play next track manually (only needed if `AutoPlayMode.disabled`):

```python
async def on_revvlink_track_end(payload: revvlink.TrackEndEventPayload) -> None:
    player = payload.player
    if not player or player.playing:
        return
    if not player.queue.is_empty:
        await player.play(player.queue.get())
```

### `on_revvlink_track_exception`

```python
async def on_revvlink_track_exception(
    payload: revvlink.TrackExceptionEventPayload
) -> None:
    payload.player     # Player
    payload.track      # Playable — the failing track
    payload.exception  # ExceptionData — error details
    payload.exception.message   # str | None
    payload.exception.severity  # str — "COMMON" | "SUSPICIOUS" | "FAULT"
    payload.exception.cause     # str
```

### `on_revvlink_track_stuck`

```python
async def on_revvlink_track_stuck(payload: revvlink.TrackStuckEventPayload) -> None:
    payload.player       # Player
    payload.track        # Playable
    payload.threshold    # int — milliseconds the track has been stuck
```

### `on_revvlink_websocket_closed`

```python
async def on_revvlink_websocket_closed(
    payload: revvlink.WebsocketClosedEventPayload
) -> None:
    payload.player  # Player
    payload.code    # int — WebSocket close code
    payload.reason  # str
    payload.by_remote  # bool
```

---

## Extra Events (Plugin)

Lavalink plugins can emit custom events. RevvLink forwards them:

```python
async def on_revvlink_extra_event(payload: revvlink.ExtraEventPayload) -> None:
    payload.player  # Player | None
    payload.node    # Node
    payload.data    # dict — raw event data from the plugin
```
