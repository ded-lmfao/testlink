"""
Tests for Lavalink v4.2.0 DAVE (E2EE voice) support.

Covers:
- VoiceRequest TypedDict includes channelId (optional)
- VoiceStateResponse TypedDict includes channelId (optional)
- on_voice_state_update captures channel_id into _voice_state
- _dispatch_voice_update sends channelId when available
- _dispatch_voice_update still works without channelId (backward-compat)
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
    discord_mod.VoiceProtocol = object
    discord_mod.Client = MagicMock()
    discord_mod.Guild = MagicMock()
    discord_mod.utils = discord_utils
    abc_mod = types.ModuleType("discord.abc")
    discord_mod.abc = abc_mod
    abc_mod.Connectable = object
    return discord_mod


@pytest.fixture(autouse=True, scope="module")
def patch_discord():
    d = _make_discord_mod()
    with patch.dict(
        sys.modules,
        {"discord": d, "discord.utils": d.utils, "discord.abc": d.abc},
    ):
        yield


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_node():
    from revvlink.enums import NodeStatus
    from revvlink.node import Node

    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_client.user = MagicMock()
    mock_client.user.id = 99999

    node = Node(
        uri="http://localhost:2333",
        password="youshallnotpass",
        session=mock_session,
        client=mock_client,
        identifier="DAVETestNode",
    )
    node._status = NodeStatus.CONNECTED
    return node


def _make_player(node=None):
    from revvlink.enums import AutoPlayMode
    from revvlink.filters import Filters
    from revvlink.player import Player
    from revvlink.queue import Queue

    node = node or _make_node()
    p = object.__new__(Player)

    p.client = node.client
    p._guild = None
    p._voice_state = {"voice": {}}
    p._node = node
    p._last_update = None
    p._last_position = 0
    p._ping = -1
    p._connected = False
    p._connection_event = asyncio.Event()
    p._current = None
    p._original = None
    p._previous = None
    p.queue = Queue()
    p.auto_queue = Queue()
    p._volume = 100
    p._paused = False
    p._auto_cutoff = 20
    p._auto_weight = 3
    p._previous_seeds_cutoff = 60
    p._history_count = None
    p._autoplay = AutoPlayMode.disabled
    p.__dict__["_Player__previous_seeds"] = asyncio.Queue(maxsize=60)
    p._auto_lock = asyncio.Lock()
    p._error_count = 0
    p._inactive_channel_limit = 3
    p._inactive_channel_count = 3
    p._filters = Filters()
    p._inactivity_task = None
    p._inactivity_wait = 300
    p._should_wait = 10
    p._reconnecting = asyncio.Event()
    p._reconnecting.set()
    p.channel = None
    return p


# ─── TypedDict field tests ────────────────────────────────────────────────────


def test_voice_request_has_channel_id_field():
    """VoiceRequest TypedDict must expose channelId as a valid key."""
    from revvlink.types.request import VoiceRequest

    annotations = VoiceRequest.__annotations__
    assert "channelId" in annotations, "VoiceRequest missing channelId field (DAVE v4.2.0)"


def test_voice_request_required_fields():
    """VoiceRequest must still contain token, endpoint, sessionId."""
    from revvlink.types.request import VoiceRequest

    annotations = VoiceRequest.__annotations__
    for key in ("token", "endpoint", "sessionId"):
        assert key in annotations, f"VoiceRequest missing required field: {key}"


def test_voice_state_response_has_channel_id_field():
    """VoiceStateResponse TypedDict must expose channelId."""
    from revvlink.types.response import VoiceStateResponse

    annotations = VoiceStateResponse.__annotations__
    assert "channelId" in annotations, "VoiceStateResponse missing channelId field"


# ─── on_voice_state_update ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_on_voice_state_update_captures_channel_id():
    """on_voice_state_update stores channel_id in _voice_state for DAVE."""
    p = _make_player()
    mock_channel = MagicMock()
    p.client.get_channel = MagicMock(return_value=mock_channel)

    data = {"channel_id": "987654321", "session_id": "dave_session"}
    await p.on_voice_state_update(data)

    assert p._voice_state.get("channel_id") == "987654321"
    assert p._voice_state["voice"]["session_id"] == "dave_session"
    assert p._connected is True


@pytest.mark.asyncio
async def test_on_voice_state_update_no_channel_id_stored_when_missing():
    """on_voice_state_update with no channel_id calls _destroy (no channel_id stored)."""
    p = _make_player()
    p._destroy = AsyncMock()

    data = {"channel_id": None, "session_id": "some_session"}
    await p.on_voice_state_update(data)

    p._destroy.assert_called_once()
    # channel_id must NOT be stored when there is no channel
    assert p._voice_state.get("channel_id") is None


# ─── _dispatch_voice_update with channelId ────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_voice_update_sends_channel_id():
    """_dispatch_voice_update includes channelId in request when present (DAVE support)."""
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 111

    # Simulate state after on_voice_state_update with channel_id
    p._voice_state = {
        "voice": {
            "session_id": "s_dave",
            "token": "t_dave",
            "endpoint": "us-east1.discord.media",
        },
        "channel_id": "777888999",
    }

    captured: list[dict] = []

    async def _capture_update(guild_id, *, data, **kw):
        captured.append(data)

    p._node._update_player = _capture_update

    await p._dispatch_voice_update()

    assert len(captured) == 1
    voice_payload = captured[0]["voice"]
    assert voice_payload.get("channelId") == "777888999", (
        "channelId missing from voice payload sent to Lavalink"
    )
    assert p._connected is True


@pytest.mark.asyncio
async def test_dispatch_voice_update_works_without_channel_id():
    """_dispatch_voice_update still works correctly when channelId is absent."""
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 222

    # No channel_id in voice_state (older path / backward-compat)
    p._voice_state = {
        "voice": {
            "session_id": "s_old",
            "token": "t_old",
            "endpoint": "us-west2.discord.media",
        }
        # No "channel_id" key
    }

    captured: list[dict] = []

    async def _capture_update(guild_id, *, data, **kw):
        captured.append(data)

    p._node._update_player = _capture_update

    await p._dispatch_voice_update()

    assert len(captured) == 1
    voice_payload = captured[0]["voice"]
    # channelId must NOT appear when it is not set
    assert "channelId" not in voice_payload
    assert p._connected is True


@pytest.mark.asyncio
async def test_dispatch_voice_update_lavalink_error_disconnects():
    """_dispatch_voice_update calls disconnect() when Lavalink raises an error."""
    from revvlink.exceptions import LavalinkException

    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 333
    p._voice_state = {
        "voice": {
            "session_id": "s_err",
            "token": "t_err",
            "endpoint": "us-east1.discord.media",
        },
        "channel_id": "111",
    }
    p.disconnect = AsyncMock()

    err_data = {"timestamp": 1000, "status": 500, "error": "Server Error", "path": "/v4/test"}

    p._node._update_player = AsyncMock(side_effect=LavalinkException(data=err_data))

    await p._dispatch_voice_update()

    p.disconnect.assert_called_once()
