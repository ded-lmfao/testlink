---
title: Pool
description: API reference for revvlink.Pool — the central node connection manager.
---

# Pool

`Pool` is the central connection manager. It holds all `Node` connections, handles reconnection,
and routes players to the best available node via a penalty-based algorithm.

!!! tip "Guide"
    See the [Node & Pool Guide](../guides/node-pool.md) for multi-node setup, failover, and caching.

---

::: revvlink.Pool
