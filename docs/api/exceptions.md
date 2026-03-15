---
title: Exceptions
description: API reference for all RevvLink exception types.
---

# Exceptions

All RevvLink exceptions inherit from `RevvLinkException`. Catch this base class to handle any library error,
or catch specific subclasses for finer control.

```
RevvLinkException (base)
├── PenaltySystemNotActiveException
├── NodeException
├── InvalidClientException
├── AuthorizationFailedException
├── InvalidNodeException
├── LavalinkException
├── LavalinkLoadException
├── InvalidChannelStateException
├── ChannelTimeoutException
└── QueueEmpty
```

---

::: revvlink.RevvLinkException

---

::: revvlink.PenaltySystemNotActiveException

---

::: revvlink.NodeException

---

::: revvlink.InvalidClientException

---

::: revvlink.AuthorizationFailedException

---

::: revvlink.InvalidNodeException

---

::: revvlink.LavalinkException

---

::: revvlink.LavalinkLoadException

---

::: revvlink.InvalidChannelStateException

---

::: revvlink.ChannelTimeoutException

---

::: revvlink.QueueEmpty

---

## Common Patterns

```python
# Catch any RevvLink error
try:
    await player.play(track)
except revvlink.RevvLinkException as e:
    print(f"Error: {e}")

# Handle empty queue
try:
    next_track = player.queue.get()
except revvlink.QueueEmpty:
    await ctx.send("No more tracks.")

# Handle Lavalink API failures
try:
    results = await revvlink.Playable.search(query)
except revvlink.LavalinkLoadException as e:
    await ctx.send(f"Could not load tracks ({e.severity}): {e.error}")
except revvlink.LavalinkException as e:
    await ctx.send(f"Lavalink error {e.status}: {e.error}")
```
