---
title: Installation
description: How to install RevvLink and set up Lavalink.
---

# Installation

RevvLink requires **Python 3.10+** and a running [Lavalink v4](https://github.com/lavalink-devs/Lavalink) server.

## Install RevvLink

=== "pip"

    ```bash
    pip install revvlink
    ```

=== "uv"

    ```bash
    uv venv
    # Creating virtual environment at: .venv
    # Activate with: source .venv/bin/activate
    uv pip install revvlink
    ```

## Setting Up Lavalink

RevvLink requires a running Lavalink v4 server. The quickest way to get one running is with Docker:

```bash
docker run --name lavalink \
  -p 2333:2333 \
  -e SERVER_PASSWORD=youshallnotpass \
  lavalink/lavalink:4
```

Or download the latest `Lavalink.jar` and create an `application.yml`:

```yaml title="application.yml"
server:
  port: 2333
  address: 0.0.0.0
  http2:
    enabled: false
lavalink:
  server:
    password: "youshallnotpass"
    sources:
      youtube: true
      bandcamp: true
      soundcloud: true
      twitch: true
      vimeo: true
      http: true
      local: false
    filters:
      volume: true
      equalizer: true
      karaoke: true
      timescale: true
      tremolo: true
      vibrato: true
      distortion: true
      rotation: true
      channelMix: true
      lowPass: true
    bufferDurationMs: 400
    frameBufferDurationMs: 5000
    youtubePlaylistLoadLimit: 6
    playerUpdateInterval: 5
    youtubeSearchEnabled: true
    soundcloudSearchEnabled: true
    gc-warnings: true
```

Then run it:

```bash
java -jar Lavalink.jar
```

!!! tip "LavaSrc Plugin (Recommended)"
    Install the [LavaSrc](https://github.com/topi314/LavaSrc) plugin to Lavalink to unlock Spotify, Apple Music, and Deezer support.

## Verifying Installation

```python
import revvlink
print(revvlink.__version__)  # e.g. "1.0.0"
```

## Next Steps

- **[Instant Start ⚡](guides/instant-start.md)** — Get music playing in under 5 minutes
- **[Quick Start](quickstart.md)** — Full bot setup walkthrough
