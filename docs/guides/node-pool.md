---
title: Node & Pool
description: Managing Lavalink nodes, the Pool, and multi-node load balancing.
---

# Node & Pool

The `Pool` is the heart of RevvLink — it manages all `Node` connections, handles reconnections, and routes players to the best available node.

## Creating Nodes

```python
import revvlink

node = revvlink.Node(
    uri="http://localhost:2333",
    password="youshallnotpass",
    # Optional:
    identifier="MAIN",      # Human-readable name for this node
    heartbeat=30.0,         # WebSocket ping interval in seconds
    retries=3,              # Reconnect attempts before giving up
    region="us-east",       # Geographic region (for load balancing)
    inactive_player_timeout=300,  # Seconds before auto-disconnecting idle players
)
```

## Connecting the Pool

Always connect in `setup_hook` (not `on_ready`) to ensure nodes are ready before commands:

```python
class Bot(commands.Bot):
    async def setup_hook(self) -> None:
        nodes = [
            revvlink.Node(uri="http://us.lavalink.example", password="secret", region="us-east"),
            revvlink.Node(uri="http://eu.lavalink.example", password="secret", region="eu-west"),
            revvlink.Node(uri="http://ap.lavalink.example", password="secret", region="ap-south"),
        ]
        await revvlink.Pool.connect(nodes=nodes, client=self, cache_capacity=200)
```

## Node Selection

When a player is created, the Pool automatically selects the best node using a penalty-based algorithm. Penalties are computed from:

- **CPU usage** — higher load = higher penalty
- **Memory pressure** — high memory usage increases cost
- **Player count** — nodes with more players receive higher penalties
- **Network latency** — higher ping = higher penalty
- **Frame deficit/nulls** — indicates node audio processing issues

The node with the **lowest total penalty** is chosen.

### Manual Node Assignment

```python
# Force a specific node for a player
node = revvlink.Pool.get_node(identifier="EU-WEST")
player = await channel.connect(cls=revvlink.Player)
await player.move_to(node)
```

## Pool Methods

```python
# Get the Pool instance
pool = revvlink.Pool

# Get a specific node by identifier
node = revvlink.Pool.get_node(identifier="MAIN")

# Get the best node for a guild
node = revvlink.Pool.get_best_node()

# Get all connected nodes
nodes = revvlink.Pool.nodes  # dict[str, Node]

# Close all connections
await revvlink.Pool.close()
```

## Node Statistics

```python
node = revvlink.Pool.get_node()
stats = node.stats

if stats:
    print(f"Players:    {stats.playing_players}")
    print(f"CPU System: {stats.cpu.system_load:.1%}")
    print(f"CPU Lavalink:{stats.cpu.lavalink_load:.1%}")
    print(f"Memory Used: {stats.memory.used / 1024**2:.1f} MB")
    print(f"Uptime:     {stats.uptime // 1000}s")
```

## Node Events

```python
async def on_revvlink_node_ready(payload: revvlink.NodeReadyEventPayload) -> None:
    print(f"Node {payload.node.identifier} ready | Resumed: {payload.resumed}")

async def on_revvlink_node_disconnected(payload: revvlink.NodeDisconnectedEventPayload) -> None:
    print(f"Node {payload.node.identifier} disconnected | Code: {payload.code}")
```

## Failover

When a node disconnects, RevvLink automatically:

1. Marks the node as unavailable
2. Moves all active players to the next best node
3. Resumes playback from where it stopped (if the new node supports session resume)
4. Continues attempting to reconnect in the background

!!! tip "Session Resume"
    RevvLink sends a `resumeKey` to Lavalink on connection. If the connection drops and reconnects within the timeout window, the session (including all players) is resumed seamlessly.

## Cache

The `cache_capacity` parameter enables an LFU (Least Frequently Used) track cache:

```python
await revvlink.Pool.connect(nodes=nodes, client=bot, cache_capacity=500)
```

Cached tracks avoid re-fetching metadata from Lavalink on repeated plays. Set to `None` to disable.
