---
title: Queue
description: API reference for revvlink.Queue — the audio track queue with history, looping, and shuffle support.
---

# Queue

`Queue` is a thread-safe audio queue with built-in history tracking, loop modes, shuffle, and async waiting.
Each `Player` has two queues: `player.queue` (main) and `player.auto_queue` (AutoPlay recommendations).

!!! tip "Guide"
    See the [Queue Guide](../guides/queue.md) for usage patterns, loop modes, and history examples.

---

::: revvlink.Queue
