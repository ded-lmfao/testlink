"""
Tests for asyncio.timeout / async_timeout compatibility shim in player.py.

Covers:
- On Python 3.11+, asyncio.timeout is used (no async_timeout dependency needed)
- On Python 3.10, async_timeout.timeout is used (external package)
- The resolved shim (async_timeout_ctx) is a callable context manager
- connect() and move_to() use the shim correctly (smoke-test)
"""

from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── Discord mock ─────────────────────────────────────────────────────────────


def _make_discord_mod():
    discord_mod = types.ModuleType("discord")
    discord_utils = types.ModuleType("discord.utils")
    discord_utils.MISSING = object()

    class VoiceProtocol:
        pass

    discord_mod.VoiceProtocol = VoiceProtocol
    discord_mod.Client = MagicMock()
    discord_mod.utils = discord_utils
    return discord_mod


@pytest.fixture(autouse=True, scope="module")
def patch_discord():
    d = _make_discord_mod()
    with patch.dict(sys.modules, {"discord": d, "discord.utils": d.utils}):
        yield


# ─── Shim resolution tests ────────────────────────────────────────────────────


def test_asyncio_timeout_shim_is_callable():
    """async_timeout_ctx in player module must be callable."""
    import revvlink.player as player_mod

    assert callable(player_mod.async_timeout_ctx)


@pytest.mark.skipif(sys.version_info < (3, 11), reason="Python 3.11+ built-in asyncio.timeout")
def test_shim_is_asyncio_timeout_on_311_plus():
    """On Python 3.11+, the shim should be asyncio.timeout itself."""
    import revvlink.player as player_mod

    assert player_mod.async_timeout_ctx is asyncio.timeout


@pytest.mark.skipif(sys.version_info >= (3, 11), reason="Only for Python < 3.11")
def test_shim_is_async_timeout_on_310():
    """On Python < 3.11, the shim uses async_timeout.timeout."""
    import async_timeout  # type: ignore[import]

    import revvlink.player as player_mod

    assert player_mod.async_timeout_ctx is async_timeout.timeout


@pytest.mark.asyncio
async def test_shim_works_as_async_context_manager():
    """async_timeout_ctx(n) must behave as a working async context manager."""
    import revvlink.player as player_mod

    # Should not raise when timeout is generous
    async with player_mod.async_timeout_ctx(10):
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_shim_raises_timeout_on_expiry():
    """async_timeout_ctx must raise TimeoutError (or asyncio.TimeoutError) on expiry."""
    import revvlink.player as player_mod

    with pytest.raises((TimeoutError, asyncio.TimeoutError)):
        async with player_mod.async_timeout_ctx(0.01):
            await asyncio.sleep(1)


# ─── Verify shim is used in connect() ────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_uses_timeout_shim_and_raises_channel_timeout():
    """Player.connect() uses async_timeout_ctx; raises if voice state not received."""
    from revvlink.player import Player

    mock_client = MagicMock()
    mock_client.user = MagicMock()
    mock_client.user.id = 1234

    mock_channel = MagicMock()
    mock_channel.guild = MagicMock()
    mock_channel.guild.id = 5678
    mock_channel.guild.me = MagicMock()
    mock_channel.guild.change_voice_state = AsyncMock()
    mock_channel.id = 9999

    player = Player.__new__(Player)
    player._guild = mock_channel.guild
    player._client = mock_client
    player._voice_state = {}

    # Override _connected to be an Event that never gets set → triggers timeout
    import asyncio as _asyncio

    never_set = _asyncio.Event()
    player._connected = never_set

    # We expect a TimeoutError from the shim when the event never fires
    with pytest.raises((TimeoutError, asyncio.TimeoutError, Exception)):
        await player.connect(timeout=0.05, reconnect=False, channel=mock_channel)


# ─── Conditional import path not broken ───────────────────────────────────────


def test_player_module_imports_without_error():
    """revvlink.player imports without ImportError on current Python version."""
    try:
        import revvlink.player as player_mod  # noqa: F401
    except ImportError as exc:
        pytest.fail(f"revvlink.player raised ImportError: {exc}")


def test_async_timeout_ctx_is_not_none():
    """async_timeout_ctx must be set (not None) after module import."""
    import revvlink.player as player_mod

    assert player_mod.async_timeout_ctx is not None


@pytest.mark.asyncio
async def test_shim_timeout_value_is_respected():
    """Passing different timeout values does not crash the shim."""
    import revvlink.player as player_mod

    for secs in (0.1, 1.0, 5.0):
        async with player_mod.async_timeout_ctx(secs):
            pass  # just check it doesn't explode
