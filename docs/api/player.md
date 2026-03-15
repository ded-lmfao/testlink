---
title: Player
description: API reference for revvlink.Player.
---

# Player

`Player` extends `discord.VoiceProtocol`. Create one by passing `cls=revvlink.Player` to `channel.connect()`.

```python
player: revvlink.Player = await channel.connect(cls=revvlink.Player)
```

!!! tip "Guide"
    See the [Player Guide](../guides/player.md) for playback patterns, state management, and lifecycle examples.

---

::: revvlink.Player
