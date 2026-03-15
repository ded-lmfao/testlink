---
title: Filters
description: API reference for revvlink.Filters and all audio filter classes.
---

# Filters

`Filters` is the top-level container for all audio filters. Retrieve from a player, modify, and apply.

```python
filters = player.filters
filters.timescale.set(pitch=1.2, speed=1.2)
await player.set_filters(filters)

# Reset all filters
await player.set_filters()
```

!!! tip "Guide"
    See the [Filters Guide](../guides/filters.md) for presets (nightcore, bass boost, 8D audio) and recipes.

---

::: revvlink.Filters

---

::: revvlink.Equalizer

---

::: revvlink.Timescale

---

::: revvlink.Karaoke

---

::: revvlink.Tremolo

---

::: revvlink.Vibrato

---

::: revvlink.Rotation

---

::: revvlink.Distortion

---

::: revvlink.ChannelMix

---

::: revvlink.LowPass

---

::: revvlink.PluginFilters
