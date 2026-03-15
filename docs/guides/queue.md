---
title: Queue
description: Working with the RevvLink Queue system.
---

# Queue

RevvLink's `Queue` is a powerful, thread-safe queue with shuffle, history, loop modes, and async support.

## Basic Operations

```python
player.queue          # The Queue instance
player.queue.history  # A second Queue holding previously played tracks
```

### Adding Tracks

```python
# Add a single track (sync)
player.queue.put(track)

# Add a single track (async — waits if the queue is full)
await player.queue.put_wait(track)

# Add a list of tracks
for track in tracks:
    player.queue.put(track)

# Add an entire Playlist at once
added: int = await player.queue.put_wait(playlist)
print(f"Added {added} tracks")
```

### Getting Tracks

```python
# Get the next track (raises QueueEmpty if empty)
track = player.queue.get()

# Async get (waits until a track is available)
track = await player.queue.get_wait()

# Peek without removing
track = player.queue.peek(0)     # First track
track = player.queue.peek(-1)    # Last track
```

### Inspecting the Queue

```python
len(player.queue)             # Number of tracks
player.queue.is_empty         # bool
player.queue.count            # Same as len()
list(player.queue)            # Copy as list

# Iterate
for track in player.queue:
    print(track.title)

# Slice
first_five = player.queue[:5]
```

## Loop Modes

```python
# Loop the entire queue
player.queue.mode = revvlink.QueueMode.loop

# Loop the current track
player.queue.mode = revvlink.QueueMode.loop_all

# No looping (default)
player.queue.mode = revvlink.QueueMode.normal
```

## Shuffle

```python
player.queue.shuffle()
```

## History

The history queue stores previously played tracks (most recent first):

```python
if player.queue.history:
    last = player.queue.history.peek(0)
    print(f"Last played: {last.title}")

# Go back one track
if player.queue.history:
    prev = player.queue.history.get()
    await player.play(prev)
```

## Manipulation

```python
# Remove by index
del player.queue[2]

# Remove a specific track
player.queue.remove(track)

# Insert at position
player.queue.put_at_index(0, track)  # Move to front

# Clear everything
player.queue.reset()

# Clear only queue (keep history)
player.queue.clear()
```

## Queue Example — Full Queue Command

```python
@bot.command()
async def queue(ctx: commands.Context) -> None:
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return await ctx.send("Not connected.")

    q = player.queue
    if q.is_empty and not player.current:
        return await ctx.send("Queue is empty.")

    lines = []
    if player.current:
        lines.append(f"**Now Playing:** {player.current.title}\n")

    for i, track in enumerate(q[:10], 1):
        lines.append(f"`{i}.` {track.title} — {track.author}")

    if len(q) > 10:
        lines.append(f"\n*...and {len(q) - 10} more*")

    embed = discord.Embed(
        title="🎵 Queue",
        description="\n".join(lines),
        color=0x8B5CF6,
    )
    embed.set_footer(text=f"Mode: {q.mode.name} | {len(q)} tracks remaining")
    await ctx.send(embed=embed)
```
