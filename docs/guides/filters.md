---
title: Filters
description: Apply professional audio filters with RevvLink.
---

# Filters

RevvLink exposes all Lavalink v4 audio filters through an easy-to-use `Filters` API.

## How Filters Work

Get the current filter state, modify it, then apply it:

```python
filters: revvlink.Filters = player.filters
# modify filters...
await player.set_filters(filters)
```

Reset all filters to default:

```python
await player.set_filters()  # Pass nothing to reset
```

## Available Filters

### Volume

```python
filters.volume = 1.5   # 150% volume (0.0–5.0)
await player.set_filters(filters)
```

### Equalizer

31 bands from 25 Hz to 16 kHz. Gain values range from -0.25 to 1.0.

```python
# Bass boost preset
filters.equalizer.set(bands=[
    {"band": 0, "gain": 0.3},   # 25 Hz
    {"band": 1, "gain": 0.2},   # 40 Hz
    {"band": 2, "gain": 0.15},  # 63 Hz
    {"band": 3, "gain": 0.1},   # 100 Hz
])
await player.set_filters(filters)
```

### Timescale (Nightcore / Slowed)

```python
# Nightcore
filters.timescale.set(pitch=1.25, speed=1.25, rate=1.0)

# Slowed + Reverb (pair with lowPass)
filters.timescale.set(pitch=0.85, speed=0.85, rate=1.0)
filters.low_pass.set(smoothing=20.0)

await player.set_filters(filters)
```

### Karaoke (Vocal Removal)

```python
filters.karaoke.set(
    level=1.0,          # Effect strength
    mono_level=1.0,
    filter_band=220.0,  # Center frequency (Hz)
    filter_width=100.0,
)
await player.set_filters(filters)
```

### Tremolo

Rapid volume oscillation (trembling effect):

```python
filters.tremolo.set(
    frequency=4.0,   # Oscillation speed (Hz)
    depth=0.75,      # Depth (0.0–1.0)
)
await player.set_filters(filters)
```

### Vibrato

Rapid pitch oscillation:

```python
filters.vibrato.set(
    frequency=4.0,
    depth=0.75,
)
await player.set_filters(filters)
```

### Rotation (8D Audio)

```python
filters.rotation.set(rotation_hz=0.2)  # Rotation speed
await player.set_filters(filters)
```

### Distortion

```python
filters.distortion.set(
    sin_offset=0.0,
    sin_scale=1.0,
    cos_offset=0.0,
    cos_scale=1.0,
    tan_offset=0.0,
    tan_scale=1.0,
    offset=0.0,
    scale=1.0,
)
await player.set_filters(filters)
```

### Channel Mix (Stereo / Mono)

```python
# Full mono
filters.channel_mix.set(
    left_to_left=0.5,
    left_to_right=0.5,
    right_to_left=0.5,
    right_to_right=0.5,
)
await player.set_filters(filters)
```

### Low Pass

```python
filters.low_pass.set(smoothing=20.0)  # Higher = more bass, less treble
await player.set_filters(filters)
```

## Preset Recipes

### Nightcore

```python
@bot.command()
async def nightcore(ctx: commands.Context) -> None:
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return
    f = player.filters
    f.timescale.set(pitch=1.2, speed=1.2, rate=1.0)
    await player.set_filters(f)
    await ctx.message.add_reaction("✅")
```

### Bass Boost

```python
@bot.command()
async def bassboost(ctx: commands.Context) -> None:
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return
    f = player.filters
    f.equalizer.set(bands=[
        {"band": 0, "gain": 0.35},
        {"band": 1, "gain": 0.25},
        {"band": 2, "gain": 0.2},
        {"band": 3, "gain": 0.15},
        {"band": 4, "gain": 0.05},
    ])
    await player.set_filters(f)
    await ctx.message.add_reaction("✅")
```

### 8D Audio

```python
@bot.command()
async def audio_8d(ctx: commands.Context) -> None:
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return
    f = player.filters
    f.rotation.set(rotation_hz=0.2)
    await player.set_filters(f)
    await ctx.message.add_reaction("✅")
```

### Reset

```python
@bot.command()
async def resetfilters(ctx: commands.Context) -> None:
    player: revvlink.Player = cast("revvlink.Player", ctx.voice_client)
    if not player:
        return
    await player.set_filters()  # Pass nothing = reset
    await ctx.message.add_reaction("✅")
```
