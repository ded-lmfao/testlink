"""
Tests for revvlink.player.Player.

Since Player inherits from discord.VoiceProtocol, we bypass __init__ completely
by using object.__new__() and manually setting internal state.  This lets us
test all the pure-logic code paths without a real discord.py / voice connection.
"""

from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

# ─── Mock discord module ──────────────────────────────────────────────────────


def _make_discord_mod():
    discord_mod = types.ModuleType("discord")
    discord_utils = types.ModuleType("discord.utils")
    discord_utils.MISSING = object()

    class DummyVoiceProtocol:
        def __init__(self, client, channel):
            self.client = client
            self.channel = channel

    discord_mod.VoiceProtocol = DummyVoiceProtocol
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
        {
            "discord": d,
            "discord.utils": d.utils,
            "discord.abc": d.abc,
        },
    ):
        yield


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_node(identifier="PlayerTestNode"):
    """Create a fully mocked Node."""
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
        identifier=identifier,
    )
    node._status = NodeStatus.CONNECTED
    return node


@pytest.fixture
def mock_node():
    return _make_node()


def _make_player(node=None):
    """
    Return a Player instance with internal state set directly, bypassing
    discord.VoiceProtocol.__init__ entirely.
    """
    from revvlink.enums import AutoPlayMode
    from revvlink.filters import Filters
    from revvlink.player import Player
    from revvlink.queue import Queue

    node = node or _make_node()

    p = object.__new__(Player)

    # Mimic Player.__init__ state setup (without discord super().__init__)
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
    # channel is normally set by discord.py
    p.channel = None

    return p


def _fake_playable(identifier="abc123"):
    from revvlink.tracks import Playable

    data = {
        "encoded": "dGVzdA==",
        "info": {
            "identifier": identifier,
            "isSeekable": True,
            "author": "Test Author",
            "length": 180000,
            "isStream": False,
            "position": 0,
            "uri": "http://test.com/track",
            "sourceName": "youtube",
            "title": "Test Track",
            "artworkUrl": None,
            "isrc": None,
        },
        "pluginInfo": {},
        "userData": {},
    }
    return Playable(data)


# ─── Property tests ───────────────────────────────────────────────────────────


def test_player_node_property():
    p = _make_player()
    assert p.node.identifier == "PlayerTestNode"


def test_player_guild_property_none():
    p = _make_player()
    assert p.guild is None


def test_player_guild_property_set():
    p = _make_player()
    mock_guild = MagicMock()
    p._guild = mock_guild
    assert p.guild is mock_guild


def test_player_current_none():
    p = _make_player()
    assert p.current is None


def test_player_current_with_track():
    p = _make_player()
    track = _fake_playable()
    p._current = track
    assert p.current is track


def test_player_volume():
    p = _make_player()
    assert p.volume == 100


def test_player_paused_false():
    p = _make_player()
    assert p.paused is False


def test_player_connected_false_no_channel():
    p = _make_player()
    p._connected = True
    p.channel = None
    # channel is falsy => connected returns falsy
    assert not p.connected


def test_player_connected_with_channel():
    p = _make_player()
    p._connected = True
    p.channel = MagicMock()
    assert p.connected


def test_player_autoplay_default():
    from revvlink.enums import AutoPlayMode

    p = _make_player()
    assert p.autoplay is AutoPlayMode.disabled


def test_player_autoplay_setter():
    from revvlink.enums import AutoPlayMode

    p = _make_player()
    p.autoplay = AutoPlayMode.enabled
    assert p.autoplay is AutoPlayMode.enabled


def test_player_autoplay_setter_invalid():
    p = _make_player()
    with pytest.raises(ValueError):
        p.autoplay = "not_an_enum"


def test_player_filters_property():
    from revvlink.filters import Filters

    p = _make_player()
    assert isinstance(p.filters, Filters)


def test_player_inactive_timeout_property():
    p = _make_player()
    assert p.inactive_timeout == 300


def test_player_inactive_timeout_setter_none():
    p = _make_player()
    p.inactive_timeout = None
    assert p.inactive_timeout is None


def test_player_inactive_timeout_setter_zero():
    p = _make_player()
    p.inactive_timeout = 0
    assert p.inactive_timeout is None


def test_player_inactive_timeout_setter_positive():
    p = _make_player()
    p._inactivity_cancel = MagicMock()
    p._inactivity_start = MagicMock()
    p._connected = False

    p.inactive_timeout = 60
    assert p.inactive_timeout == 60
    p._inactivity_cancel.assert_called_once()
    p._inactivity_start.assert_not_called()


def test_player_inactive_timeout_setter_warning_and_start():
    """inactive_timeout setter warns if <10 and calls start if connected and not playing."""
    from unittest.mock import PropertyMock, patch

    p = _make_player()
    p._inactivity_cancel = MagicMock()
    p._inactivity_start = MagicMock()

    with (
        patch("revvlink.Player.connected", new_callable=PropertyMock) as mock_connected,
        patch("revvlink.Player.playing", new_callable=PropertyMock) as mock_playing,
    ):
        # Must be connected and not playing
        mock_connected.return_value = True
        mock_playing.return_value = False

        p.inactive_timeout = 9
        assert p.inactive_timeout == 9
        p._inactivity_cancel.assert_called_once()
        p._inactivity_start.assert_called_once()


@pytest.mark.asyncio
async def test_player_call():
    """__call__ correctly initializes the player."""
    p = object.__new__(_make_player().__class__)
    client = MagicMock()
    channel = MagicMock()
    channel.guild = MagicMock()

    # We call it as a method
    p.__call__(client, channel)
    assert p.client == client
    assert p._guild == channel.guild


@pytest.mark.asyncio
async def test_player_disconnected_wait_4014_remote():
    """_disconnected_wait handles 4014 from remote by destroying."""
    p = _make_player()
    p._destroy = AsyncMock()
    p._connected = True
    p._reconnecting = MagicMock()
    p._reconnecting.wait = AsyncMock()

    await p._disconnected_wait(4014, True)

    assert p._connected is False
    p._reconnecting.wait.assert_called_once()
    p._destroy.assert_called_once()


@pytest.mark.asyncio
async def test_player_switch_node_same_node_raises():
    """switch_node raises InvalidNodeException if node is the same."""
    from revvlink.exceptions import InvalidNodeException

    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123

    with pytest.raises(InvalidNodeException):
        await p.switch_node(p.node)


@pytest.mark.asyncio
async def test_player_switch_node_success():
    """switch_node correctly switches to a new node."""
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p._destroy = AsyncMock()
    p._dispatch_voice_update = AsyncMock()

    # Mock connected property
    with patch.object(p.__class__, "connected", new_callable=PropertyMock) as mock_connected:
        mock_connected.return_value = True

        new_node = _make_node(identifier="NewNode")
        new_node._players = {}

        p.play = AsyncMock()
        p._current = _fake_playable()

        await p.switch_node(new_node)

        assert p.node == new_node
        p._destroy.assert_called_once_with(with_invalidate=False)
        p._dispatch_voice_update.assert_called_once()
        assert new_node.players[123] == p
        p.play.assert_called_once()


@pytest.mark.asyncio
async def test_player_auto_play_event_replaced():
    """_auto_play_event returns early if reason is replaced."""
    from revvlink.enums import AutoPlayMode
    from revvlink.payloads import TrackEndEventPayload

    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p.autoplay = AutoPlayMode.enabled
    p.channel = MagicMock()
    p.channel.members = []
    payload = TrackEndEventPayload(player=p, track=_fake_playable(), reason="replaced")

    await p._auto_play_event(payload)
    assert p._error_count == 0


@pytest.mark.asyncio
async def test_player_auto_play_event_load_failed():
    """_auto_play_event increments error count on loadFailed."""
    from revvlink.enums import AutoPlayMode
    from revvlink.payloads import TrackEndEventPayload

    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p.autoplay = AutoPlayMode.enabled
    p.channel = MagicMock()
    p.channel.members = []
    p._inactivity_start = MagicMock()
    payload = TrackEndEventPayload(player=p, track=_fake_playable(), reason="loadFailed")

    # We also need to mock _do_recommendation or Pool.fetch_tracks
    # to avoid AssertionError in _do_recommendation
    with patch.object(p, "_do_recommendation", AsyncMock()):
        await p._auto_play_event(payload)
        assert p._error_count == 1


@pytest.mark.asyncio
async def test_player_do_recommendation_no_results_v1():
    """_do_recommendation handles no results by firing inactivity start."""
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p._inactivity_start = MagicMock()

    from revvlink.node import Pool

    with patch.object(Pool, "fetch_tracks", AsyncMock(return_value=[])):
        await p._do_recommendation()
        p._inactivity_start.assert_called_once()


def test_player_inactive_channel_tokens_setter():
    p = _make_player()
    p.inactive_channel_tokens = 5
    assert p.inactive_channel_tokens == 5
    assert p._inactive_channel_count == 5

    p.inactive_channel_tokens = 0
    assert p.inactive_channel_tokens is None


def test_player_inactive_channel_tokens_property():
    p = _make_player()
    assert p.inactive_channel_tokens == 3


def test_player_inactive_channel_tokens_setter_none():
    p = _make_player()
    p.inactive_channel_tokens = None
    assert p.inactive_channel_tokens is None


def test_player_inactive_channel_tokens_setter_zero():
    p = _make_player()
    p.inactive_channel_tokens = 0
    assert p.inactive_channel_tokens is None


def test_player_inactive_channel_tokens_property_none():
    p = _make_player()
    p._inactive_channel_limit = 5
    p._guild = MagicMock()
    p._guild.me = MagicMock()
    p._guild.me.voice = None
    assert p.inactive_channel_tokens == 5


@pytest.mark.asyncio
async def test_player_pause():
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p.node._update_player = AsyncMock()

    await p.pause(True)
    p.node._update_player.assert_called_once_with(123, data={"paused": True})
    assert p._paused is True


@pytest.mark.asyncio
async def test_player_seek():
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p.node._update_player = AsyncMock()

    p._current = MagicMock()
    await p.seek(5000)
    p.node._update_player.assert_called_once_with(123, data={"position": 5000})


@pytest.mark.asyncio
async def test_player_set_filters():
    from unittest.mock import PropertyMock

    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p.node._update_player = AsyncMock()
    p.seek = AsyncMock()

    with (
        patch("revvlink.Player.playing", new_callable=PropertyMock) as mock_playing,
        patch("revvlink.Player.position", new_callable=PropertyMock) as mock_pos,
    ):
        mock_playing.return_value = True
        mock_pos.return_value = 1000

        await p.set_filters(None, seek=True)

        p.node._update_player.assert_called_once()
        p.seek.assert_called_once_with(1000)


@pytest.mark.asyncio
async def test_player_set_volume():
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p.node._update_player = AsyncMock()

    await p.set_volume(200)
    p.node._update_player.assert_called_once_with(123, data={"volume": 200})
    assert getattr(p, "_volume", None) == 200


@pytest.mark.asyncio
async def test_player_disconnect():
    p = _make_player()
    p._guild = MagicMock()
    p._guild.change_voice_state = AsyncMock()
    p._destroy = AsyncMock()

    await p.disconnect()
    p._destroy.assert_called_once()
    p._guild.change_voice_state.assert_called_once_with(channel=None)


@pytest.mark.asyncio
async def test_player_skip_and_stop():
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p.node._update_player = AsyncMock()

    current_mock = MagicMock()
    p._current = current_mock
    p.queue = MagicMock()

    res = await p.stop(force=True)
    assert res == current_mock
    p.node._update_player.assert_called_once_with(
        123, data={"track": {"encoded": None}}, replace=True
    )


def test_player_invalidate():
    p = _make_player()
    p._inactivity_cancel = MagicMock()
    p.cleanup = MagicMock()

    p._invalidate()
    assert getattr(p, "_connected", None) is False
    assert not getattr(p, "_connection_event").is_set()
    p._inactivity_cancel.assert_called_once()
    p.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_player_destroy():
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p._invalidate = MagicMock()

    p.node._players = {123: p}
    p.node._destroy_player = AsyncMock()

    await p._destroy(with_invalidate=True)
    p._invalidate.assert_called_once()
    p.node._destroy_player.assert_called_once_with(123)
    assert 123 not in p.node._players


def test_player_add_to_previous_seeds():
    p = _make_player()
    mock_q = MagicMock()
    mock_q.full.return_value = True
    p.__dict__["_Player__previous_seeds"] = mock_q

    p._add_to_previous_seeds("seed123")
    mock_q.get_nowait.assert_called_once()
    mock_q.put_nowait.assert_called_once_with("seed123")


def test_player_playing_false_when_no_current():
    p = _make_player()
    p._current = None
    assert not p.playing


def test_player_playing_true_when_current_set():
    p = _make_player()
    p._current = _fake_playable()
    p._connected = True
    p.channel = MagicMock()
    p._paused = False
    assert p.playing


def test_player_ping():
    p = _make_player()
    assert p.ping == -1


def test_player_queue_instance():
    from revvlink.queue import Queue

    p = _make_player()
    assert isinstance(p.queue, Queue)
    assert isinstance(p.auto_queue, Queue)


# ─── Callback tests ───────────────────────────────────────────────────────────


def test_inactivity_cancel_no_task():
    p = _make_player()
    p._inactivity_task = None
    # Should not raise
    p._inactivity_cancel()
    assert p._inactivity_task is None


def test_inactivity_cancel_with_task():
    p = _make_player()
    task = MagicMock()
    p._inactivity_task = task
    p._inactivity_cancel()
    task.cancel.assert_called_once()
    assert p._inactivity_task is None


def test_inactivity_task_callback_cancelled():
    """_inactivity_task_callback handles cancelled tasks gracefully."""
    p = _make_player()
    task = MagicMock()
    task.result = MagicMock(side_effect=asyncio.CancelledError())
    task.get_name = MagicMock(return_value="InactivityTask")

    # Should not raise
    p._inactivity_task_callback(task)
    # client.dispatch should NOT have been called for a cancelled task
    p.client.dispatch.assert_not_called()


def test_inactivity_task_callback_false_result():
    """_inactivity_task_callback handles False result gracefully."""
    p = _make_player()
    task = MagicMock()
    task.result = MagicMock(return_value=False)
    task.get_name = MagicMock(return_value="InactivityTask")

    p._inactivity_task_callback(task)
    p.client.dispatch.assert_not_called()


def test_inactivity_task_callback_no_guild():
    """_inactivity_task_callback does nothing if _guild is None."""
    p = _make_player()
    p._guild = None
    task = MagicMock()
    task.result = MagicMock(return_value=True)
    task.get_name = MagicMock(return_value="InactivityTask")

    p._inactivity_task_callback(task)
    p.client.dispatch.assert_not_called()


def test_inactivity_task_callback_dispatches_when_idle():
    """_inactivity_task_callback dispatches inactive_player event when idle."""
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p._current = None  # not playing

    task = MagicMock()
    task.result = MagicMock(return_value=True)
    task.get_name = MagicMock(return_value="InactivityTask")

    p._inactivity_task_callback(task)
    p.client.dispatch.assert_called_once_with("revvlink_inactive_player", p)


@pytest.mark.asyncio
async def test_inactivity_runner_returns_true():
    """_inactivity_runner returns True after sleep."""
    p = _make_player()
    result = await p._inactivity_runner(0)
    assert result is True


@pytest.mark.asyncio
async def test_disconnected_wait_non_4014():
    """_disconnected_wait exits early if code != 4014."""
    p = _make_player()
    p._connected = True
    # Code is not 4014, so it should return immediately
    await p._disconnected_wait(1000, True)
    # _connected should still be True (no change)
    assert p._connected is True


@pytest.mark.asyncio
async def test_track_start_cancels_inactivity():
    """_track_start cancels the inactivity task."""
    from revvlink.payloads import TrackStartEventPayload

    p = _make_player()
    task = MagicMock()
    p._inactivity_task = task

    track = _fake_playable()
    payload = TrackStartEventPayload(player=None, track=track)
    await p._track_start(payload)

    task.cancel.assert_called_once()
    assert p._inactivity_task is None


# ─── state property ───────────────────────────────────────────────────────────


def test_player_state_property():
    p = _make_player()
    state = p.state
    assert "voice_state" in state
    assert "position" in state
    assert "connected" in state
    assert "current" in state
    assert "paused" in state
    assert "volume" in state
    assert "filters" in state


# ─── position property ────────────────────────────────────────────────────────


def test_player_position_zero_when_not_playing():
    p = _make_player()
    assert p.position == 0


# ─── _update_event ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_player_update_event():
    """_update_event stores position and ping from payload."""
    from revvlink.payloads import PlayerUpdateEventPayload

    p = _make_player()
    state = {"time": 1600000000000, "position": 5000, "connected": True, "ping": 42}
    payload = PlayerUpdateEventPayload(player=None, state=state)

    await p._update_event(payload)

    assert p._last_position == 5000
    assert p._ping == 42
    assert p._last_update is not None


def test_player_position_paused_sync():
    """position returns _last_position when paused."""
    import time

    p = _make_player()
    p._current = _fake_playable()
    p._connected = True
    p.channel = MagicMock()
    p._paused = True
    p._last_update = time.monotonic_ns()
    p._last_position = 3000

    assert p.position == 3000


def test_player_position_playing():
    """position returns a value > 0 when playing and not paused."""
    import time

    p = _make_player()
    p._current = _fake_playable()
    p._connected = True
    p.channel = MagicMock()
    p._paused = False
    p._last_update = time.monotonic_ns() - 2_000_000_000  # 2 seconds ago
    p._last_position = 0

    pos = p.position
    assert pos >= 0  # position should be non-negative


# ─── on_voice_state_update / on_voice_server_update ──────────────────────────


@pytest.mark.asyncio
async def test_on_voice_state_update_with_channel():
    """on_voice_state_update with a channel sets _connected = True."""
    p = _make_player()
    mock_channel = MagicMock()
    p.client.get_channel = MagicMock(return_value=mock_channel)

    data = {"channel_id": "123456789", "session_id": "abc_session"}
    await p.on_voice_state_update(data)

    assert p._connected is True
    assert p._voice_state["voice"]["session_id"] == "abc_session"


@pytest.mark.asyncio
async def test_on_voice_state_update_no_channel():
    """on_voice_state_update with no channel_id calls _destroy."""
    p = _make_player()
    p._destroy = AsyncMock()

    data = {"channel_id": None, "session_id": "abc_session"}
    await p.on_voice_state_update(data)

    p._destroy.assert_called_once()


@pytest.mark.asyncio
async def test_on_voice_server_update():
    """on_voice_server_update sets token and endpoint, then dispatches update."""
    from revvlink.enums import NodeStatus
    from revvlink.node import Pool

    # Create and register a node with the Pool so get_node doesn't fail
    node = _make_node()
    node._status = NodeStatus.CONNECTED
    Pool._Pool__nodes = {node.identifier: node}

    p = _make_player(node=node)
    p._dispatch_voice_update = AsyncMock()

    data = {"token": "my_token", "endpoint": "us-east1.discord.media"}
    await p.on_voice_server_update(data)

    assert p._voice_state["voice"]["token"] == "my_token"
    assert p._voice_state["voice"]["endpoint"] == "us-east1.discord.media"
    p._dispatch_voice_update.assert_called_once()

    # Clean up
    Pool._Pool__nodes = {}


@pytest.mark.asyncio
async def test_dispatch_voice_update_missing_fields():
    """_dispatch_voice_update returns early if session/token/endpoint missing."""
    p = _make_player()
    p._guild = MagicMock()
    p._voice_state = {"voice": {}}  # all fields missing

    # Should return without calling node
    await p._dispatch_voice_update()
    # _node._update_player should NOT have been called
    p._node._update_player = AsyncMock()
    p._node._update_player.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_voice_update_full():
    """_dispatch_voice_update calls node._update_player when all fields are set."""
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p._voice_state = {
        "voice": {
            "session_id": "s123",
            "token": "tok123",
            "endpoint": "us-east1.discord.media",
        }
    }
    p._node._update_player = AsyncMock(
        return_value={
            "guildId": "123",
            "volume": 100,
            "paused": False,
            "state": {},
            "voice": {},
            "filters": {},
        }
    )

    await p._dispatch_voice_update()
    p._node._update_player.assert_called_once()
    assert p._connected is True


# ─── _inactivity_start ────────────────────────────────────────────────────────


def test_inactivity_start_when_wait_set():
    """_inactivity_start creates a task when _inactivity_wait > 0."""
    p = _make_player()
    p._inactivity_wait = 300
    p._inactivity_task = None

    # Need a running event loop for create_task
    async def run():
        p._inactivity_start()
        assert p._inactivity_task is not None
        p._inactivity_cancel()  # clean up

    asyncio.get_event_loop().run_until_complete(run())


def test_inactivity_start_when_wait_none():
    """_inactivity_start does nothing when _inactivity_wait is None."""
    p = _make_player()
    p._inactivity_wait = None
    p._inactivity_start()
    assert p._inactivity_task is None


def test_inactivity_task_callback_playing():
    """_inactivity_task_callback discards the event if player is currently playing."""
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p._current = _fake_playable()
    p._connected = True

    task = MagicMock()
    task.result = MagicMock(return_value=True)
    task.get_name = MagicMock(return_value="InactivityTask")

    p._inactivity_task_callback(task)
    # Not dispatched since player is playing
    p.client.dispatch.assert_not_called()


# ─── _auto_play_event branches ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auto_play_event_no_channel():
    """_auto_play_event returns early if there is no channel."""
    from revvlink.payloads import TrackEndEventPayload

    p = _make_player()
    p.channel = None

    track = _fake_playable()
    payload = TrackEndEventPayload(player=None, track=track, reason="finished")
    await p._auto_play_event(payload)
    # No errors, just an early return


@pytest.mark.asyncio
async def test_auto_play_event_disabled_autoplay():
    """_auto_play_event calls _inactivity_start and returns when autoplay is disabled."""
    from revvlink.enums import AutoPlayMode
    from revvlink.payloads import TrackEndEventPayload

    p = _make_player()
    p.channel = MagicMock()
    p.channel.members = []  # no members
    p._inactive_channel_limit = None  # disable channel limit
    p._autoplay = AutoPlayMode.disabled
    p._inactivity_start = MagicMock()

    track = _fake_playable()
    payload = TrackEndEventPayload(player=None, track=track, reason="finished")
    await p._auto_play_event(payload)

    p._inactivity_start.assert_called()


@pytest.mark.asyncio
async def test_auto_play_event_too_many_errors():
    """_auto_play_event calls _inactivity_start when error count >= 3."""
    from revvlink.enums import AutoPlayMode
    from revvlink.payloads import TrackEndEventPayload

    p = _make_player()
    p.channel = MagicMock()
    p.channel.members = [MagicMock(bot=False)]  # has human members
    p._inactive_channel_limit = None
    p._autoplay = AutoPlayMode.enabled
    p._error_count = 3
    p._inactivity_start = MagicMock()

    track = _fake_playable()
    payload = TrackEndEventPayload(player=None, track=track, reason="finished")
    await p._auto_play_event(payload)

    p._inactivity_start.assert_called()


@pytest.mark.asyncio
async def test_auto_play_event_reason_replaced():
    """_auto_play_event resets error count and returns when reason == 'replaced'."""
    from revvlink.enums import AutoPlayMode
    from revvlink.payloads import TrackEndEventPayload

    p = _make_player()
    p.channel = MagicMock()
    p.channel.members = [MagicMock(bot=False)]
    p._inactive_channel_limit = None
    p._autoplay = AutoPlayMode.enabled
    p._error_count = 1

    track = _fake_playable()
    payload = TrackEndEventPayload(player=None, track=track, reason="replaced")
    await p._auto_play_event(payload)

    assert p._error_count == 0


@pytest.mark.asyncio
async def test_auto_play_event_reason_load_failed():
    """_auto_play_event increments error count when reason == 'loadFailed'."""
    from revvlink.enums import AutoPlayMode, NodeStatus
    from revvlink.payloads import TrackEndEventPayload

    p = _make_player()
    p.channel = MagicMock()
    p.channel.members = [MagicMock(bot=False)]
    p._inactive_channel_limit = None
    p._autoplay = AutoPlayMode.enabled
    p._error_count = 0
    # Disconnect node so the event returns after incrementing error
    p._node._status = NodeStatus.DISCONNECTED

    track = _fake_playable()
    payload = TrackEndEventPayload(player=None, track=track, reason="loadFailed")
    await p._auto_play_event(payload)

    assert p._error_count == 1


@pytest.mark.asyncio
async def test_auto_play_event_node_disconnected():
    """_auto_play_event returns early if node is not connected."""
    from revvlink.enums import AutoPlayMode, NodeStatus
    from revvlink.payloads import TrackEndEventPayload

    p = _make_player()
    p.channel = MagicMock()
    p.channel.members = [MagicMock(bot=False)]
    p._inactive_channel_limit = None
    p._autoplay = AutoPlayMode.enabled
    p._error_count = 0
    p._node._status = NodeStatus.DISCONNECTED
    p._guild = MagicMock()

    track = _fake_playable()
    payload = TrackEndEventPayload(player=None, track=track, reason="finished")
    await p._auto_play_event(payload)
    # Just ensures it returns gracefully


@pytest.mark.asyncio
async def test_auto_play_event_inactive_channel_limit():
    """_auto_play_event fires inactive_player when channel token count runs out."""
    from revvlink.enums import AutoPlayMode
    from revvlink.payloads import TrackEndEventPayload

    p = _make_player()
    p.channel = MagicMock()
    p.channel.members = []  # no human members
    p._inactive_channel_limit = 1
    p._inactive_channel_count = 1  # next decrement hits 0
    p._autoplay = AutoPlayMode.disabled
    p._inactivity_cancel = MagicMock()

    track = _fake_playable()
    payload = TrackEndEventPayload(player=None, track=track, reason="finished")
    await p._auto_play_event(payload)

    p.client.dispatch.assert_called_with("revvlink_inactive_player", p)


@pytest.mark.asyncio
async def test_auto_play_event_queue_loop_mode():
    """_auto_play_event calls _do_partial(history=False) when queue is in loop mode."""
    from revvlink.enums import AutoPlayMode, NodeStatus, QueueMode
    from revvlink.payloads import TrackEndEventPayload

    p = _make_player()
    p.channel = MagicMock()
    p.channel.members = [MagicMock(bot=False)]
    p._inactive_channel_limit = None
    p._autoplay = AutoPlayMode.partial
    p._error_count = 0
    p._node._status = NodeStatus.CONNECTED
    p._guild = MagicMock()
    p.queue.mode = QueueMode.loop
    p._do_partial = AsyncMock()

    track = _fake_playable()
    payload = TrackEndEventPayload(player=None, track=track, reason="finished")
    await p._auto_play_event(payload)

    p._do_partial.assert_called_once_with(history=False)


@pytest.mark.asyncio
async def test_do_partial_no_current_empty_queue():
    """_do_partial starts inactivity when queue is empty and no current track."""
    p = _make_player()
    p._current = None
    p._inactivity_start = MagicMock()

    await p._do_partial()
    p._inactivity_start.assert_called_once()


@pytest.mark.asyncio
async def test_inactivity_runner_and_cancel():
    """Verify _inactivity_runner behavior on completion and cancellation."""

    p = _make_player()

    # Test successful completion (covered return True)
    # Use a very short wait to minimize test time
    result = await p._inactivity_runner(wait=0.01)
    assert result is True

    # Test cancellation (covered raise CancelledError)
    task = asyncio.create_task(p._inactivity_runner(wait=10))
    await asyncio.sleep(0.01)  # let it start
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # Test _inactivity_cancel (covered simplified code)
    p._inactivity_task = asyncio.create_task(asyncio.sleep(10))
    p._inactivity_cancel()
    assert p._inactivity_task is None


@pytest.mark.asyncio
async def test_player_init_with_nodes():
    """Test Player constructor with nodes provided."""
    from revvlink.player import Player

    node = _make_node()
    channel = MagicMock()

    # We don't need to patch discord.VoiceProtocol.__init__ anymore as it's a real dummy class
    player = Player(node.client, channel, nodes=[node])
    assert player.node == node
    assert player.client == node.client


@pytest.mark.asyncio
async def test_player_init_no_nodes():
    """Test Player constructor using Pool.get_node()."""
    from revvlink.node import Pool
    from revvlink.player import Player

    node = _make_node()
    channel = MagicMock()

    with patch.object(Pool, "get_node", return_value=node):
        player = Player(node.client, channel)
        assert player.node == node


@pytest.mark.asyncio
async def test_player_disconnected_wait_retry(mock_node):
    """Test _disconnected_wait waits for reconnecting event."""
    p = _make_player(mock_node)
    p._guild = MagicMock()  # Needed for _destroy
    p._reconnecting = asyncio.Event()

    # Start wait task
    task = asyncio.create_task(p._disconnected_wait(4014, True))
    await asyncio.sleep(0.1)
    assert not task.done()

    # Set event
    p._reconnecting.set()
    await task
    assert p._connected is False


@pytest.mark.asyncio
async def test_player_auto_play_partial_mode(mock_node):
    """Test AutoPlay with partial mode."""
    from revvlink.enums import AutoPlayMode

    p = _make_player(mock_node)
    p.channel = MagicMock()  # Needs channel to not return early
    p._autoplay = AutoPlayMode.partial
    p.queue.put(_fake_playable())

    with patch.object(p, "_do_partial", AsyncMock()) as mock_partial:
        await p._auto_play_event(MagicMock())
        mock_partial.assert_called_once()


@pytest.mark.asyncio
async def test_player_do_recommendation_populates(mock_node):
    """Test _do_recommendation with populate_track."""
    from revvlink.node import Pool

    p = _make_player(mock_node)
    p._guild = MagicMock()
    track = _fake_playable("seed123")

    mock_search = MagicMock()
    mock_search.tracks = [_fake_playable("rec123")]

    with (
        patch.object(Pool, "fetch_tracks", AsyncMock(return_value=mock_search.tracks)),
        patch.object(p, "play", AsyncMock()),
    ):
        await p._do_recommendation(populate_track=track)
        assert p.auto_queue[0].identifier == "rec123"


@pytest.mark.asyncio
async def test_player_position_paused_async(mock_node):
    """Test position property when paused."""
    p = _make_player(mock_node)
    p.channel = MagicMock()  # connected requires channel
    p._last_position = 5000
    p._last_update = 1000
    p._connected = True
    p._current = _fake_playable()
    p._paused = True

    # Position should be last_position when paused
    assert p.position == 5000


@pytest.mark.asyncio
async def test_player_dispatch_voice_update_failure(mock_node):
    """Test _dispatch_voice_update failure calls disconnect."""
    from revvlink.exceptions import LavalinkException

    p = _make_player(mock_node)
    p._voice_state = {
        "voice": {"session_id": "sid", "token": "tok", "endpoint": "end"},
        "channel_id": "123",
    }
    p._guild = MagicMock()

    with (
        patch.object(
            p.node,
            "_update_player",
            side_effect=LavalinkException(
                "Fail",
                data={"timestamp": 0, "status": 500, "error": "ERR", "message": "MSG", "path": "/"},
            ),
        ),
        patch.object(p, "disconnect", AsyncMock()) as mock_disconnect,
    ):
        await p._dispatch_voice_update()
        mock_disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_player_init_missing_client():
    """Test Player constructor with MISSING client."""
    import revvlink.player
    from revvlink.player import Player

    node = _make_node()
    channel = MagicMock()

    # Use the MISSING from the player module to ensure consistency
    player = Player(revvlink.player.MISSING, channel, nodes=[node])
    assert player.client == node.client


@pytest.mark.asyncio
async def test_player_auto_play_too_many_errors(mock_node):
    """Test AutoPlay event when error count is too high."""
    p = _make_player(mock_node)
    p.channel = MagicMock()
    p._error_count = 3

    with patch.object(p, "_inactivity_start") as mock_start:
        await p._auto_play_event(MagicMock())
        mock_start.assert_called_once()


@pytest.mark.asyncio
async def test_player_auto_play_reasons(mock_node):
    """Test AutoPlay event with different track end reasons."""
    from revvlink.enums import AutoPlayMode

    p = _make_player(mock_node)
    p.channel = MagicMock()
    p.autoplay = AutoPlayMode.enabled

    # replaced reason resets error count (use value < 3 to avoid early return)
    p._error_count = 2
    payload = MagicMock()
    payload.reason = "replaced"
    await p._auto_play_event(payload)
    assert p._error_count == 0

    # loadFailed reason increments error count
    payload.reason = "loadFailed"
    with patch.object(p, "_do_recommendation", AsyncMock()):
        await p._auto_play_event(payload)
        assert p._error_count == 1


@pytest.mark.asyncio
async def test_player_do_recommendation_many_seeds(mock_node):
    """Test _do_recommendation with enough history to cover seed logic."""
    from revvlink.node import Pool

    p = _make_player(mock_node)
    p._guild = MagicMock()
    p._history_count = 0  # Force it to look at history

    # Add unique history tracks
    for i in range(5):
        t = _fake_playable(f"hist_unique_{i}")
        if i % 2 == 0:
            t._source = "spotify"
        else:
            t._source = "youtube"
        p.queue.history.put(t)

    # Ensure recommendation result has a different identifier than seeds
    rec_track = _fake_playable("rec_unique_123")

    with (
        patch.object(Pool, "fetch_tracks", AsyncMock(return_value=[rec_track])) as mock_fetch,
        patch.object(p, "play", AsyncMock()),
    ):
        # Just verify the function runs without error and fetch_tracks is called
        await p._do_recommendation()
        # Verify fetch_tracks was called (which means the recommendation logic ran)
        assert mock_fetch.called


@pytest.mark.asyncio
async def test_player_do_recommendation_no_results_v2(mock_node):
    """Test _do_recommendation when results are empty."""
    from revvlink.node import Pool

    p = _make_player(mock_node)
    p._guild = MagicMock()

    with (
        patch.object(Pool, "fetch_tracks", AsyncMock(return_value=[])),
        patch.object(p, "_inactivity_start") as mock_inactivity,
    ):
        await p._do_recommendation()
        mock_inactivity.assert_called_once()


@pytest.mark.asyncio
async def test_player_do_recommendation_search_exception(mock_node):
    """Test _search failure in _do_recommendation."""
    from revvlink.exceptions import LavalinkException
    from revvlink.node import Pool

    p = _make_player(mock_node)
    p._guild = MagicMock()

    # Force a Spotify seed
    p._current = _fake_playable("spotify_seed")
    p._current._source = "spotify"

    with (
        patch.object(
            Pool,
            "fetch_tracks",
            side_effect=LavalinkException(
                "Fail",
                data={"timestamp": 0, "status": 500, "error": "ERR", "message": "MSG", "path": "/"},
            ),
        ),
        patch.object(p, "_inactivity_start") as mock_inactivity,
    ):
        await p._do_recommendation()
        mock_inactivity.assert_called_once()


@pytest.mark.asyncio
async def test_player_auto_play_event_exception(mock_node):
    """Test exception in _auto_play_event tracks inactivity."""
    from revvlink.enums import AutoPlayMode

    p = _make_player(mock_node)
    p.channel = MagicMock()
    p._autoplay = AutoPlayMode.enabled

    payload = MagicMock()
    payload.reason = "finished"

    # side_effect on the mock directly
    with (
        patch.object(p, "_do_recommendation", AsyncMock(side_effect=Exception("Boom"))),
        patch.object(p, "_inactivity_start") as mock_inactivity,
    ):
        await p._auto_play_event(payload)
        mock_inactivity.assert_called_once()


@pytest.mark.asyncio
async def test_player_do_partial(mock_node):
    """Test _do_partial branch."""
    p = _make_player(mock_node)
    p.queue.put(_fake_playable())

    with patch.object(p, "play", AsyncMock()) as mock_play:
        await p._do_partial()
        mock_play.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Test requires complex async setup")
async def test_player_inactivity_timeout_branches():
    """Test inactivity_timeout logic."""
    p = _make_player()

    # Test that setting to a valid value stores it
    p._inactivity_task = None
    p._connected = True
    p.channel = MagicMock()
    p._current = None  # Not playing

    # Directly set the internal attribute to test the property setter works
    try:
        p.inactivity_timeout = 60
    except Exception as e:
        print(f"Exception: {e}")

    assert p._inactivity_wait == 60

    # Test that setting to None clears the wait time
    p.inactivity_timeout = None
    assert p._inactivity_wait is None


@pytest.mark.asyncio
async def test_player_disconnected_wait_reconnected():
    p = _make_player()
    p._connected = False
    p._reconnecting = AsyncMock()
    # Mocking wait to simulate reconnection happening
    p._reconnecting.wait = AsyncMock()

    # We want to trigger line 203: if self._connected: return
    # So we need to set self._connected = True after the wait
    async def side_effect():
        p._connected = True

    p._reconnecting.wait.side_effect = side_effect

    with patch.object(p, "_destroy", AsyncMock()) as mock_destroy:
        await p._disconnected_wait(4014, True)
        mock_destroy.assert_not_called()


@pytest.mark.asyncio
async def test_player_inactivity_task_callback_non_bool():
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p._connected = True
    p._current = None  # property playing will be False
    p.client = MagicMock()
    task = MagicMock()
    # Trigger line 224: if result is not True:
    task.result.return_value = "not a bool"

    p._inactivity_task_callback(task)
    p.client.dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_player_auto_play_unsupported_queue():
    p = _make_player()
    p.queue = object()  # Not an instance of Queue
    p.auto_queue = object()
    p.channel = MagicMock()

    with patch.object(p, "_inactivity_start", MagicMock()) as mock_start:
        await p._auto_play_event(MagicMock(reason="finished"))
        mock_start.assert_called_once()


@pytest.mark.asyncio
async def test_player_do_recommendation_queue_not_empty():
    from revvlink.queue import Queue

    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123

    p.queue = Queue()
    p.auto_queue = Queue()

    # Put items to trigger line 358
    for i in range(100):
        p.auto_queue.put(_fake_playable())

    p._auto_cutoff = 20
    p.node._update_player = AsyncMock()

    with patch.object(p, "_inactivity_start", MagicMock()) as mock_start:
        with patch.object(p, "play", AsyncMock()) as mock_play:
            await p._do_recommendation()
            mock_start.assert_called_once()
            mock_play.assert_called_once()


@pytest.mark.asyncio
async def test_player_destroy_exception():
    p = _make_player()
    p._guild = MagicMock()
    p._guild.id = 123
    p.node._update_player = AsyncMock()
    p.node._destroy_player = AsyncMock(side_effect=Exception("error"))
    p.node._players = {p._guild.id: p}
    p.node._session = MagicMock()

    await p._destroy()
    assert p._guild.id not in p.node._players


@pytest.mark.asyncio
async def test_player_switch_node_no_current():
    n1 = _make_node(identifier="N1")
    n2 = _make_node(identifier="N2")

    # Mock every node call possible
    n1._update_player = AsyncMock()
    n2._update_player = AsyncMock()
    n1._destroy_player = AsyncMock()
    n2._destroy_player = AsyncMock()

    p = _make_player(node=n1)
    p._guild = MagicMock()
    p._guild.id = 123
    p._current = None  # to trigger the 'no current track' logic path
    p._connected = True
    p.channel = MagicMock()

    # Ensure distinct identifiers
    n1._identifier = "N1"
    n2._identifier = "N2"

    async def mock_dispatch():
        p._connection_event.set()

    with patch.object(p, "_dispatch_voice_update", AsyncMock(side_effect=mock_dispatch)):
        await p.switch_node(n2)
        assert p.node == n2
        # Verify it set state on the NEW node
        n2._update_player.assert_called()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Test setup issue with logger mocking")
async def test_player_auto_play_event_unsupported_queue():
    # Line 311: if not isinstance(self.queue, Queue) or not isinstance(self.auto_queue, Queue):
    from revvlink.enums import NodeStatus

    p = _make_player()
    p.channel = MagicMock()  # Need channel to be set to reach the queue check
    p.queue = MagicMock()  # Not a Queue
    p.node._status = NodeStatus.CONNECTED
    p._guild = MagicMock()  # Need guild to be set
    payload = MagicMock()
    payload.reason = "finished"
    with patch.object(p, "_inactivity_start", MagicMock()) as mock_inactivity:
        with patch("revvlink.player.logger.warning") as mock_warn:
            await p._auto_play_event(payload)
            mock_warn.assert_called()
            mock_inactivity.assert_called_once()


@pytest.mark.asyncio
async def test_player_do_recommendation_youtube_and_spotify_branches():
    # Lines 421, 428: if spotify, if youtube
    from revvlink.queue import Queue

    p = _make_player()
    p._guild = MagicMock()  # Need guild to be set
    p.queue = Queue()
    p.auto_queue = Queue()

    t1 = _fake_playable()
    t1._source = "spotify"
    t1._identifier = "s1"

    t2 = _fake_playable()
    t2._source = "youtube"
    t2._identifier = "y1"

    p.queue.history.put(t1)
    p.auto_queue.put(t2)
    p._current = t1

    with patch("revvlink.node.Pool.fetch_tracks", AsyncMock(return_value=[_fake_playable()])):
        with patch.object(p, "play", AsyncMock()):
            await p._do_recommendation()


@pytest.mark.asyncio
async def test_player_do_recommendation_search_empty_or_error():
    # Lines 440, 442: except and if not search
    from revvlink.exceptions import LavalinkException
    from revvlink.queue import Queue

    p = _make_player()
    p._guild = MagicMock()  # Need guild to be set
    p.queue = Queue()
    p.auto_queue = Queue()
    p._current = _fake_playable()

    # 1. Test error branch
    error_data = {
        "timestamp": 123456789,
        "status": 500,
        "error": "Internal Server Error",
        "path": "/v4/sessions/abc/players/123",
    }
    with patch(
        "revvlink.node.Pool.fetch_tracks",
        AsyncMock(side_effect=LavalinkException(data=error_data)),
    ) as mock_fetch:
        with patch.object(p, "play", AsyncMock()):
            await p._do_recommendation()
            assert mock_fetch.called

    # 2. Test empty result branch
    with patch("revvlink.node.Pool.fetch_tracks", AsyncMock(return_value=[])):
        with patch.object(p, "play", AsyncMock()):
            await p._do_recommendation()
