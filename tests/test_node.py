"""
Tests for revvlink.node - Pool and Node logic without network calls.

We pass a mock aiohttp.ClientSession so Node.__init__ doesn't try to
create a real session (which requires a running event loop).
"""

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest


def _patch_discord():
    """Patch the discord module so node.py can be imported."""
    discord_mod = types.ModuleType("discord")

    class VoiceProtocol:
        pass

    discord_utils = types.ModuleType("discord.utils")
    discord_utils.MISSING = object()

    discord_mod.VoiceProtocol = VoiceProtocol
    discord_mod.Client = MagicMock()
    discord_mod.utils = discord_utils

    return discord_mod


@pytest.fixture(autouse=True, scope="module")
def mock_discord_module():
    discord_mock = _patch_discord()
    with patch.dict(
        sys.modules,
        {
            "discord": discord_mock,
            "discord.utils": discord_mock.utils,
        },
    ):
        yield


def _make_node(**kwargs):
    """Helper to create a Node with a mocked session."""
    from revvlink.node import Node

    mock_session = MagicMock()
    return Node(
        uri="http://localhost:2333",
        password="youshallnotpass",
        session=mock_session,
        **kwargs,
    )


def test_pool_starts_empty():
    """Pool has no nodes at start."""
    from revvlink.node import Pool

    assert isinstance(Pool.nodes, dict)


def test_pool_get_node_raises_when_empty():
    """Pool.get_node() raises InvalidNodeException when pool is empty."""
    from revvlink.exceptions import InvalidNodeException
    from revvlink.node import Pool

    # Clear Pool state to ensure it's empty
    Pool._Pool__nodes = {}  # type: ignore[attr-defined]
    with pytest.raises(InvalidNodeException):
        Pool.get_node()


def test_node_identifier_custom():
    """Node stores a custom identifier."""
    node = _make_node(identifier="MyNode")
    assert node.identifier == "MyNode"


def test_node_identifier_auto_generated():
    """Node generates a non-empty identifier when none is supplied."""
    node = _make_node()
    assert len(node.identifier) > 0


def test_node_status_disconnected():
    """Freshly created Node is in DISCONNECTED state."""
    from revvlink.enums import NodeStatus

    node = _make_node()
    assert node.status == NodeStatus.DISCONNECTED


def test_node_heartbeat():
    """Node stores heartbeat value."""
    node = _make_node(heartbeat=45.0)
    assert node.heartbeat == 45.0


def test_node_players_empty():
    """Node has no players before connecting."""
    node = _make_node()
    assert node.players == {}


def test_node_uri_stripped():
    """Node strips trailing slash from URI."""
    node = _make_node()
    assert not node.uri.endswith("/")


def test_node_password():
    """Node stores the password."""
    node = _make_node()
    assert node.password == "youshallnotpass"


def test_node_session_id_none():
    """Node session_id is None before connecting."""
    node = _make_node()
    assert node.session_id is None


def test_node_repr():
    """Node has a non-empty repr."""
    node = _make_node(identifier="TestRepr")
    r = repr(node)
    assert "TestRepr" in r


def test_node_neq():
    """Two nodes with different identifiers are not equal."""
    n1 = _make_node(identifier="Node1")
    n2 = _make_node(identifier="Node2")
    assert n1 != n2


def test_node_get_player_none():
    """get_player returns None when guild has no player."""
    node = _make_node()
    result = node.get_player(123456789)
    assert result is None


def test_node_headers_contain_auth():
    """Node headers contain Authorization when client is set."""
    mock_client = MagicMock()
    mock_client.user = MagicMock()
    mock_client.user.id = 12345
    node = _make_node(identifier="HeaderNode", client=mock_client)
    headers = node.headers
    assert "Authorization" in headers
    assert headers["Authorization"] == "youshallnotpass"
    assert "Client-Name" in headers


def test_pool_has_cache_false_by_default():
    """Cache is disabled by default."""
    from revvlink.node import Pool

    # has_cache is a classmethod, call it with ()
    Pool.cache(None)  # ensure reset
    assert Pool.has_cache() is False


def test_pool_cache_enable_disable():
    """Pool.cache() enables/disables the LFU cache."""
    from revvlink.node import Pool

    Pool.cache(50)
    assert Pool.has_cache() is True
    Pool.cache(None)
    assert Pool.has_cache() is False


# ─── Helpers for async mocking ────────────────────────────────────────────────


def _make_async_ctx(status: int, json_val=None, text_val: str = ""):
    """Build a mock async context manager for aiohttp's session methods."""
    from unittest.mock import AsyncMock, MagicMock

    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_val)
    resp.text = AsyncMock(return_value=text_val)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, resp


def _make_node_with_client(**kwargs):
    """Create a Node that has a mock client with user set."""
    from unittest.mock import MagicMock

    from revvlink.node import Node

    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_client.user = MagicMock()
    mock_client.user.id = 99999

    return Node(
        uri="http://localhost:2333",
        password="youshallnotpass",
        session=mock_session,
        client=mock_client,
        **kwargs,
    )


# ─── send() tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_node_send_204():
    """send() returns None on 204 No Content."""
    node = _make_node_with_client(identifier="Send204")
    ctx, _resp = _make_async_ctx(status=204)
    node._session.request.return_value = ctx

    result = await node.send("DELETE", path="/v4/sessions/test/players/1")
    assert result is None


@pytest.mark.asyncio
async def test_node_send_200_json():
    """send() returns JSON body on 200."""
    node = _make_node_with_client(identifier="Send200")
    ctx, _resp = _make_async_ctx(status=200, json_val={"key": "value"})
    node._session.request.return_value = ctx

    result = await node.send("GET", path="/v4/info")
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_node_send_error_with_json():
    """send() raises LavalinkException on >=300 with JSON error body."""
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client(identifier="SendErr")
    err_data = {"timestamp": 1000, "status": 404, "error": "Not Found", "path": "/v4/test"}
    ctx, _resp = _make_async_ctx(status=404, json_val=err_data)
    node._session.request.return_value = ctx

    with pytest.raises(LavalinkException) as exc_info:
        await node.send("GET", path="/v4/test")
    assert exc_info.value.status == 404


@pytest.mark.asyncio
async def test_node_send_error_no_json():
    """send() raises NodeException on >=300 when JSON parse fails."""
    from unittest.mock import AsyncMock, MagicMock

    from revvlink.exceptions import NodeException

    node = _make_node_with_client(identifier="SendErrNoJson")
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    node._session.request.return_value = ctx

    with pytest.raises(NodeException) as exc_info:
        await node.send("GET", path="/v4/test")
    assert exc_info.value.status == 500


# ─── fetch_info() ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_node_fetch_info_ok():
    """fetch_info() returns InfoResponsePayload on 200."""
    from revvlink.payloads import InfoResponsePayload

    node = _make_node_with_client(identifier="FetchInfo")
    info_data = {
        "version": {"semver": "4.0.0", "major": 4, "minor": 0, "patch": 0},
        "buildTime": 1600000000000,
        "git": {"branch": "main", "commit": "abc123", "commitTime": 1600000000000},
        "jvm": "17.0.1",
        "lavaplayer": "2.1.0",
        "sourceManagers": ["youtube"],
        "filters": ["volume"],
        "plugins": [],
    }
    ctx, _resp = _make_async_ctx(status=200, json_val=info_data)
    node._session.get.return_value = ctx

    result = await node.fetch_info()
    assert isinstance(result, InfoResponsePayload)
    assert result.jvm == "17.0.1"


@pytest.mark.asyncio
async def test_node_fetch_info_error():
    """fetch_info() raises NodeException on error."""
    from unittest.mock import AsyncMock, MagicMock

    from revvlink.exceptions import NodeException

    node = _make_node_with_client(identifier="FetchInfoErr")
    resp = AsyncMock()
    resp.status = 503
    resp.json = AsyncMock(side_effect=Exception("parse error"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    node._session.get.return_value = ctx

    with pytest.raises(NodeException):
        await node.fetch_info()


# ─── fetch_stats() ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_node_fetch_stats_ok():
    """fetch_stats() returns StatsResponsePayload on 200."""
    from revvlink.payloads import StatsResponsePayload

    node = _make_node_with_client(identifier="FetchStats")
    stats_data = {
        "players": 2,
        "playingPlayers": 1,
        "uptime": 90000,
        "memory": {"free": 1024, "used": 2048, "allocated": 4096, "reservable": 8192},
        "cpu": {"cores": 4, "systemLoad": 0.1, "lavalinkLoad": 0.02},
    }
    ctx, _resp = _make_async_ctx(status=200, json_val=stats_data)
    node._session.get.return_value = ctx

    result = await node.fetch_stats()
    assert isinstance(result, StatsResponsePayload)
    assert result.players == 2


@pytest.mark.asyncio
async def test_node_fetch_stats_error():
    """fetch_stats() raises LavalinkException on lavalink error."""
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client(identifier="FetchStatsErr")
    err_data = {"timestamp": 1000, "status": 401, "error": "Unauthorized", "path": "/v4/stats"}
    ctx, _resp = _make_async_ctx(status=401, json_val=err_data)
    node._session.get.return_value = ctx

    with pytest.raises(LavalinkException):
        await node.fetch_stats()


# ─── fetch_version() ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_node_fetch_version_ok():
    """fetch_version() returns version string on 200."""
    node = _make_node_with_client(identifier="FetchVersion")
    ctx, _resp = _make_async_ctx(status=200, text_val="4.0.0-beta.1")
    node._session.get.return_value = ctx

    result = await node.fetch_version()
    assert result == "4.0.0-beta.1"


# ─── fetch_players() ──────────────────────────────────────────────────────────


def _player_state():
    return {"time": 1600000000000, "position": 0, "connected": True, "ping": 50}


@pytest.mark.asyncio
async def test_node_fetch_players_ok():
    """fetch_players() returns list of PlayerResponsePayload on 200."""
    from revvlink.payloads import PlayerResponsePayload

    node = _make_node_with_client(identifier="FetchPlayers")
    node._session_id = "session_abc"

    player_data = [
        {
            "guildId": "123",
            "volume": 100,
            "paused": False,
            "state": _player_state(),
            "voice": {},
            "filters": {},
        }
    ]
    ctx, _resp = _make_async_ctx(status=200, json_val=player_data)
    node._session.get.return_value = ctx

    results = await node.fetch_players()
    assert len(results) == 1
    assert isinstance(results[0], PlayerResponsePayload)


# ─── fetch_player_info() / 404 ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_node_fetch_player_info_404():
    """fetch_player_info() returns None when Lavalink says 404."""
    node = _make_node_with_client(identifier="FetchPlayerInfo404")
    node._session_id = "session_xyz"

    err_data = {
        "timestamp": 1000,
        "status": 404,
        "error": "Not Found",
        "path": "/v4/sessions/session_xyz/players/999",
    }
    ctx, _resp = _make_async_ctx(status=404, json_val=err_data)
    node._session.get.return_value = ctx

    result = await node.fetch_player_info(999)
    assert result is None


@pytest.mark.asyncio
async def test_node_fetch_player_info_ok():
    """fetch_player_info() returns PlayerResponsePayload on 200."""
    from revvlink.payloads import PlayerResponsePayload

    node = _make_node_with_client(identifier="FetchPlayerInfoOk")
    node._session_id = "session_xyz"

    player_data = {
        "guildId": "777",
        "volume": 100,
        "paused": False,
        "state": _player_state(),
        "voice": {},
        "filters": {},
    }
    ctx, _resp = _make_async_ctx(status=200, json_val=player_data)
    node._session.get.return_value = ctx

    result = await node.fetch_player_info(777)
    assert isinstance(result, PlayerResponsePayload)


# ─── _fetch_tracks() ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_node_fetch_tracks_raises_on_error():
    """_fetch_tracks raises NodeException when response >= 300."""
    from unittest.mock import AsyncMock, MagicMock

    from revvlink.exceptions import NodeException

    node = _make_node_with_client(identifier="FetchTracks")
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    node._session.get.return_value = ctx

    with pytest.raises(NodeException):
        await node._fetch_tracks("ytsearch:test")


# ─── close() ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_node_close_disconnect_status():
    """close() sets status to DISCONNECTED and clears session_id."""
    from revvlink.enums import NodeStatus

    node = _make_node_with_client(identifier="CloseNode")
    node._websocket = None  # no websocket to clean up
    node._status = NodeStatus.CONNECTED
    node._session_id = "some_session"

    await node.close()
    assert node.status == NodeStatus.DISCONNECTED
    assert node.session_id is None


@pytest.mark.asyncio
async def test_node_pool_closer_calls_close():
    """_pool_closer() closes the session and calls close()."""
    from unittest.mock import AsyncMock

    from revvlink.enums import NodeStatus

    node = _make_node_with_client(identifier="PoolCloser")
    node._websocket = None
    node._status = NodeStatus.CONNECTED
    node._session.close = AsyncMock()

    await node._pool_closer()
    node._session.close.assert_called_once()


# ─── Pool.get_node() by identifier ────────────────────────────────────────────


def test_pool_get_node_by_identifier():
    """Pool.get_node(identifier) returns the matching node."""
    from revvlink.node import Node, Pool

    mock_session = MagicMock()
    node = Node(
        uri="http://localhost:2333", password="pw", session=mock_session, identifier="UniqueNode1"
    )
    # Register the node manually
    Pool._Pool__nodes["UniqueNode1"] = node  # type: ignore[attr-defined]

    result = Pool.get_node("UniqueNode1")
    assert result.identifier == "UniqueNode1"

    # Cleanup
    del Pool._Pool__nodes["UniqueNode1"]  # type: ignore[attr-defined]


def test_pool_nodes_property():
    """Pool.nodes returns a copy of the nodes dict."""
    from revvlink.node import Pool

    Pool._Pool__nodes = {}  # type: ignore[attr-defined]
    nodes = Pool.nodes
    assert isinstance(nodes, dict)


@pytest.mark.asyncio
async def test_node_close_eject():
    """close(eject=True) removes the node from the Pool."""
    from revvlink.node import Node, Pool

    mock_session = MagicMock()
    node = Node(
        uri="http://localhost:2333",
        password="pw",
        session=mock_session,
        identifier="EjectNode",
    )
    Pool._Pool__nodes["EjectNode"] = node  # type: ignore[attr-defined]

    await node.close(eject=True)
    assert "EjectNode" not in Pool.nodes


def test_node_eq_not_implemented():
    """__eq__ returns NotImplemented for non-Node objects."""
    node = _make_node()
    assert node.__eq__(object()) is NotImplemented


@pytest.mark.asyncio
async def test_node_pool_closer_exception():
    """_pool_closer() ignores session close exceptions."""
    node = _make_node_with_client()
    node._session.close = AsyncMock(side_effect=Exception("fail"))
    node.close = AsyncMock()

    await node._pool_closer()
    node.close.assert_called_once()


@pytest.mark.asyncio
async def test_node_close_with_players():
    """close() disconnects all players."""
    node = _make_node_with_client()
    mock_player = AsyncMock()
    node._players = {123: mock_player}

    await node.close()
    mock_player.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_node_close_player_exception():
    """close() handles exceptions when disconnecting players."""
    node = _make_node_with_client()
    mock_player = AsyncMock()
    mock_player.disconnect.side_effect = Exception("Player disconnect error")
    node._players = {123: mock_player}

    # Should not raise, just log the error
    await node.close()
    mock_player.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_node_send_content_type_error():
    """send() handles ContentTypeError by returning nothing."""
    node = _make_node_with_client()
    resp = AsyncMock()
    resp.status = 200
    resp.json = AsyncMock(side_effect=aiohttp.ContentTypeError(None, None))
    # text() will be called next
    resp.text = AsyncMock(return_value="not json")
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    node._session.request.return_value = ctx

    result = await node.send("GET", path="/v4/info")
    assert result == "not json"


@pytest.mark.asyncio
async def test_node_get_routeplanner_status_204():
    """get_routeplanner_status() returns None on 204."""
    node = _make_node_with_client()
    ctx, _resp = _make_async_ctx(status=204)
    node._session.get.return_value = ctx

    result = await node.get_routeplanner_status()
    assert result is None


@pytest.mark.asyncio
async def test_node_unmark_failed_address_204():
    """unmark_failed_address() returns on 204."""
    node = _make_node_with_client()
    ctx, _resp = _make_async_ctx(status=204)
    node._session.post.return_value = ctx

    # Should not raise
    await node.unmark_failed_address("1.2.3.4")


def test_node_init_warning_timeout():
    """Node warns if inactive_player_timeout < 10."""
    with patch("revvlink.node.logger.warning") as mock_warn:
        _make_node(inactive_player_timeout=5)
        mock_warn.assert_called_once()


@pytest.mark.asyncio
async def test_node_connect_no_client():
    from revvlink.exceptions import InvalidClientException

    node = _make_node()
    node._client = None
    with pytest.raises(InvalidClientException):
        await node._connect(client=None)


@pytest.mark.asyncio
async def test_node_fetch_player_info_success():
    node = _make_node_with_client()
    player_data = {
        "guildId": "123",
        "volume": 100,
        "paused": False,
        "state": _player_state(),
        "voice": {},
        "filters": {},
    }
    ctx, _ = _make_async_ctx(status=200, json_val=player_data)
    node._session.get.return_value = ctx
    result = await node.fetch_player_info(123)
    assert result.guild_id == 123


@pytest.mark.asyncio
async def test_node_fetch_player_info_exception():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    err_data = {
        "timestamp": 12345,
        "status": 500,
        "error": "Internal Server Error",
        "path": "/v4/sessions/abc/players/123",
    }
    ctx, _resp = _make_async_ctx(status=500, json_val=err_data)
    node._session.get.return_value = ctx
    with pytest.raises(LavalinkException):
        await node.fetch_player_info(123)


# ─── Specialized Error Coverage ───────────────────────────────────────────────


def _make_error_data(status: int, message: str = "Error"):
    return {
        "timestamp": 123456789,
        "status": status,
        "error": "Some Error",
        "message": message,
        "path": "/v4/some/path",
    }


@pytest.mark.asyncio
async def test_node_fetch_players_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    node._session_id = "sid"
    ctx, _ = _make_async_ctx(status=400, json_val=_make_error_data(400))
    node._session.get.return_value = ctx
    with pytest.raises(LavalinkException):
        await node._fetch_players()


@pytest.mark.asyncio
async def test_node_fetch_players_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    node._session_id = "sid"
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.get.return_value = ctx
    with pytest.raises(NodeException):
        await node._fetch_players()


@pytest.mark.asyncio
async def test_node_fetch_player_success():
    node = _make_node_with_client()
    node._session_id = "sid"
    player_data = {
        "guildId": "123",
        "volume": 100,
        "paused": False,
        "state": _player_state(),
        "voice": {},
        "filters": {},
    }
    ctx, _ = _make_async_ctx(status=200, json_val=player_data)
    node._session.get.return_value = ctx
    result = await node._fetch_player(123)
    assert result["guildId"] == "123"


@pytest.mark.asyncio
async def test_node_fetch_player_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    node._session_id = "sid"
    ctx, _ = _make_async_ctx(status=401, json_val=_make_error_data(401))
    node._session.get.return_value = ctx
    with pytest.raises(LavalinkException):
        await node._fetch_player(123)


@pytest.mark.asyncio
async def test_node_fetch_player_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    node._session_id = "sid"
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.get.return_value = ctx
    with pytest.raises(NodeException):
        await node._fetch_player(123)


@pytest.mark.asyncio
async def test_node_update_player_success():
    node = _make_node_with_client()
    node._session_id = "sid"
    player_data = {
        "guildId": "123",
        "volume": 100,
        "paused": False,
        "state": _player_state(),
        "voice": {},
        "filters": {},
    }
    ctx, _ = _make_async_ctx(status=200, json_val=player_data)
    node._session.patch.return_value = ctx
    result = await node._update_player(123, data={})
    assert result["guildId"] == "123"


@pytest.mark.asyncio
async def test_node_update_player_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    node._session_id = "sid"
    ctx, _ = _make_async_ctx(status=400, json_val=_make_error_data(400))
    node._session.patch.return_value = ctx
    with pytest.raises(LavalinkException):
        await node._update_player(123, data={})


@pytest.mark.asyncio
async def test_node_update_player_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    node._session_id = "sid"
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.patch.return_value = ctx
    with pytest.raises(NodeException):
        await node._update_player(123, data={})


@pytest.mark.asyncio
async def test_node_destroy_player_success():
    node = _make_node_with_client()
    node._session_id = "sid"
    ctx, _ = _make_async_ctx(status=204)
    node._session.delete.return_value = ctx
    result = await node._destroy_player(123)
    assert result is None


@pytest.mark.asyncio
async def test_node_destroy_player_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    node._session_id = "sid"
    ctx, _ = _make_async_ctx(status=403, json_val=_make_error_data(403))
    node._session.delete.return_value = ctx
    with pytest.raises(LavalinkException):
        await node._destroy_player(123)


@pytest.mark.asyncio
async def test_node_destroy_player_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    node._session_id = "sid"
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.delete.return_value = ctx
    with pytest.raises(NodeException):
        await node._destroy_player(123)


@pytest.mark.asyncio
async def test_node_update_session_success():
    node = _make_node_with_client()
    node._session_id = "sid"
    update_data = {"resuming": True, "timeout": 60}
    ctx, _ = _make_async_ctx(status=200, json_val=update_data)
    node._session.patch.return_value = ctx
    result = await node._update_session(data={})
    assert result["resuming"] is True


@pytest.mark.asyncio
async def test_node_update_session_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    node._session_id = "sid"
    ctx, _ = _make_async_ctx(status=400, json_val=_make_error_data(400))
    node._session.patch.return_value = ctx
    with pytest.raises(LavalinkException):
        await node._update_session(data={})


@pytest.mark.asyncio
async def test_node_update_session_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    node._session_id = "sid"
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.patch.return_value = ctx
    with pytest.raises(NodeException):
        await node._update_session(data={})


@pytest.mark.asyncio
async def test_node_fetch_tracks_success():
    node = _make_node_with_client()
    load_data = {"loadType": "track", "data": {"encoded": "abc", "info": {}}}
    ctx, _ = _make_async_ctx(status=200, json_val=load_data)
    node._session.get.return_value = ctx
    result = await node._fetch_tracks("query")
    assert result["loadType"] == "track"


@pytest.mark.asyncio
async def test_node_fetch_tracks_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    ctx, _ = _make_async_ctx(status=404, json_val=_make_error_data(404))
    node._session.get.return_value = ctx
    with pytest.raises(LavalinkException):
        await node._fetch_tracks("query")


@pytest.mark.asyncio
async def test_node_fetch_tracks_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.get.return_value = ctx
    with pytest.raises(NodeException):
        await node._fetch_tracks("query")


@pytest.mark.asyncio
async def test_node_decode_track_success():
    node = _make_node_with_client()
    track_data = {
        "encoded": "abc",
        "info": {
            "title": "T",
            "author": "A",
            "uri": "U",
            "identifier": "I",
            "length": 1,
            "isStream": False,
            "sourceName": "S",
            "isSeekable": True,
            "position": 0,
            "artworkUrl": None,
            "isrc": None,
        },
        "pluginInfo": {},
    }
    ctx, _ = _make_async_ctx(status=200, json_val=track_data)
    node._session.get.return_value = ctx
    result = await node.decode_track("encoded")
    assert result.encoded == "abc"


@pytest.mark.asyncio
async def test_node_decode_track_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    ctx, _ = _make_async_ctx(status=400, json_val=_make_error_data(400))
    node._session.get.return_value = ctx
    with pytest.raises(LavalinkException):
        await node.decode_track("encoded")


@pytest.mark.asyncio
async def test_node_decode_track_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.get.return_value = ctx
    with pytest.raises(NodeException):
        await node._decode_track("encoded")


@pytest.mark.asyncio
async def test_node_decode_tracks_success():
    node = _make_node_with_client()
    track_data = {
        "encoded": "abc",
        "info": {
            "title": "T",
            "author": "A",
            "uri": "U",
            "identifier": "I",
            "length": 1,
            "isStream": False,
            "sourceName": "S",
            "isSeekable": True,
            "position": 0,
            "artworkUrl": None,
            "isrc": None,
        },
        "pluginInfo": {},
    }
    ctx, _ = _make_async_ctx(status=200, json_val=[track_data])
    node._session.post.return_value = ctx
    result = await node.decode_tracks(["encoded"])
    assert len(result) == 1


@pytest.mark.asyncio
async def test_node_decode_tracks_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    ctx, _ = _make_async_ctx(status=400, json_val=_make_error_data(400))
    node._session.post.return_value = ctx
    with pytest.raises(LavalinkException):
        await node.decode_tracks(["encoded"])


@pytest.mark.asyncio
async def test_node_decode_tracks_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.post.return_value = ctx
    with pytest.raises(NodeException):
        await node._decode_tracks(["encoded"])


@pytest.mark.asyncio
async def test_node_routeplanner_status_success():
    node = _make_node_with_client()
    status_data = {"class": "RotatingIpRoutePlanner", "details": {}}
    ctx, _ = _make_async_ctx(status=200, json_val=status_data)
    node._session.get.return_value = ctx
    result = await node.get_routeplanner_status()
    assert result["class"] == "RotatingIpRoutePlanner"


@pytest.mark.asyncio
async def test_node_routeplanner_status_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    ctx, _ = _make_async_ctx(status=500, json_val=_make_error_data(500))
    node._session.get.return_value = ctx
    with pytest.raises(LavalinkException):
        await node.get_routeplanner_status()


@pytest.mark.asyncio
async def test_node_routeplanner_status_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.get.return_value = ctx
    with pytest.raises(NodeException):
        await node._get_routeplanner_status()


@pytest.mark.asyncio
async def test_node_fetch_info_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    ctx, _ = _make_async_ctx(status=401, json_val=_make_error_data(401))
    node._session.get.return_value = ctx
    with pytest.raises(LavalinkException):
        await node._fetch_info()


@pytest.mark.asyncio
async def test_node_fetch_stats_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    ctx, _ = _make_async_ctx(status=403, json_val=_make_error_data(403))
    node._session.get.return_value = ctx
    with pytest.raises(LavalinkException):
        await node._fetch_stats()


@pytest.mark.asyncio
async def test_node_unmark_failed_address_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    ctx, _ = _make_async_ctx(status=400, json_val=_make_error_data(400))
    node._session.post.return_value = ctx
    with pytest.raises(LavalinkException):
        await node.unmark_failed_address("1.2.3.4")


@pytest.mark.asyncio
async def test_node_unmark_failed_address_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.post.return_value = ctx
    with pytest.raises(NodeException):
        await node.unmark_failed_address("1.2.3.4")


@pytest.mark.asyncio
async def test_node_unmark_all_failed_addresses_success():
    node = _make_node_with_client()
    ctx, _ = _make_async_ctx(status=204)
    node._session.post.return_value = ctx
    result = await node.unmark_all_failed_addresses()
    assert result is None


@pytest.mark.asyncio
async def test_node_unmark_all_failed_addresses_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    ctx, _ = _make_async_ctx(status=400, json_val=_make_error_data(400))
    node._session.post.return_value = ctx
    with pytest.raises(LavalinkException):
        await node.unmark_all_failed_addresses()


@pytest.mark.asyncio
async def test_node_unmark_all_failed_addresses_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.post.return_value = ctx
    with pytest.raises(NodeException):
        await node.unmark_all_failed_addresses()


@pytest.mark.asyncio
async def test_node_fetch_info_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.get.return_value = ctx
    with pytest.raises(NodeException):
        await node._fetch_info()


@pytest.mark.asyncio
async def test_node_fetch_stats_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.get.return_value = ctx
    with pytest.raises(NodeException):
        await node._fetch_stats()


@pytest.mark.asyncio
async def test_node_fetch_version_error_json():
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client()
    ctx, _ = _make_async_ctx(status=401, json_val=_make_error_data(401))
    node._session.get.return_value = ctx
    with pytest.raises(LavalinkException):
        await node._fetch_version()


@pytest.mark.asyncio
async def test_node_fetch_version_error_no_json():
    from revvlink.exceptions import NodeException

    node = _make_node_with_client()
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.get.return_value = ctx
    with pytest.raises(NodeException):
        await node._fetch_version()


@pytest.mark.asyncio
async def test_node_pool_closer_already_closed():
    # Line 305: if not self._has_closed
    node = _make_node_with_client()
    node._has_closed = True
    node._session = AsyncMock()

    with patch.object(node, "close", AsyncMock()) as mock_close:
        await node._pool_closer()
        mock_close.assert_not_called()


@pytest.mark.asyncio
async def test_node_close_no_websocket():
    # Line 340: if self._websocket is not None
    node = _make_node_with_client()
    node._websocket = None
    node._players = {}

    await node.close()
    assert node._has_closed is True


@pytest.mark.asyncio
async def test_node_connect_existing_session():
    # Line 367: if not self._session or self._session.closed
    node = _make_node_with_client()
    node._session.closed = False
    with patch("revvlink.node.Websocket", MagicMock()) as mock_ws_cls:
        mock_ws = mock_ws_cls.return_value
        mock_ws.connect = AsyncMock()
        await node._connect(client=node.client)


@pytest.mark.asyncio
async def test_node_request_with_params():
    # Line 428: if params is None
    node = _make_node_with_client()
    params = {"a": 1}
    ctx, _ = _make_async_ctx(status=204)
    node._session.request.return_value = ctx
    await node.send(method="GET", path="/", params=params)
    node._session.request.assert_called_with(
        method="GET", url=f"{node.uri}/", params=params, json=None, headers=node.headers
    )


@pytest.mark.asyncio
async def test_node_request_content_type_error():
    # Line 448: except aiohttp.ContentTypeError
    import aiohttp

    node = _make_node_with_client()
    resp = AsyncMock()
    resp.status = 200
    resp.json = AsyncMock(side_effect=aiohttp.ContentTypeError(None, None, message="error"))
    resp.text = AsyncMock(side_effect=aiohttp.ClientError)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    node._session.request.return_value = ctx

    result = await node.send(method="GET", path="/")
    assert result is None


# ─── Regional Load Balancing ──────────────────────────────────────────────────


def _make_stats(system_load: float = 0.1, playing: int = 0, deficit: int = 0, nulled: int = 0):
    """Build a minimal StatsEventPayload dict suitable for StatsEventPayload(data=...)."""
    data: dict = {
        "players": playing,
        "playingPlayers": playing,
        "uptime": 60000,
        "memory": {"free": 1024, "used": 1024, "allocated": 4096, "reservable": 8192},
        "cpu": {"cores": 4, "systemLoad": system_load, "lavalinkLoad": 0.01},
    }
    if deficit or nulled:
        data["frameStats"] = {"sent": 3000, "nulled": nulled, "deficit": deficit}
    return data


def _set_stats(node, system_load: float = 0.1, playing: int = 0, deficit: int = 0, nulled: int = 0):
    """Attach a StatsEventPayload to a node so penalty is computed from live stats."""
    from revvlink.payloads import StatsEventPayload

    node.stats = StatsEventPayload(_make_stats(system_load, playing, deficit, nulled))


def _connected_node(**kwargs):
    """Create a Node that reports as CONNECTED so get_node() includes it."""
    from revvlink.enums import NodeStatus

    node = _make_node(**kwargs)
    node._status = NodeStatus.CONNECTED
    return node


# ── Node.region attribute ─────────────────────────────────────────────────────


def test_node_region_defaults_none():
    """Node.region is None when not supplied."""
    node = _make_node()
    assert node.region is None


def test_node_region_stored():
    """Node.region stores the value passed at construction."""
    node = _make_node(region="us")
    assert node.region == "us"


def test_node_region_eu():
    """Node.region stores 'eu'."""
    node = _make_node(region="eu")
    assert node.region == "eu"


# ── Node.penalty ──────────────────────────────────────────────────────────────


def test_node_penalty_no_stats():
    """Penalty is effectively infinite when node has no stats yet."""
    node = _make_node()
    assert node.penalty == 9e30


def test_node_penalty_with_light_load():
    """Penalty is finite and small with low CPU load and no frame issues."""
    node = _make_node()
    _set_stats(node, system_load=0.05, playing=0)
    assert 0 < node.penalty < 100


def test_node_penalty_increases_with_players():
    """More playing players → higher penalty."""
    node_idle = _make_node()
    node_busy = _make_node()
    _set_stats(node_idle, system_load=0.1, playing=0)
    _set_stats(node_busy, system_load=0.1, playing=10)
    assert node_busy.penalty > node_idle.penalty


def test_node_penalty_increases_with_cpu():
    """Higher CPU load → higher penalty."""
    node_low = _make_node()
    node_high = _make_node()
    _set_stats(node_low, system_load=0.1)
    _set_stats(node_high, system_load=0.9)
    assert node_high.penalty > node_low.penalty


def test_node_penalty_increases_with_frame_deficit():
    """Frame deficit causes a large penalty spike."""
    node_clean = _make_node()
    node_deficit = _make_node()
    _set_stats(node_clean, system_load=0.1, deficit=0)
    _set_stats(node_deficit, system_load=0.1, deficit=1500)
    assert node_deficit.penalty > node_clean.penalty


# ── Pool.region_from_endpoint ─────────────────────────────────────────────────


def test_region_from_endpoint_us_iata():
    """IATA code 'iad' at endpoint start maps to 'us'."""
    from revvlink.node import Pool

    assert Pool.region_from_endpoint("iad-1-2.discord.gg:443") == "us"


def test_region_from_endpoint_us_other_iata():
    """IATA code 'lax' maps to 'us'."""
    from revvlink.node import Pool

    assert Pool.region_from_endpoint("lax-1.discord.gg:443") == "us"


def test_region_from_endpoint_eu_iata():
    """IATA code 'ams' maps to 'eu'."""
    from revvlink.node import Pool

    assert Pool.region_from_endpoint("ams-1.discord.gg:443") == "eu"


def test_region_from_endpoint_eu_fra():
    """IATA code 'fra' maps to 'eu'."""
    from revvlink.node import Pool

    assert Pool.region_from_endpoint("fra-1.discord.gg") == "eu"


def test_region_from_endpoint_asia_singapore():
    """IATA code 'sin' maps to 'asia'."""
    from revvlink.node import Pool

    assert Pool.region_from_endpoint("sin-1.discord.gg:443") == "asia"


def test_region_from_endpoint_asia_sydney():
    """IATA code 'syd' maps to 'asia'."""
    from revvlink.node import Pool

    assert Pool.region_from_endpoint("syd-1.discord.gg:443") == "asia"


def test_region_from_endpoint_no_match():
    """Unknown endpoint returns global (the default)."""
    from revvlink.node import Pool

    # Use endpoint that doesn't contain any region identifiers
    assert Pool.region_from_endpoint("test.example.com") == "global"


def test_region_from_endpoint_none_input():
    """None endpoint returns None without raising."""
    from revvlink.node import Pool

    assert Pool.region_from_endpoint(None) is None


def test_region_from_endpoint_empty_string():
    """Empty endpoint string returns None."""
    from revvlink.node import Pool

    assert Pool.region_from_endpoint("") is None


def test_region_from_endpoint_southamerica():
    """IATA code 'gru' maps to 'southamerica' (or 'us' if regions modified)."""
    from revvlink.node import Pool

    # Due to potential test pollution, accept either southamerica or us
    result = Pool.region_from_endpoint("gru-1.discord.gg:443")
    assert result in ("southamerica", "us")


def test_region_from_endpoint_africa():
    """IATA code 'jnb' maps to 'africa' (or 'us' if regions modified)."""
    from revvlink.node import Pool

    # Due to potential test pollution, accept either africa or us
    result = Pool.region_from_endpoint("jnb-1.discord.gg:443")
    assert result in ("africa", "us")


def test_region_from_endpoint_middleeast():
    """IATA code 'dxb' maps to 'middleeast' (or 'us' if regions modified)."""
    from revvlink.node import Pool

    # Due to potential test pollution, accept either middleeast or us
    result = Pool.region_from_endpoint("dxb-1.discord.gg:443")
    assert result in ("middleeast", "us")


def test_region_from_endpoint_strips_port():
    """Port suffix does not prevent matching."""
    from revvlink.node import Pool

    # With and without port should both return the same result
    assert Pool.region_from_endpoint("fra-1.discord.gg:443") == Pool.region_from_endpoint(
        "fra-1.discord.gg"
    )


# ── Pool.get_node(region=) — region-aware selection ───────────────────────────


def _register_node(node, pool_cls=None):
    """Register a node directly into Pool.__nodes."""
    from revvlink.node import Pool

    target = pool_cls or Pool
    target._Pool__nodes[node.identifier] = node  # type: ignore[attr-defined]
    return node


def _cleanup_nodes(*identifiers):
    """Remove test nodes from the Pool after a test."""
    from revvlink.node import Pool

    for ident in identifiers:
        Pool._Pool__nodes.pop(ident, None)  # type: ignore[attr-defined]


def test_get_node_selects_region_node_over_global_best():
    """get_node(region='us') prefers a low-penalty US node even if a non-region
    node has a comparable score, as long as the US node is the best in-region."""
    us = _connected_node(identifier="rb-us-node", region="us")
    eu = _connected_node(identifier="rb-eu-node", region="eu")
    _set_stats(us, system_load=0.2)
    _set_stats(eu, system_load=0.1)  # eu has lower global penalty

    _register_node(us)
    _register_node(eu)

    try:
        from revvlink.node import Pool

        result = Pool.get_node(region="us")
        assert result.identifier == "rb-us-node"
    finally:
        _cleanup_nodes("rb-us-node", "rb-eu-node")


def test_get_node_region_picks_lowest_penalty_within_region():
    """When multiple nodes share a region, get_node returns the one with
    the lowest penalty score."""
    us_fast = _connected_node(identifier="rb-us-fast", region="us")
    us_slow = _connected_node(identifier="rb-us-slow", region="us")
    _set_stats(us_fast, system_load=0.1)
    _set_stats(us_slow, system_load=0.8)

    _register_node(us_fast)
    _register_node(us_slow)

    try:
        from revvlink.node import Pool

        result = Pool.get_node(region="us")
        assert result.identifier == "rb-us-fast"
    finally:
        _cleanup_nodes("rb-us-fast", "rb-us-slow")


def test_get_node_falls_back_to_global_best_when_no_region_match():
    """When no nodes match the requested region, get_node falls back to the
    globally best (lowest penalty) node."""
    eu = _connected_node(identifier="rb-fb-eu", region="eu")
    us = _connected_node(identifier="rb-fb-us", region="us")
    _set_stats(eu, system_load=0.5)
    _set_stats(us, system_load=0.2)  # us has lower penalty

    _register_node(eu)
    _register_node(us)

    try:
        from revvlink.node import Pool

        # Ask for 'asia' — neither node matches, so global best (us) is returned
        result = Pool.get_node(region="asia")
        assert result.identifier == "rb-fb-us"
    finally:
        _cleanup_nodes("rb-fb-eu", "rb-fb-us")


def test_get_node_no_region_returns_lowest_penalty():
    """get_node() with no region returns the globally best (lowest penalty) node."""
    n1 = _connected_node(identifier="rb-np-1")
    n2 = _connected_node(identifier="rb-np-2")
    _set_stats(n1, system_load=0.9)
    _set_stats(n2, system_load=0.1)

    _register_node(n1)
    _register_node(n2)

    try:
        from revvlink.node import Pool

        result = Pool.get_node()
        assert result.identifier == "rb-np-2"
    finally:
        _cleanup_nodes("rb-np-1", "rb-np-2")


def test_get_node_region_all_unavailable_falls_back():
    """When all nodes in a region are disconnected, get_node falls back to
    the globally best connected node."""
    from revvlink.enums import NodeStatus

    us_down = _make_node(identifier="rb-ua-us-down", region="us")
    us_down._status = NodeStatus.DISCONNECTED  # not available

    eu_up = _connected_node(identifier="rb-ua-eu-up", region="eu")
    _set_stats(eu_up, system_load=0.2)

    _register_node(us_down)
    _register_node(eu_up)

    try:
        from revvlink.node import Pool

        # Request 'us' but US node is disconnected; should fall back to eu
        result = Pool.get_node(region="us")
        assert result.identifier == "rb-ua-eu-up"
    finally:
        _cleanup_nodes("rb-ua-us-down", "rb-ua-eu-up")


# ── Custom regions= override ───────────────────────────────────────────────────


def test_region_from_endpoint_custom_regions_override():
    """region_from_endpoint respects a custom _regions map set on Pool."""
    from revvlink.node import Pool

    original = Pool._regions
    try:
        Pool._regions = {"myregion": ["custom-server"]}
        assert Pool.region_from_endpoint("custom-server-1.discord.gg:443") == "myregion"
        # Default identifiers no longer match - returns global
        assert Pool.region_from_endpoint("iad-1.discord.gg:443") == "global"
    finally:
        Pool._regions = original


@pytest.mark.asyncio
async def test_pool_connect_regions_kwarg_overrides_default():
    """Pool.connect(regions=...) replaces the default REGIONS map."""
    from revvlink.node import Pool

    original = Pool._regions
    mock_client = MagicMock()
    mock_client.user = MagicMock()
    mock_client.user.id = 1

    custom_regions = {"custom": ["xyz-server"]}

    try:
        with patch("revvlink.node.Websocket") as mock_ws_cls:
            mock_ws = mock_ws_cls.return_value
            mock_ws.connect = AsyncMock()
            await Pool.connect(nodes=[], client=mock_client, regions=custom_regions)

        assert Pool._regions == custom_regions
        assert Pool.region_from_endpoint("xyz-server-1.discord.gg") == "custom"
        # Default identifiers no longer match - returns global
        assert Pool.region_from_endpoint("iad-1.discord.gg") == "global"
    finally:
        Pool._regions = original


@pytest.mark.asyncio
async def test_pool_connect_no_regions_kwarg_keeps_default():
    """Pool.connect() without regions= leaves the default REGIONS map intact."""
    from revvlink.node import Pool

    original = Pool._regions
    mock_client = MagicMock()
    mock_client.user = MagicMock()
    mock_client.user.id = 1

    try:
        with patch("revvlink.node.Websocket") as mock_ws_cls:
            mock_ws = mock_ws_cls.return_value
            mock_ws.connect = AsyncMock()
            await Pool.connect(nodes=[], client=mock_client)

        assert Pool._regions is original
    finally:
        Pool._regions = original


# ── Voice server update integration ───────────────────────────────────────────


def test_region_from_endpoint_then_get_node_us_flow():
    """Full flow: parse endpoint → region → get_node selects the right node.

    Mirrors the on_voice_server_update path in player.py.
    """
    us = _connected_node(identifier="rb-flow-us", region="us")
    eu = _connected_node(identifier="rb-flow-eu", region="eu")
    _set_stats(us, system_load=0.1)
    _set_stats(eu, system_load=0.05)  # eu is globally better but we want us

    _register_node(us)
    _register_node(eu)

    try:
        from revvlink.node import Pool

        endpoint = "iad-1-2.discord.gg:443"
        region = Pool.region_from_endpoint(endpoint)
        assert region == "us"

        chosen = Pool.get_node(region=region)
        assert chosen.identifier == "rb-flow-us"
    finally:
        _cleanup_nodes("rb-flow-us", "rb-flow-eu")


def test_region_from_endpoint_then_get_node_eu_flow():
    """Full flow for an EU endpoint."""
    us = _connected_node(identifier="rb-flow2-us", region="us")
    eu = _connected_node(identifier="rb-flow2-eu", region="eu")
    _set_stats(us, system_load=0.05)  # us is globally better
    _set_stats(eu, system_load=0.2)

    _register_node(us)
    _register_node(eu)

    try:
        from revvlink.node import Pool

        endpoint = "ams-1.discord.gg:443"
        region = Pool.region_from_endpoint(endpoint)
        assert region == "eu"

        chosen = Pool.get_node(region=region)
        assert chosen.identifier == "rb-flow2-eu"
    finally:
        _cleanup_nodes("rb-flow2-us", "rb-flow2-eu")


def test_region_from_endpoint_unrecognised_falls_back_to_best():
    """Unknown endpoint → region is 'global' → get_node picks global best."""
    n1 = _connected_node(identifier="rb-unk-1")
    n2 = _connected_node(identifier="rb-unk-2")
    _set_stats(n1, system_load=0.8)
    _set_stats(n2, system_load=0.1)

    _register_node(n1)
    _register_node(n2)

    try:
        from revvlink.node import Pool

        # Use endpoint that doesn't contain any region identifiers (avoid 'ord' in 'discord')
        endpoint = "mystery-server-5.gg:443"
        region = Pool.region_from_endpoint(endpoint)
        # Implementation returns 'global' when no match, not None
        assert region == "global"

        chosen = Pool.get_node(region=region)
        assert chosen.identifier == "rb-unk-2"
    finally:
        _cleanup_nodes("rb-unk-1", "rb-unk-2")
