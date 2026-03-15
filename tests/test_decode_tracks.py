"""
Tests for Node.decode_track() and Node.decode_tracks() — Lavalink v4 REST API.

Covers:
- _decode_track() calls GET /v4/decodetrack with encodedTrack param
- decode_track() returns a Playable from a base64 encoded string
- _decode_tracks() calls POST /v4/decodetracks with a list payload
- decode_tracks() returns a list[Playable]
- Both methods raise LavalinkException on error responses
- Both methods raise NodeException when JSON parse fails
"""

from __future__ import annotations

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


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_node_with_client(**kwargs):
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


def _make_async_ctx(status: int, json_val=None):
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_val)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, resp


def _fake_track_payload(identifier="abc123", title="Test Track"):
    return {
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
            "title": title,
            "artworkUrl": None,
            "isrc": None,
        },
        "pluginInfo": {},
        "userData": {},
    }


ENCODED_TRACK = "QAAAjwIAJVJpY2sgQXN0bGV5IC0gTmV2ZXIgR29ubmEgR2l2ZSBZb3UgVXA="


# ─── _decode_track() raw tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_decode_track_calls_correct_endpoint():
    """_decode_track hits GET /v4/decodetrack with correct params."""
    node = _make_node_with_client(identifier="DecodeTrack1")
    payload = _fake_track_payload()
    ctx, _resp = _make_async_ctx(status=200, json_val=payload)
    node._session.get.return_value = ctx

    result = await node._decode_track(ENCODED_TRACK)

    # Verify the URL used
    call_kwargs = node._session.get.call_args
    assert "/v4/decodetrack" in call_kwargs.kwargs.get("url", "")
    params = call_kwargs.kwargs.get("params", {})
    assert params.get("encodedTrack") == ENCODED_TRACK

    assert result["info"]["identifier"] == "abc123"


@pytest.mark.asyncio
async def test_decode_track_raises_lavalink_exception_on_error():
    """_decode_track raises LavalinkException on >= 300 with JSON body."""
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client(identifier="DecodeTrackErr")
    err_data = {"timestamp": 1000, "status": 400, "error": "Bad Request", "path": "/v4/decodetrack"}
    ctx, _resp = _make_async_ctx(status=400, json_val=err_data)
    node._session.get.return_value = ctx

    with pytest.raises(LavalinkException) as exc_info:
        await node._decode_track("invalid_encoded")
    assert exc_info.value.status == 400


@pytest.mark.asyncio
async def test_decode_track_raises_node_exception_on_json_fail():
    """_decode_track raises NodeException when JSON parse fails on error."""
    from revvlink.exceptions import NodeException

    node = _make_node_with_client(identifier="DecodeTrackNoJson")
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    node._session.get.return_value = ctx

    with pytest.raises(NodeException) as exc_info:
        await node._decode_track("some_encoded")
    assert exc_info.value.status == 500


# ─── decode_track() public API ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_decode_track_returns_playable():
    """decode_track() returns a Playable instance."""
    from revvlink.tracks import Playable

    node = _make_node_with_client(identifier="DecodeTrackPublic")
    payload = _fake_track_payload(identifier="rick_roll", title="Never Gonna Give You Up")
    ctx, _resp = _make_async_ctx(status=200, json_val=payload)
    node._session.get.return_value = ctx

    result = await node.decode_track(ENCODED_TRACK)

    assert isinstance(result, Playable)
    assert result.identifier == "rick_roll"
    assert result.title == "Never Gonna Give You Up"


@pytest.mark.asyncio
async def test_decode_track_propagates_lavalink_exception():
    """decode_track() propagates LavalinkException from _decode_track."""
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client(identifier="DecodeTrackPublicErr")
    err_data = {"timestamp": 1000, "status": 404, "error": "Not Found", "path": "/v4/decodetrack"}
    ctx, _resp = _make_async_ctx(status=404, json_val=err_data)
    node._session.get.return_value = ctx

    with pytest.raises(LavalinkException):
        await node.decode_track("nonexistent_encoded")


# ─── _decode_tracks() raw tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_decode_tracks_calls_correct_endpoint():
    """_decode_tracks hits POST /v4/decodetracks with list body."""
    node = _make_node_with_client(identifier="DecodeTracks1")
    payload = [_fake_track_payload("id_1", "Track 1"), _fake_track_payload("id_2", "Track 2")]
    ctx, _resp = _make_async_ctx(status=200, json_val=payload)
    node._session.post.return_value = ctx

    encoded_list = [ENCODED_TRACK, ENCODED_TRACK]
    result = await node._decode_tracks(encoded_list)

    # Verify POST was called to the correct URL
    call_kwargs = node._session.post.call_args
    assert "/v4/decodetracks" in call_kwargs.kwargs.get("url", "")
    body = call_kwargs.kwargs.get("json", [])
    assert body == encoded_list

    assert len(result) == 2
    assert result[0]["info"]["identifier"] == "id_1"
    assert result[1]["info"]["identifier"] == "id_2"


@pytest.mark.asyncio
async def test_decode_tracks_raises_lavalink_exception_on_error():
    """_decode_tracks raises LavalinkException on >= 300."""
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client(identifier="DecodeTracksErr")
    err_data = {
        "timestamp": 1000,
        "status": 400,
        "error": "Bad Request",
        "path": "/v4/decodetracks",
    }
    ctx, _resp = _make_async_ctx(status=400, json_val=err_data)
    node._session.post.return_value = ctx

    with pytest.raises(LavalinkException):
        await node._decode_tracks(["bad_encoded"])


@pytest.mark.asyncio
async def test_decode_tracks_raises_node_exception_when_json_fails():
    """_decode_tracks raises NodeException when error response JSON fails to parse."""
    from revvlink.exceptions import NodeException

    node = _make_node_with_client(identifier="DecodeTracksNoJson")
    resp = AsyncMock()
    resp.status = 503
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    node._session.post.return_value = ctx

    with pytest.raises(NodeException) as exc_info:
        await node._decode_tracks(["some_encoded"])
    assert exc_info.value.status == 503


# ─── decode_tracks() public API ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_decode_tracks_returns_list_of_playable():
    """decode_tracks() returns list[Playable]."""
    from revvlink.tracks import Playable

    node = _make_node_with_client(identifier="DecodeTracksPublic")
    payloads = [
        _fake_track_payload("track_a", "Song A"),
        _fake_track_payload("track_b", "Song B"),
        _fake_track_payload("track_c", "Song C"),
    ]
    ctx, _resp = _make_async_ctx(status=200, json_val=payloads)
    node._session.post.return_value = ctx

    results = await node.decode_tracks([ENCODED_TRACK, ENCODED_TRACK, ENCODED_TRACK])

    assert len(results) == 3
    assert all(isinstance(r, Playable) for r in results)
    assert results[0].identifier == "track_a"
    assert results[1].title == "Song B"
    assert results[2].identifier == "track_c"


@pytest.mark.asyncio
async def test_decode_tracks_returns_empty_list():
    """decode_tracks() handles an empty response list."""
    node = _make_node_with_client(identifier="DecodeTracksEmpty")
    ctx, _resp = _make_async_ctx(status=200, json_val=[])
    node._session.post.return_value = ctx

    results = await node.decode_tracks([])

    assert results == []


@pytest.mark.asyncio
async def test_decode_tracks_propagates_lavalink_exception():
    """decode_tracks() propagates LavalinkException from _decode_tracks."""
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client(identifier="DecodeTracksPublicErr")
    err_data = {
        "timestamp": 1000,
        "status": 400,
        "error": "Bad Request",
        "path": "/v4/decodetracks",
    }
    ctx, _resp = _make_async_ctx(status=400, json_val=err_data)
    node._session.post.return_value = ctx

    with pytest.raises(LavalinkException):
        await node.decode_tracks(["bad"])


@pytest.mark.asyncio
async def test_decode_track_single_vs_batch():
    """decode_track and decode_tracks use different HTTP methods (GET vs POST)."""
    node = _make_node_with_client(identifier="DecodeBothMethods")

    single_payload = _fake_track_payload("single")
    ctx_get, _ = _make_async_ctx(status=200, json_val=single_payload)
    node._session.get.return_value = ctx_get

    await node.decode_track(ENCODED_TRACK)
    assert node._session.get.called
    assert not node._session.post.called  # POST not used for single decode

    # Reset mocks
    node._session.reset_mock()

    batch_payload = [_fake_track_payload("batch1"), _fake_track_payload("batch2")]
    ctx_post, _ = _make_async_ctx(status=200, json_val=batch_payload)
    node._session.post.return_value = ctx_post

    await node.decode_tracks([ENCODED_TRACK, ENCODED_TRACK])
    assert node._session.post.called
    assert not node._session.get.called  # GET not used for batch decode
