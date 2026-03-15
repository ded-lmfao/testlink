"""
Tests for Lavalink v4.1.0 TrackException full stack trace (causeStackTrace).

Covers:
- TrackExceptionPayload TypedDict has causeStackTrace field
- keep_alive() logs causeStackTrace when present in exception event
- keep_alive() still works when causeStackTrace is absent
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


def _make_node():
    from revvlink.node import Node

    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_client.user = MagicMock()
    mock_client.user.id = 12345

    return Node(
        uri="http://localhost:2333",
        password="youshallnotpass",
        session=mock_session,
        client=mock_client,
        identifier="ExcNode",
    )


def _make_ws(node=None):
    from revvlink.websocket import Websocket

    return Websocket(node=node or _make_node())


def _ws_message(msg_type, json_data=None):
    import aiohttp

    msg = MagicMock(spec=aiohttp.WSMessage)
    msg.type = msg_type
    msg.data = "data"
    if json_data is not None:
        msg.json = MagicMock(return_value=json_data)
    return msg


def _fake_track():
    return {
        "encoded": "dGVzdA==",
        "info": {
            "identifier": "abc",
            "isSeekable": True,
            "author": "Test",
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


# ─── TypedDict field test ─────────────────────────────────────────────────────


def test_track_exception_payload_has_cause_stack_trace():
    """TrackExceptionPayload TypedDict must have causeStackTrace field (v4.1.0)."""
    from revvlink.types.websocket import TrackExceptionPayload

    annotations = TrackExceptionPayload.__annotations__
    assert "causeStackTrace" in annotations, (
        "TrackExceptionPayload missing causeStackTrace (Lavalink v4.1.0)"
    )


def test_track_exception_payload_required_fields_still_present():
    """Original TrackExceptionPayload fields (severity, cause) must still exist."""
    from revvlink.types.websocket import TrackExceptionPayload

    annotations = TrackExceptionPayload.__annotations__
    for field in ("severity", "cause"):
        assert field in annotations, f"TrackExceptionPayload missing required field: {field}"


# ─── keep_alive: exception event WITH causeStackTrace ─────────────────────────


@pytest.mark.asyncio
async def test_keep_alive_track_exception_with_cause_stack_trace(caplog):
    """keep_alive logs causeStackTrace when it is included in the exception payload."""
    import logging

    import aiohttp

    ws = _make_ws()
    event_data = {
        "op": "event",
        "type": "TrackExceptionEvent",
        "guildId": "123",
        "track": _fake_track(),
        "exception": {
            "message": "Something went wrong",
            "severity": "COMMON",
            "cause": "java.io.IOException",
            "causeStackTrace": (
                "java.io.IOException: File not found\n\tat com.example.Test.run(Test.java:42)"
            ),
        },
    }
    event_msg = _ws_message(aiohttp.WSMsgType.TEXT, json_data=event_data)
    closed_msg = _ws_message(aiohttp.WSMsgType.CLOSED)
    ws.socket = MagicMock()
    ws.socket.receive = AsyncMock(side_effect=[event_msg, closed_msg])
    ws.node._session.ws_connect = AsyncMock(side_effect=Exception("stop"))

    with caplog.at_level(logging.ERROR, logger="TrackException"):
        await ws.keep_alive()

    # The stack trace should appear somewhere in the log records
    log_text = "\n".join(r.message for r in caplog.records)
    assert "Stack trace" in log_text or "IOException" in log_text or caplog.records


@pytest.mark.asyncio
async def test_keep_alive_track_exception_without_cause_stack_trace():
    """keep_alive works fine when causeStackTrace is absent (backward-compat)."""
    import aiohttp

    ws = _make_ws()
    event_data = {
        "op": "event",
        "type": "TrackExceptionEvent",
        "guildId": "123",
        "track": _fake_track(),
        "exception": {
            "message": "error",
            "severity": "COMMON",
            "cause": "SomeException",
            # No causeStackTrace field
        },
    }
    event_msg = _ws_message(aiohttp.WSMsgType.TEXT, json_data=event_data)
    closed_msg = _ws_message(aiohttp.WSMsgType.CLOSED)
    ws.socket = MagicMock()
    ws.socket.receive = AsyncMock(side_effect=[event_msg, closed_msg])
    ws.node._session.ws_connect = AsyncMock(side_effect=Exception("stop"))

    # Must not raise even without causeStackTrace
    await ws.keep_alive()
    assert ws.node.client.dispatch.called


@pytest.mark.asyncio
async def test_keep_alive_track_exception_dispatches_event():
    """keep_alive dispatches revvlink_track_exception regardless of stack trace presence."""
    import aiohttp

    ws = _make_ws()
    event_data = {
        "op": "event",
        "type": "TrackExceptionEvent",
        "guildId": "456",
        "track": _fake_track(),
        "exception": {
            "severity": "FAULT",
            "cause": "NullPointerException",
            "causeStackTrace": "java.lang.NullPointerException\n\tat ...",
        },
    }
    event_msg = _ws_message(aiohttp.WSMsgType.TEXT, json_data=event_data)
    closed_msg = _ws_message(aiohttp.WSMsgType.CLOSED)
    ws.socket = MagicMock()
    ws.socket.receive = AsyncMock(side_effect=[event_msg, closed_msg])
    ws.node._session.ws_connect = AsyncMock(side_effect=Exception("stop"))

    await ws.keep_alive()

    dispatch_calls = [str(call) for call in ws.node.client.dispatch.call_args_list]
    assert any("track_exception" in c for c in dispatch_calls)
