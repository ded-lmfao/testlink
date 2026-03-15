---
title: Enums
description: API reference for all RevvLink enumerations.
---

# Enums

All enumerations used throughout RevvLink.

---

::: revvlink.NodeStatus

---

::: revvlink.TrackSource

!!! note "Plugin Sources"
    Spotify, Apple Music, Deezer, and other plugin sources are **not** enum members.
    Pass their search prefix as a raw string instead:

    ```python
    # Requires LavaSrc plugin
    tracks = await revvlink.Playable.search("lofi", source="spsearch")   # Spotify
    tracks = await revvlink.Playable.search("lofi", source="amsearch")   # Apple Music
    tracks = await revvlink.Playable.search("lofi", source="dzsearch")   # Deezer
    ```

---

::: revvlink.AutoPlayMode

---

::: revvlink.QueueMode

---

::: revvlink.DiscordVoiceCloseType
