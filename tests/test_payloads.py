import datetime
from typing import Any

from revvlink.enums import DiscordVoiceCloseType
from revvlink.filters import Filters
from revvlink.payloads import (
    ExtraEventPayload,
    GitResponsePayload,
    InfoResponsePayload,
    NodeReadyEventPayload,
    PlayerResponsePayload,
    PlayerStatePayload,
    PlayerUpdateEventPayload,
    PluginResponsePayload,
    StatsEventPayload,
    StatsResponsePayload,
    TrackEndEventPayload,
    TrackExceptionEventPayload,
    TrackStartEventPayload,
    TrackStuckEventPayload,
    VersionResponsePayload,
    VoiceStatePayload,
    WebsocketClosedEventPayload,
)
from revvlink.tracks import Playable


def _make_player_state():
    return {"time": 1600000000000, "position": 5000, "connected": True, "ping": 50}


def test_git_response_payload():
    payload = {"branch": "master", "commit": "abcdef", "commitTime": 1600000000000}
    git = GitResponsePayload(payload)
    assert git.branch == "master"
    assert git.commit == "abcdef"
    assert git.commit_time.tzinfo == datetime.timezone.utc


def test_version_response_payload():
    payload = {
        "semver": "3.7.0",
        "major": 3,
        "minor": 7,
        "patch": 0,
        "preRelease": "rc1",
        "build": "123",
    }
    version = VersionResponsePayload(payload)
    assert version.semver == "3.7.0"
    assert version.major == 3
    assert version.pre_release == "rc1"
    assert version.build == "123"


def test_plugin_response_payload():
    payload = {"name": "lavasrc", "version": "4.0.0"}
    plugin = PluginResponsePayload(payload)
    assert plugin.name == "lavasrc"
    assert plugin.version == "4.0.0"


def test_info_response_payload():
    payload = {
        "version": {"semver": "3.7.0", "major": 3, "minor": 7, "patch": 0},
        "buildTime": 1600000000000,
        "git": {"branch": "master", "commit": "abcdef", "commitTime": 1600000000000},
        "jvm": "11.0.12",
        "lavaplayer": "2.1.2",
        "sourceManagers": ["youtube", "twitch"],
        "filters": ["volume", "equalizer"],
        "plugins": [{"name": "lavasrc", "version": "4.0.0"}],
    }
    info = InfoResponsePayload(payload)
    assert info.jvm == "11.0.12"
    assert len(info.plugins) == 1


def test_stats_event_payload_with_frames():
    payload = {
        "players": 1,
        "playingPlayers": 1,
        "uptime": 60000,
        "memory": {"free": 1024, "used": 2048, "allocated": 4096, "reservable": 8192},
        "cpu": {"cores": 4, "systemLoad": 0.5, "lavalinkLoad": 0.1},
        "frameStats": {"sent": 100, "nulled": 0, "deficit": 0},
    }
    stats = StatsEventPayload(payload)
    assert stats.players == 1
    assert stats.frames is not None
    assert stats.frames.sent == 100
    assert stats.cpu.cores == 4
    assert stats.memory.free == 1024


def test_stats_event_payload_no_frames():
    payload = {
        "players": 2,
        "playingPlayers": 1,
        "uptime": 90000,
        "memory": {"free": 1024, "used": 2048, "allocated": 4096, "reservable": 8192},
        "cpu": {"cores": 8, "systemLoad": 0.3, "lavalinkLoad": 0.05},
    }
    stats = StatsEventPayload(payload)
    assert stats.frames is None


def test_stats_response_payload():
    payload = {
        "players": 1,
        "playingPlayers": 1,
        "uptime": 60000,
        "memory": {"free": 1024, "used": 2048, "allocated": 4096, "reservable": 8192},
        "cpu": {"cores": 4, "systemLoad": 0.5, "lavalinkLoad": 0.1},
        "frameStats": {"sent": 50, "nulled": 0, "deficit": 0},
    }
    stats = StatsResponsePayload(payload)
    assert stats.players == 1
    assert stats.frames is not None

    # No frames version
    payload_no_frames = dict(payload)
    del payload_no_frames["frameStats"]
    stats2 = StatsResponsePayload(payload_no_frames)
    assert stats2.frames is None


def test_player_state_payload():
    payload = _make_player_state()
    state = PlayerStatePayload(payload)
    assert state.position == 5000
    assert state.connected is True
    assert state.ping == 50


def test_voice_state_payload():
    payload = {"token": "abc", "endpoint": "discord.gg", "sessionId": "def"}
    vs = VoiceStatePayload(payload)
    assert vs.token == "abc"
    assert vs.endpoint == "discord.gg"
    assert vs.session_id == "def"

    # Empty
    vs2 = VoiceStatePayload({})
    assert vs2.token is None
    assert vs2.endpoint is None
    assert vs2.session_id is None


def test_player_response_payload(dummy_track_payload: dict[str, Any]):
    payload = {
        "guildId": "123456789",
        "track": dummy_track_payload,
        "volume": 100,
        "paused": False,
        "state": _make_player_state(),
        "voice": {"token": "abc", "endpoint": "discord.gg", "sessionId": "def"},
        "filters": {},
    }
    player_res = PlayerResponsePayload(payload)
    assert player_res.guild_id == 123456789
    assert player_res.track is not None
    assert isinstance(player_res.filters, Filters)


def test_player_response_payload_no_track():
    payload = {
        "guildId": "987654321",
        "volume": 100,
        "paused": True,
        "state": _make_player_state(),
        "voice": {},
        "filters": {},
    }
    player_res = PlayerResponsePayload(payload)
    assert player_res.track is None
    assert player_res.paused is True


def test_node_ready_event_payload():
    from unittest.mock import MagicMock

    node = MagicMock()
    payload = NodeReadyEventPayload(node=node, resumed=True, session_id="session_123")
    assert payload.resumed is True
    assert payload.session_id == "session_123"


def test_track_start_event_payload(dummy_track_payload: dict[str, Any]):
    track = Playable(dummy_track_payload)

    # No player path
    payload = TrackStartEventPayload(player=None, track=track)
    assert payload.player is None
    assert payload.original is None

    # With player mock
    from unittest.mock import MagicMock

    player = MagicMock()
    player._original = track
    payload2 = TrackStartEventPayload(player=player, track=track)
    assert payload2.original == track


def test_track_end_event_payload(dummy_track_payload: dict[str, Any]):
    track = Playable(dummy_track_payload)

    payload = TrackEndEventPayload(player=None, track=track, reason="finished")
    assert payload.reason == "finished"
    assert payload.original is None

    from unittest.mock import MagicMock

    player = MagicMock()
    player._previous = track
    payload2 = TrackEndEventPayload(player=player, track=track, reason="stopped")
    assert payload2.original == track


def test_track_exception_event_payload(dummy_track_payload: dict[str, Any]):
    track = Playable(dummy_track_payload)
    exception_data = {"message": "oops", "severity": "COMMON", "cause": "issue"}
    payload = TrackExceptionEventPayload(player=None, track=track, exception=exception_data)  # type: ignore
    assert payload.exception == exception_data


def test_track_stuck_event_payload(dummy_track_payload: dict[str, Any]):
    track = Playable(dummy_track_payload)
    payload = TrackStuckEventPayload(player=None, track=track, threshold=5000)
    assert payload.threshold == 5000


def test_websocket_closed_event_payload():
    payload = WebsocketClosedEventPayload(
        player=None, code=4001, reason="Unknown opcode", by_remote=True
    )
    assert payload.code == DiscordVoiceCloseType.UNKNOWN_OPCODE
    assert payload.reason == "Unknown opcode"
    assert payload.by_remote is True


def test_player_update_event_payload():
    state = _make_player_state()
    payload = PlayerUpdateEventPayload(player=None, state=state)
    assert payload.position == 5000
    assert payload.connected is True
    assert payload.ping == 50
    assert payload.time == 1600000000000


def test_extra_event_payload():
    from unittest.mock import MagicMock

    node = MagicMock()
    extra_data = {"type": "CustomEvent", "guildId": "123"}
    payload = ExtraEventPayload(node=node, player=None, data=extra_data)
    assert payload.data == extra_data
    assert payload.player is None
