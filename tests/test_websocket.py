"""
Tests for revvlink.websocket.Websocket.
"""

from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from revvlink.enums import NodeStatus

# ─── Mock discord module ──────────────────────────────────────────────────────


def _make_discord_mod():
    discord_mod = types.ModuleType("discord")
    discord_mod.Client = MagicMock()
    discord_mod.user = MagicMock()
    discord_mod.user.id = 12345
    return discord_mod


@pytest.fixture(autouse=True, scope="module")
def patch_discord():
    d = _make_discord_mod()
    with patch.dict(sys.modules, {"discord": d}):
        yield


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_node():
    """Create a fully mocked Node."""
    from revvlink.node import Node

    # Mock the response object
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = {"sourceManagers": [], "plugins": []}
    mock_resp.__aenter__.return_value = mock_resp

    # Mock the session
    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    mock_session.request.return_value = mock_resp
    mock_session.get.return_value = mock_resp
    mock_session.post.return_value = mock_resp
    mock_session.patch.return_value = mock_resp
    mock_session.delete.return_value = mock_resp

    mock_client = MagicMock()
    mock_client.user = MagicMock()
    mock_client.user.id = 12345

    node = Node(
        uri="http://localhost:2333",
        password="youshallnotpass",
        session=mock_session,
        client=mock_client,
        identifier="WebSocketTestNode",
    )
    node._status = NodeStatus.CONNECTED
    return node


@pytest.fixture
def mock_node():
    return _make_node()


def _make_websocket(node=None):
    from revvlink.websocket import Websocket

    node = node or _make_node()
    return Websocket(node=node)


# ─── Tests ───────────────────────────────────────────────────────────────────


def test_websocket_headers():
    """headers property returns correct dict."""
    n = _make_node()
    n._session_id = "test_session"
    ws = _make_websocket(n)

    headers = ws.headers
    assert headers["Authorization"] == "youshallnotpass"
    assert headers["User-Id"] == "12345"
    assert "RevvLink" in headers["Client-Name"]
    assert headers["Session-Id"] == "test_session"


def test_websocket_is_connected():
    """is_connected returns True when socket is open."""
    ws = _make_websocket()
    assert ws.is_connected() is False

    ws.socket = MagicMock()
    ws.socket.closed = False
    assert ws.is_connected() is True

    ws.socket.closed = True
    assert ws.is_connected() is False


@pytest.mark.asyncio
async def test_websocket_update_node():
    """_update_node fetches info and updates state."""
    n = _make_node()
    n._resume_timeout = 60
    n._update_session = AsyncMock()
    n._fetch_info = AsyncMock(return_value={"sourceManagers": ["spotify", "youtube"]})

    ws = _make_websocket(n)
    await ws._update_node()

    n._update_session.assert_called_once()
    n._fetch_info.assert_called_once()
    assert n._spotify_enabled is True


@pytest.mark.asyncio
async def test_websocket_cleanup(mock_node):
    """cleanup resets state and cancels task."""
    from revvlink.websocket import Websocket

    ws = Websocket(node=mock_node)
    mock_task = MagicMock()
    mock_socket = AsyncMock()
    ws.keep_alive_task = mock_task
    ws.socket = mock_socket

    await ws.cleanup()

    mock_task.cancel.assert_called_once()
    mock_socket.close.assert_called_once()
    assert ws.keep_alive_task is None
    assert ws.socket is None
    assert ws.node._status == NodeStatus.DISCONNECTED
    assert ws.node._session_id is None
    assert ws.node._websocket is None


@pytest.mark.asyncio
async def test_websocket_connect_retries(mock_node):
    """Test websocket connect retries and backoff."""
    from revvlink.websocket import Websocket

    ws = Websocket(node=mock_node)
    mock_node._retries = 1

    with (
        patch.object(mock_node._session, "ws_connect", side_effect=Exception("Failed")),
        patch("asyncio.sleep", AsyncMock()) as mock_sleep,
    ):
        await ws.connect()

        # Should have called ws_connect twice (initial + 1 retry)
        assert mock_node._session.ws_connect.call_count == 2
        assert mock_sleep.call_count == 1
        assert ws.node._status == NodeStatus.DISCONNECTED


@pytest.mark.asyncio
async def test_websocket_connect_success():
    """connect successfully establishes a websocket."""
    n = _make_node()
    ws = _make_websocket(n)

    mock_ws = AsyncMock()
    mock_ws.closed = False
    n._session.ws_connect = AsyncMock(return_value=mock_ws)

    # We need to mock keep_alive to avoid it starting a real loop
    with patch.object(ws, "keep_alive", return_value=None):
        await ws.connect()

    assert ws.socket == mock_ws
    n._session.ws_connect.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_connect_auth_failed():
    """connect raises AuthorizationFailedException on 401."""
    from revvlink.exceptions import AuthorizationFailedException

    n = _make_node()
    ws = _make_websocket(n)

    n._session.ws_connect.side_effect = aiohttp.WSServerHandshakeError(
        request_info=MagicMock(), history=(), status=401
    )

    with pytest.raises(AuthorizationFailedException):
        await ws.connect()


@pytest.mark.asyncio
async def test_websocket_connect_not_found():
    """connect raises NodeException on 404."""
    from revvlink.exceptions import NodeException

    n = _make_node()
    ws = _make_websocket(n)

    n._session.ws_connect.side_effect = aiohttp.WSServerHandshakeError(
        request_info=MagicMock(), history=(), status=404
    )

    with pytest.raises(NodeException):
        await ws.connect()


@pytest.mark.asyncio
async def test_websocket_keep_alive_ready():
    """keep_alive processes ready message."""
    n = _make_node()
    ws = _make_websocket(n)
    ws.socket = AsyncMock()
    ws.socket.closed = False

    msg = MagicMock()
    msg.type = aiohttp.WSMsgType.TEXT
    msg.json.return_value = {"op": "ready", "resumed": False, "sessionId": "new_session"}

    ws.socket.receive.side_effect = [msg, asyncio.CancelledError()]
    ws._update_node = AsyncMock()

    try:
        await ws.keep_alive()
    except asyncio.CancelledError:
        pass

    assert n._session_id == "new_session"
    assert n._status == NodeStatus.CONNECTED
    ws._update_node.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_keep_alive_player_update():
    """keep_alive processes playerUpdate message."""
    n = _make_node()
    ws = _make_websocket(n)
    ws.socket = AsyncMock()

    player = MagicMock()
    player._update_event = AsyncMock()
    n.get_player = MagicMock(return_value=player)

    msg = MagicMock()
    msg.type = aiohttp.WSMsgType.TEXT
    msg.json.return_value = {
        "op": "playerUpdate",
        "guildId": "123",
        "state": {"time": 1000, "position": 500, "connected": True, "ping": 20},
    }

    ws.socket.receive.side_effect = [msg, asyncio.CancelledError()]

    try:
        await ws.keep_alive()
    except asyncio.CancelledError:
        pass

    player._update_event.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_keep_alive_track_start():
    """keep_alive processes TrackStartEvent message."""
    n = _make_node()
    ws = _make_websocket(n)
    ws.socket = AsyncMock()

    player = MagicMock()
    player._track_start = AsyncMock()
    n.get_player = MagicMock(return_value=player)

    msg = MagicMock()
    msg.type = aiohttp.WSMsgType.TEXT
    msg.json.return_value = {
        "op": "event",
        "type": "TrackStartEvent",
        "guildId": "123",
        "track": {
            "encoded": "abc",
            "info": {
                "title": "Title",
                "author": "Author",
                "uri": "https://uri",
                "identifier": "id",
                "length": 1000,
                "isStream": False,
                "isSeekable": True,
                "sourceName": "youtube",
                "position": 0,
                "artworkUrl": None,
                "isrc": None,
            },
            "pluginInfo": {},
            "userData": {},
        },
    }

    ws.socket.receive.side_effect = [msg, asyncio.CancelledError()]

    try:
        await ws.keep_alive()
    except asyncio.CancelledError:
        pass

    player._track_start.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_keep_alive_track_end():
    """keep_alive processes TrackEndEvent message."""
    n = _make_node()
    ws = _make_websocket(n)
    ws.socket = AsyncMock()

    player = MagicMock()
    player._auto_play_event = AsyncMock()
    n.get_player = MagicMock(return_value=player)

    msg = MagicMock()
    msg.type = aiohttp.WSMsgType.TEXT
    msg.json.return_value = {
        "op": "event",
        "type": "TrackEndEvent",
        "guildId": "123",
        "track": {
            "encoded": "abc",
            "info": {
                "title": "Title",
                "author": "Author",
                "uri": "https://uri",
                "identifier": "id",
                "length": 1000,
                "isStream": False,
                "isSeekable": True,
                "sourceName": "youtube",
                "position": 0,
                "artworkUrl": None,
                "isrc": None,
            },
            "pluginInfo": {},
            "userData": {},
        },
        "reason": "finished",
    }

    ws.socket.receive.side_effect = [msg, asyncio.CancelledError()]

    try:
        await ws.keep_alive()
    except asyncio.CancelledError:
        pass

    player._auto_play_event.assert_called_once()
    assert player._current is None


@pytest.mark.asyncio
async def test_websocket_keep_alive_websocket_closed():
    """keep_alive processes WebSocketClosedEvent message."""
    n = _make_node()
    ws = _make_websocket(n)
    ws.socket = AsyncMock()

    player = MagicMock()
    player._disconnected_wait = AsyncMock()
    n.get_player = MagicMock(return_value=player)

    msg = MagicMock()
    msg.type = aiohttp.WSMsgType.TEXT
    msg.json.return_value = {
        "op": "event",
        "type": "WebSocketClosedEvent",
        "guildId": "123",
        "code": 4006,
        "reason": "Something",
        "byRemote": True,
    }

    ws.socket.receive.side_effect = [msg, asyncio.CancelledError()]

    try:
        await ws.keep_alive()
    except asyncio.CancelledError:
        pass

    player._disconnected_wait.assert_called_once_with(4006, True)


@pytest.mark.asyncio
async def test_websocket_keep_alive_closed(mock_node):
    """Test keep_alive handling CLOSED/CLOSING messages."""
    ws = _make_websocket(node=mock_node)
    mock_socket = AsyncMock()
    ws.socket = mock_socket

    # Mock CLOSED message
    closed_msg = MagicMock()
    closed_msg.type = aiohttp.WSMsgType.CLOSED
    mock_socket.receive.side_effect = [closed_msg]

    with patch.object(ws, "connect", AsyncMock()) as mock_connect:
        await ws.keep_alive()
        mock_connect.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_stats_op(mock_node):
    """Test stats operation processing."""
    ws = _make_websocket(node=mock_node)
    data = {
        "op": "stats",
        "players": 10,
        "playingPlayers": 5,
        "uptime": 1000,
        "memory": {"free": 100, "used": 200, "index": 0, "reservable": 300, "allocated": 500},
        "cpu": {"cores": 4, "systemLoad": 0.1, "lavalinkLoad": 0.2},
        "frameStats": {"sent": 1000, "nulled": 0, "deficit": 0},
    }

    ws.keep_alive_task = MagicMock()

    # Process stats
    msg = MagicMock()
    msg.type = aiohttp.WSMsgType.TEXT
    msg.data = "mock_data"
    msg.json.return_value = data

    ws.socket = AsyncMock()
    ws.socket.receive.side_effect = [msg, MagicMock(type=aiohttp.WSMsgType.CLOSED)]

    with patch.object(ws, "connect", AsyncMock()):
        await ws.keep_alive()

    assert ws.node._total_player_count == 10


@pytest.mark.asyncio
async def test_websocket_event_track_exception(mock_node):
    """Test TrackExceptionEvent processing."""
    ws = _make_websocket(node=mock_node)
    track_data = {
        "encoded": "encoded",
        "info": {
            "title": "title",
            "author": "author",
            "uri": "uri",
            "identifier": "id",
            "length": 1000,
            "isStream": False,
            "sourceName": "youtube",
            "isSeekable": True,
            "position": 0,
            "artworkUrl": "url",
            "isrc": "isrc",
        },
        "pluginInfo": {},
        "userData": {},
    }
    data = {
        "op": "event",
        "type": "TrackExceptionEvent",
        "guildId": 123,
        "track": track_data,
        "exception": {"message": "error", "severity": "COMMON", "cause": "unknown"},
    }

    ws.socket = AsyncMock()
    msg = MagicMock(type=aiohttp.WSMsgType.TEXT, data="mock")
    msg.json.return_value = data
    ws.socket.receive.side_effect = [msg, MagicMock(type=aiohttp.WSMsgType.CLOSED)]

    with patch.object(ws, "connect", AsyncMock()):
        await ws.keep_alive()

    assert ws.node.client.dispatch.called


@pytest.mark.asyncio
async def test_websocket_event_track_stuck(mock_node):
    """Test TrackStuckEvent processing."""
    ws = _make_websocket(node=mock_node)
    track_data = {
        "encoded": "encoded",
        "info": {
            "title": "title",
            "author": "author",
            "uri": "uri",
            "identifier": "id",
            "length": 1000,
            "isStream": False,
            "sourceName": "youtube",
            "isSeekable": True,
            "position": 0,
            "artworkUrl": "url",
            "isrc": "isrc",
        },
        "pluginInfo": {},
        "userData": {},
    }
    data = {
        "op": "event",
        "type": "TrackStuckEvent",
        "guildId": 123,
        "track": track_data,
        "thresholdMs": 1000,
    }

    ws.socket = AsyncMock()
    msg = MagicMock(type=aiohttp.WSMsgType.TEXT, data="mock")
    msg.json.return_value = data
    ws.socket.receive.side_effect = [msg, MagicMock(type=aiohttp.WSMsgType.CLOSED)]

    with patch.object(ws, "connect", AsyncMock()):
        await ws.keep_alive()

    assert ws.node.client.dispatch.called


@pytest.mark.asyncio
async def test_websocket_extra_event(mock_node):
    """Test processing of unknown event types."""
    ws = _make_websocket(node=mock_node)
    data = {"op": "event", "type": "UnknownEvent", "guildId": 123}

    ws.socket = AsyncMock()
    msg = MagicMock(type=aiohttp.WSMsgType.TEXT, data="mock")
    msg.json.return_value = data
    ws.socket.receive.side_effect = [msg, MagicMock(type=aiohttp.WSMsgType.CLOSED)]

    with patch.object(ws, "connect", AsyncMock()):
        await ws.keep_alive()

    # Should dispatch extra_event
    found = any(
        call.args[0] == "revvlink_extra_event" for call in ws.node.client.dispatch.call_args_list
    )
    assert found


@pytest.mark.asyncio
async def test_websocket_unknown_op(mock_node):
    """Test processing of unknown OP codes."""
    ws = _make_websocket(node=mock_node)
    data = {"op": "unknown"}

    ws.socket = AsyncMock()
    msg = MagicMock(type=aiohttp.WSMsgType.TEXT, data="mock")
    msg.json.return_value = data
    ws.socket.receive.side_effect = [msg, MagicMock(type=aiohttp.WSMsgType.CLOSED)]

    with patch.object(ws, "connect", AsyncMock()):
        await ws.keep_alive()

    # Should just disregard
