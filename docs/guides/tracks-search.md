---
title: Tracks & Search
description: Searching for and working with Playable tracks and Playlists.
---

# Tracks & Search

## Searching

`Playable.search()` is the universal search method. It handles URLs, plain queries, and all supported sources.

```python
tracks: revvlink.Search = await revvlink.Playable.search(query)
```

`Search` is `list[Playable] | Playlist`. Always check before indexing:

```python
if isinstance(tracks, revvlink.Playlist):
    # It's a full playlist
    await player.queue.put_wait(tracks)
else:
    # It's a list of individual tracks
    track = tracks[0]
    await player.queue.put_wait(track)
```

## Track Sources

Specify a source to override the default search engine:

```python
# Default (YouTube)
tracks = await revvlink.Playable.search("lofi hip hop")

# Explicit sources
tracks = await revvlink.Playable.search("lofi hip hop", source=revvlink.TrackSource.YouTube)
tracks = await revvlink.Playable.search("lofi hip hop", source=revvlink.TrackSource.YouTubeMusic)
tracks = await revvlink.Playable.search("lofi hip hop", source=revvlink.TrackSource.SoundCloud)

# URL-based (auto-detects source)
tracks = await revvlink.Playable.search("https://open.spotify.com/track/...")  # needs LavaSrc
tracks = await revvlink.Playable.search("https://www.youtube.com/watch?v=...")
tracks = await revvlink.Playable.search("https://soundcloud.com/artist/track")
```

!!! note "Spotify / Apple Music"
    Spotify, Apple Music, and Deezer require the [LavaSrc](https://github.com/topi314/LavaSrc) Lavalink plugin.

## Track Properties

```python
track = tracks[0]

track.title         # str — "Never Gonna Give You Up"
track.author        # str — "Rick Astley"
track.length        # int — duration in milliseconds
track.uri           # str | None — original URL
track.artwork       # str | None — thumbnail/cover image URL
track.source        # str — "youtube", "spotify", etc.
track.isrc          # str | None — ISRC code (if available)
track.recommended   # bool — True if this track was AutoPlay-recommended

track.album.name    # str | None
track.album.url     # str | None

track.playlist.name # str | None — playlist it came from (if any)
track.playlist.url  # str | None
```

## Formatting Duration

```python
def fmt(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"

print(fmt(track.length))  # "3:47"
```

## Playlist

```python
if isinstance(tracks, revvlink.Playlist):
    playlist = tracks
    playlist.name           # str — playlist name
    playlist.url            # str | None
    playlist.selected_track # int — index of auto-selected track (e.g. from URL)
    playlist.artwork        # str | None

    # Iterate tracks
    for track in playlist:
        print(track.title)

    # Bulk-add to queue
    added = await player.queue.put_wait(playlist)
    print(f"Added {added} tracks")
```

## Handling Empty Results

```python
tracks = await revvlink.Playable.search(query)
if not tracks:
    await ctx.send(f"No results found for `{query}`.")
    return
```

## Search Example Command

```python
@bot.command()
async def search(ctx: commands.Context, *, query: str) -> None:
    """Search for tracks and show a numbered list."""
    tracks = await revvlink.Playable.search(query)
    if not tracks or isinstance(tracks, revvlink.Playlist):
        await ctx.send("No track results.")
        return

    results = tracks[:5]
    msg = "\n".join(
        f"`{i+1}.` **{t.title}** — {t.author} `[{t.length // 60000}:{(t.length // 1000) % 60:02d}]`"
        for i, t in enumerate(results)
    )
    await ctx.send(f"Results for `{query}`:\n{msg}\n\nReply with a number to play.")
```
