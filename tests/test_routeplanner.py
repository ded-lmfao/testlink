"""
Tests for RoutePlanner API methods on Node — Lavalink v4 REST API.

Covers:
- get_routeplanner_status() returns None when Lavalink returns 204 (disabled)
- get_routeplanner_status() returns dict when Lavalink returns 200 JSON
- get_routeplanner_status() raises LavalinkException on error
- unmark_failed_address() succeeds (204 No Content)
- unmark_failed_address() raises LavalinkException on error
- unmark_all_failed_addresses() succeeds (204 No Content)
- unmark_all_failed_addresses() raises LavalinkException on error
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
    if json_val is not None:
        resp.json = AsyncMock(return_value=json_val)
    else:
        resp.json = AsyncMock(side_effect=Exception("no body"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, resp


def _make_async_ctx_no_body(status: int):
    """Helper for responses with no body (e.g. 204 No Content)."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(side_effect=Exception("no body"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, resp


# ─── Sample RoutePlanner payloads ─────────────────────────────────────────────


_NANO_IP_ROUTEPLANNER_STATUS = {
    "class": "NanoIpRoutePlanner",
    "details": {
        "ipBlock": {
            "type": "Inet6Address",
            "size": "1208925819614629174706176",
        },
        "failingAddresses": [
            {
                "failingAddress": "1.0.0.1",
                "failingTimestamp": 1573520770002,
                "failingTime": "Mon Oct 28 12:00:00 CET 2019",
            }
        ],
        "blockIndex": "0",
        "currentAddressIndex": "37911",
    },
}

_ROTATING_NANO_ROUTEPLANNER_STATUS = {
    "class": "RotatingNanoIpRoutePlanner",
    "details": {
        "ipBlock": {"type": "Inet6Address", "size": "1208925819614629174706176"},
        "failingAddresses": [],
        "blockIndex": "0",
        "currentAddressIndex": "0",
    },
}


# ─── get_routeplanner_status() ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_routeplanner_status_returns_none_when_disabled():
    """Returns None when Lavalink responds 204 (RoutePlanner not configured)."""
    node = _make_node_with_client(identifier="RoutePlannerDisabled")
    ctx, _ = _make_async_ctx_no_body(status=204)
    node._session.get.return_value = ctx

    result = await node.get_routeplanner_status()

    assert result is None


@pytest.mark.asyncio
async def test_get_routeplanner_status_returns_dict_on_success():
    """Returns the JSON dict when Lavalink responds 200."""
    node = _make_node_with_client(identifier="RoutePlannerActive")
    ctx, _ = _make_async_ctx(status=200, json_val=_NANO_IP_ROUTEPLANNER_STATUS)
    node._session.get.return_value = ctx

    result = await node.get_routeplanner_status()

    assert result is not None
    assert isinstance(result, dict)
    assert result["class"] == "NanoIpRoutePlanner"
    assert "details" in result


@pytest.mark.asyncio
async def test_get_routeplanner_status_returns_rotating_nano_variant():
    """Returns dict correctly for RotatingNanoIpRoutePlanner."""
    node = _make_node_with_client(identifier="RotatingNano")
    ctx, _ = _make_async_ctx(status=200, json_val=_ROTATING_NANO_ROUTEPLANNER_STATUS)
    node._session.get.return_value = ctx

    result = await node.get_routeplanner_status()

    assert result is not None
    assert result["class"] == "RotatingNanoIpRoutePlanner"
    assert result["details"]["failingAddresses"] == []


@pytest.mark.asyncio
async def test_get_routeplanner_status_calls_correct_url():
    """get_routeplanner_status hits GET /v4/routeplanner/status."""
    node = _make_node_with_client(identifier="RoutePlannerURL")
    ctx, _ = _make_async_ctx_no_body(status=204)
    node._session.get.return_value = ctx

    await node.get_routeplanner_status()

    call_kwargs = node._session.get.call_args
    url = call_kwargs.kwargs.get("url", "")
    assert "/v4/routeplanner/status" in url


@pytest.mark.asyncio
async def test_get_routeplanner_status_raises_on_error():
    """get_routeplanner_status raises LavalinkException on error status."""
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client(identifier="RoutePlannerStatusErr")
    err_data = {
        "timestamp": 1000,
        "status": 500,
        "error": "Internal Server Error",
        "path": "/v4/routeplanner/status",
    }
    ctx, _ = _make_async_ctx(status=500, json_val=err_data)
    node._session.get.return_value = ctx

    with pytest.raises(LavalinkException) as exc_info:
        await node.get_routeplanner_status()
    assert exc_info.value.status == 500


@pytest.mark.asyncio
async def test_get_routeplanner_status_raises_node_exception_when_json_fails():
    """get_routeplanner_status raises NodeException when error JSON parse fails."""
    from revvlink.exceptions import NodeException

    node = _make_node_with_client(identifier="RoutePlannerStatusNoJson")
    resp = AsyncMock()
    resp.status = 503
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    node._session.get.return_value = ctx

    with pytest.raises(NodeException) as exc_info:
        await node.get_routeplanner_status()
    assert exc_info.value.status == 503


# ─── unmark_failed_address() ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unmark_failed_address_succeeds_on_204():
    """unmark_failed_address returns None when Lavalink responds 204."""
    node = _make_node_with_client(identifier="UnmarkAddr")
    ctx, _ = _make_async_ctx_no_body(status=204)
    node._session.post.return_value = ctx

    result = await node.unmark_failed_address("1.2.3.4")

    assert result is None


@pytest.mark.asyncio
async def test_unmark_failed_address_calls_correct_url():
    """unmark_failed_address hits POST /v4/routeplanner/free/address."""
    node = _make_node_with_client(identifier="UnmarkAddrURL")
    ctx, _ = _make_async_ctx_no_body(status=204)
    node._session.post.return_value = ctx

    await node.unmark_failed_address("1.2.3.4")

    call_kwargs = node._session.post.call_args
    url = call_kwargs.kwargs.get("url", "")
    assert "/v4/routeplanner/free/address" in url


@pytest.mark.asyncio
async def test_unmark_failed_address_sends_address_in_body():
    """unmark_failed_address sends the address in the JSON body."""
    node = _make_node_with_client(identifier="UnmarkAddrBody")
    ctx, _ = _make_async_ctx_no_body(status=204)
    node._session.post.return_value = ctx

    await node.unmark_failed_address("10.0.0.1")

    call_kwargs = node._session.post.call_args
    body = call_kwargs.kwargs.get("json", {})
    assert body.get("address") == "10.0.0.1"


@pytest.mark.asyncio
async def test_unmark_failed_address_raises_on_error():
    """unmark_failed_address raises LavalinkException on error status."""
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client(identifier="UnmarkAddrErr")
    err_data = {
        "timestamp": 1000,
        "status": 400,
        "error": "Bad Request",
        "path": "/v4/routeplanner/free/address",
    }
    ctx, _ = _make_async_ctx(status=400, json_val=err_data)
    node._session.post.return_value = ctx

    with pytest.raises(LavalinkException) as exc_info:
        await node.unmark_failed_address("bad_address")
    assert exc_info.value.status == 400


@pytest.mark.asyncio
async def test_unmark_failed_address_raises_node_exception_when_json_fails():
    """unmark_failed_address raises NodeException when error JSON parse fails."""
    from revvlink.exceptions import NodeException

    node = _make_node_with_client(identifier="UnmarkAddrNoJson")
    resp = AsyncMock()
    resp.status = 500
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    node._session.post.return_value = ctx

    with pytest.raises(NodeException) as exc_info:
        await node.unmark_failed_address("1.2.3.4")
    assert exc_info.value.status == 500


# ─── unmark_all_failed_addresses() ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_unmark_all_failed_addresses_succeeds_on_204():
    """unmark_all_failed_addresses returns None when Lavalink responds 204."""
    node = _make_node_with_client(identifier="UnmarkAll")
    ctx, _ = _make_async_ctx_no_body(status=204)
    node._session.post.return_value = ctx

    result = await node.unmark_all_failed_addresses()

    assert result is None


@pytest.mark.asyncio
async def test_unmark_all_failed_addresses_calls_correct_url():
    """unmark_all_failed_addresses hits POST /v4/routeplanner/free/all."""
    node = _make_node_with_client(identifier="UnmarkAllURL")
    ctx, _ = _make_async_ctx_no_body(status=204)
    node._session.post.return_value = ctx

    await node.unmark_all_failed_addresses()

    call_kwargs = node._session.post.call_args
    url = call_kwargs.kwargs.get("url", "")
    assert "/v4/routeplanner/free/all" in url


@pytest.mark.asyncio
async def test_unmark_all_failed_addresses_sends_no_body():
    """unmark_all_failed_addresses sends an empty body (or no JSON body)."""
    node = _make_node_with_client(identifier="UnmarkAllBody")
    ctx, _ = _make_async_ctx_no_body(status=204)
    node._session.post.return_value = ctx

    await node.unmark_all_failed_addresses()

    call_kwargs = node._session.post.call_args
    # Either json=None or json={} is acceptable; it must NOT send an address
    body = call_kwargs.kwargs.get("json", {})
    assert "address" not in (body or {})


@pytest.mark.asyncio
async def test_unmark_all_failed_addresses_raises_on_error():
    """unmark_all_failed_addresses raises LavalinkException on error status."""
    from revvlink.exceptions import LavalinkException

    node = _make_node_with_client(identifier="UnmarkAllErr")
    err_data = {
        "timestamp": 1000,
        "status": 500,
        "error": "Internal Server Error",
        "path": "/v4/routeplanner/free/all",
    }
    ctx, _ = _make_async_ctx(status=500, json_val=err_data)
    node._session.post.return_value = ctx

    with pytest.raises(LavalinkException) as exc_info:
        await node.unmark_all_failed_addresses()
    assert exc_info.value.status == 500


@pytest.mark.asyncio
async def test_unmark_all_failed_addresses_raises_node_exception_when_json_fails():
    """unmark_all_failed_addresses raises NodeException on non-JSON error body."""
    from revvlink.exceptions import NodeException

    node = _make_node_with_client(identifier="UnmarkAllNoJson")
    resp = AsyncMock()
    resp.status = 503
    resp.json = AsyncMock(side_effect=Exception("not json"))
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    node._session.post.return_value = ctx

    with pytest.raises(NodeException) as exc_info:
        await node.unmark_all_failed_addresses()
    assert exc_info.value.status == 503


# ─── Integration: correct HTTP verbs ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_routeplanner_uses_get_for_status_and_post_for_free():
    """RoutePlanner status uses GET; unmark methods use POST."""
    node = _make_node_with_client(identifier="RoutePlannerVerbs")

    ctx_get, _ = _make_async_ctx_no_body(status=204)
    node._session.get.return_value = ctx_get
    await node.get_routeplanner_status()
    assert node._session.get.called
    assert not node._session.post.called

    node._session.reset_mock()

    ctx_post, _ = _make_async_ctx_no_body(status=204)
    node._session.post.return_value = ctx_post
    await node.unmark_failed_address("1.2.3.4")
    assert node._session.post.called
    assert not node._session.get.called

    node._session.reset_mock()

    ctx_post2, _ = _make_async_ctx_no_body(status=204)
    node._session.post.return_value = ctx_post2
    await node.unmark_all_failed_addresses()
    assert node._session.post.called
    assert not node._session.get.called
