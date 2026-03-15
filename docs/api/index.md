---
title: API Reference
description: Full API reference for RevvLink.
---

# API Reference

Complete reference documentation for every public class, method, and type in RevvLink.

## Modules

| Module | Description |
|---|---|
| [Pool](pool.md) | Central connection manager for Lavalink nodes |
| [Node](node.md) | Represents a single Lavalink server connection |
| [Player](player.md) | Audio player, extends `discord.VoiceClient` |
| [Queue](queue.md) | Track queue with history, shuffle, and loop modes |
| [Playable](playable.md) | Track objects and search API |
| [Events](events.md) | Event payload dataclasses |
| [Filters](filters.md) | Audio filter classes |
| [Payloads](payloads.md) | Request/response payload types |
| [Enums](enums.md) | Enumerations used throughout the library |
| [Exceptions](exceptions.md) | Custom exception types |

## Quick Imports

```python
import revvlink

# Core
revvlink.Pool
revvlink.Node
revvlink.Player

# Tracks
revvlink.Playable
revvlink.Playlist

# Queue
revvlink.Queue
revvlink.QueueMode

# Filters
revvlink.Filters

# Enums
revvlink.AutoPlayMode
revvlink.TrackSource
revvlink.TrackEndReason

# Events
revvlink.TrackStartEventPayload
revvlink.TrackEndEventPayload
revvlink.NodeReadyEventPayload

# Exceptions
revvlink.RevvLinkException
revvlink.NodeException
revvlink.PlayerException
revvlink.QueueException
```
