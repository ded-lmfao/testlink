---
title: Events
description: API reference for RevvLink event payload dataclasses.
---

# Events

All RevvLink events pass a typed payload object to your handler.

| Event | Payload |
|---|---|
| `on_revvlink_node_ready` | `NodeReadyEventPayload` |
| `on_revvlink_node_disconnected` | `NodeDisconnectedEventPayload` |
| `on_revvlink_track_start` | `TrackStartEventPayload` |
| `on_revvlink_track_end` | `TrackEndEventPayload` |
| `on_revvlink_track_exception` | `TrackExceptionEventPayload` |
| `on_revvlink_track_stuck` | `TrackStuckEventPayload` |
| `on_revvlink_websocket_closed` | `WebsocketClosedEventPayload` |
| `on_revvlink_player_update` | `PlayerUpdateEventPayload` |
| `on_revvlink_stats_update` | `StatsEventPayload` |
| `on_revvlink_extra_event` | `ExtraEventPayload` |

!!! tip "Guide"
    See the [Events Guide](../guides/events.md) for handler examples and usage patterns.

---

## Node Events

::: revvlink.NodeReadyEventPayload

---

::: revvlink.NodeDisconnectedEventPayload

---

## Track Events

::: revvlink.TrackStartEventPayload

---

::: revvlink.TrackEndEventPayload

---

::: revvlink.TrackExceptionEventPayload

---

::: revvlink.TrackStuckEventPayload

---

## WebSocket & Player Events

::: revvlink.WebsocketClosedEventPayload

---

::: revvlink.PlayerUpdateEventPayload

---

::: revvlink.StatsEventPayload

---

::: revvlink.StatsEventMemory

---

::: revvlink.StatsEventCPU

---

::: revvlink.StatsEventFrames

---

## Plugin Events

::: revvlink.ExtraEventPayload
