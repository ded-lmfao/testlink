---
title: Playable
description: API reference for revvlink.Playable, revvlink.Playlist, and related track classes.
---

# Playable

A `Playable` represents a single audio track. Use `Playable.search()` to search for tracks.

`Playable.search()` returns `Search`, a type alias for `list[Playable] | Playlist`.

```python
results: revvlink.Search = await revvlink.Playable.search("lofi chill")

if isinstance(results, revvlink.Playlist):
    await player.queue.put_wait(results)
elif results:
    await player.play(results[0])
```

!!! tip "Guide"
    See the [Tracks & Search Guide](../guides/tracks-search.md) for source selection, URL searching, and playlist handling.

---

::: revvlink.Playable

---

::: revvlink.Playlist

---

::: revvlink.PlaylistInfo

---

::: revvlink.Album

---

::: revvlink.Artist
