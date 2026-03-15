"""
MIT License

Copyright (c) 2026-Present @JustNixx and @IamGroot

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, cast

import aiohttp

from . import __version__
from .backoff import Backoff
from .enums import NodeStatus
from .exceptions import AuthorizationFailedException, NodeException
from .logger import revv_logger
from .payloads import (
    ExtraEventPayload,
    NodeDisconnectedEventPayload,
    NodeReadyEventPayload,
    PlayerUpdateEventPayload,
    StatsEventPayload,
    TrackEndEventPayload,
    TrackExceptionEventPayload,
    TrackStartEventPayload,
    TrackStuckEventPayload,
    WebsocketClosedEventPayload,
)
from .tracks import Playable

if TYPE_CHECKING:
    from .node import Node
    from .player import Player
    from .types.request import UpdateSessionRequest
    from .types.response import InfoResponse
    from .types.state import PlayerState
    from .types.websocket import (
        DAVEPrepareTransitionEvent,
        DAVEProtocolChangeEvent,
        PlayerUpdateOP,
        ReadyOP,
        StatsOP,
        TrackEndEvent,
        TrackExceptionEvent,
        TrackExceptionPayload,
        TrackStartEvent,
        TrackStuckEvent,
        WebsocketClosedEvent,
        WebsocketOP,
    )


logger: logging.Logger = logging.getLogger(__name__)
LOGGER_TRACK: logging.Logger = logging.getLogger("TrackException")


class Websocket:
    def __init__(self, *, node: Node) -> None:
        self.node = node

        self.backoff: Backoff = Backoff()

        self.socket: aiohttp.ClientWebSocketResponse | None = None
        self.keep_alive_task: asyncio.Task[None] | None = None
        self._tasks: set[asyncio.Task[Any]] = set()

    @property
    def headers(self) -> dict[str, str]:
        assert self.node.client is not None
        assert self.node.client.user is not None

        data = {
            "Authorization": self.node.password,
            "User-Id": str(self.node.client.user.id),
            "Client-Name": f"RevvLink/{__version__}",
        }

        if self.node.session_id:
            data["Session-Id"] = self.node.session_id

        return data

    def is_connected(self) -> bool:
        return self.socket is not None and not self.socket.closed

    async def _update_node(self) -> None:
        if self.node._resume_timeout > 0:
            udata: UpdateSessionRequest = {"resuming": True, "timeout": self.node._resume_timeout}
            await self.node._update_session(data=udata)

        info: InfoResponse = await self.node._fetch_info()
        if "spotify" in info["sourceManagers"]:
            self.node._spotify_enabled = True

    def _cancel_keep_alive(self) -> None:
        task = self.keep_alive_task
        if task and not task.done():
            try:
                task.cancel()
            except Exception as e:
                logger.debug(
                    "Failed to cancel websocket keep alive: %s",
                    e,
                )
        self.keep_alive_task = None

    async def _establish_connection(self, *, silent: bool = False) -> None:
        session: aiohttp.ClientSession = self.node._session
        heartbeat: float = self.node.heartbeat
        uri: str = f"{self.node.uri.removesuffix('/')}/v4/websocket"

        if revv_logger.enabled and not silent:
            revv_logger.ws(
                "WS connect attempt",
                node_id=self.node.identifier,
                uri=uri,
                heartbeat=heartbeat,
                region=self.node.region or "global",
            )

        try:
            self.socket = await session.ws_connect(
                url=uri, heartbeat=heartbeat, headers=self.headers
            )  # type: ignore
        except Exception as e:
            await self._handle_connect_error(e, uri, silent)

    async def _handle_connect_error(self, e: Exception, uri: str, silent: bool) -> None:
        if isinstance(e, aiohttp.WSServerHandshakeError) and e.status in (401, 404):
            if revv_logger.enabled:
                msg = (
                    "WS connect failed — authorization error (401)"
                    if e.status == 401
                    else "WS connect failed — endpoint not found (404)"
                )
                revv_logger.error(msg, node_id=self.node.identifier, uri=uri)

            await self.cleanup()
            if e.status == 401:
                raise AuthorizationFailedException from e
            raise NodeException from e

        if revv_logger.enabled and not silent:
            revv_logger.error(
                "WS connect failed — unexpected error",
                node_id=self.node.identifier,
                uri=uri,
                error=str(e),
            )
        raise e
        # We suppress the repetitive logger.warning here to avoid spamming the console.
        # The Pool.connect method will handle the unified reporting.

    async def _wait_for_ready(self, attempt: int, max_attempts: int) -> bool:
        """Wait up to 2.0 seconds for 'ready' OP and NodeStatus.CONNECTED."""
        import time

        start = time.monotonic()
        while time.monotonic() - start < 2.0:
            if self.node.status is NodeStatus.CONNECTED:
                if revv_logger.enabled:
                    msg = (
                        "WS connected — node is READY"
                        if attempt == 0
                        else f"WS connected (attempt {attempt + 1}/{max_attempts}) — node is READY"
                    )
                    revv_logger.node(
                        msg,
                        node_id=self.node.identifier,
                        uri=self.node.uri,
                        region=self.node.region or "global",
                    )
                return True
            await asyncio.sleep(0.1)
        return False

    def _handle_previous_connection(self) -> None:
        if self.node._status is NodeStatus.CONNECTED:
            if revv_logger.enabled:
                revv_logger.ws(
                    "WS reconnect — node was previously CONNECTED, dispatching disconnect event",
                    node_id=self.node.identifier,
                )
            payload: NodeDisconnectedEventPayload = NodeDisconnectedEventPayload(node=self.node)
            self.dispatch("node_disconnected", payload)

    async def connect(self) -> None:
        self._handle_previous_connection()
        self.node._status = NodeStatus.CONNECTING
        self._cancel_keep_alive()

        try:
            await self._run_connect_loop()
        except (NodeException, AuthorizationFailedException):
            self.node._status = NodeStatus.DISCONNECTED
            raise
        except Exception:
            self.node._status = NodeStatus.DISCONNECTED
            # Initial attempts failed, start background retry loop
            _task = asyncio.create_task(self._run_retry_loop())
            self._tasks.add(_task)
            _task.add_done_callback(self._tasks.discard)

    async def _run_connect_loop(self) -> None:
        retries = self.node._retries if self.node._retries is not None else 2
        max_attempts = 1 + retries

        last_exception: Exception | None = None
        for attempt in range(max_attempts):
            try:
                await self._establish_connection()
                last_exception = None
            except AuthorizationFailedException:
                raise
            except Exception as e:
                last_exception = e
                await self._handle_connect_retry(attempt, max_attempts)
                continue

            if await self._handle_connection_success(attempt, max_attempts):
                return

        if last_exception:
            raise last_exception

    async def _handle_connect_retry(self, attempt: int, max_attempts: int) -> None:
        if attempt < max_attempts - 1:
            await asyncio.sleep(1.5)

    async def _handle_connection_success(self, attempt: int, max_attempts: int) -> bool:
        if not self.is_connected():
            return False

        self.keep_alive_task = asyncio.create_task(self.keep_alive())
        # We always return True here to signal we at least established the socket
        # The result of _wait_for_ready determines if we consider the node fully "ready"
        # but the loop should stop regardless if established.
        await self._wait_for_ready(attempt, max_attempts)
        return True

    async def _retry_once(self) -> bool:
        """Attempt a single background retry."""
        try:
            await self._establish_connection(silent=True)
            if self.is_connected():
                if revv_logger.enabled:
                    revv_logger.node(
                        "WS connected — keep_alive started",
                        node_id=self.node.identifier,
                        uri=self.node.uri,
                        region=self.node.region or "global",
                    )
                self.keep_alive_task = asyncio.create_task(self.keep_alive())
                return True
        except Exception:
            pass
        return False

    async def _run_retry_loop(self) -> None:
        retries: int | None = self.node._retries

        while True:
            if retries == 0:
                if revv_logger.enabled:
                    revv_logger.error(
                        "WS retries exhausted — node permanently disconnected",
                        node_id=self.node.identifier,
                    )
                await self.cleanup()
                break

            if retries:
                retries -= 1

            await asyncio.sleep(5.0)

            if await self._retry_once():
                break

    async def _process_op_ready(self, data: WebsocketOP) -> None:
        payload = cast("ReadyOP", data)
        resumed: bool = payload["resumed"]
        session_id: str = payload["sessionId"]

        self.node._status = NodeStatus.CONNECTED
        self.node._session_id = session_id

        await self._update_node()

        # Auto-fetch node info on connect
        try:
            self.node._info = await self.node.fetch_info()
        except Exception:
            logger.warning("Failed to fetch node info on connect", exc_info=True)

        if revv_logger.enabled:
            revv_logger.node(
                "OP ready — node CONNECTED",
                node_id=self.node.identifier,
                uri=self.node.uri,
                region=self.node.region or "global",
                session_id=session_id,
                resumed=resumed,
            )

        ready_payload: NodeReadyEventPayload = NodeReadyEventPayload(
            node=self.node, resumed=resumed, session_id=session_id
        )
        self.dispatch("node_ready", ready_payload)

    def _process_op_player_update(self, data: WebsocketOP) -> None:
        payload = cast("PlayerUpdateOP", data)
        playerup: Player | None = self.get_player(payload["guildId"])
        state: PlayerState = payload["state"]

        if revv_logger.enabled:
            revv_logger.ws_debug(
                "OP playerUpdate",
                node_id=self.node.identifier,
                guild_id=payload["guildId"],
                connected=state.get("connected", "?"),
                position_ms=state.get("position", "?"),
            )

        updatepayload: PlayerUpdateEventPayload = PlayerUpdateEventPayload(
            player=playerup, state=state
        )
        self.dispatch("player_update", updatepayload)

        if playerup:
            task = asyncio.create_task(playerup._update_event(updatepayload))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    def _process_op_stats(self, data: WebsocketOP) -> None:
        payload = cast("StatsOP", data)
        statspayload: StatsEventPayload = StatsEventPayload(data=payload)
        self.node._total_player_count = statspayload.players
        self.node.stats = statspayload

        if revv_logger.enabled:
            revv_logger.ws_debug(
                "OP stats",
                node_id=self.node.identifier,
                players=statspayload.players,
                playing=statspayload.playing,
            )

        self.dispatch("stats_update", statspayload)

    def _process_op_event(self, data: WebsocketOP) -> None:
        event_type = cast("dict[str, str]", data).get("type", "")
        guild_id = cast("dict[str, str]", data).get("guildId", "")
        player: Player | None = self.get_player(guild_id)

        handler = self._get_event_handler(event_type)
        if handler:
            handler(data, player)
        else:
            self._handle_unknown_event(data, player)

    def _get_event_handler(self, event_type: str):
        handlers = {
            "TrackStartEvent": self._handle_track_start_event,
            "TrackEndEvent": self._handle_track_end_event,
            "TrackExceptionEvent": self._handle_track_exception_event,
            "TrackStuckEvent": self._handle_track_stuck_event,
            "WebSocketClosedEvent": self._handle_websocket_closed_event,
        }
        return handlers.get(event_type)

    def _handle_track_start_event(self, data: WebsocketOP, player: Player | None) -> None:
        payload = cast("TrackStartEvent", data)
        track: Playable = Playable(payload["track"])

        if revv_logger.enabled:
            revv_logger.player(
                "Track started",
                node_id=self.node.identifier,
                guild_id=payload.get("guildId", "?"),
                track=track.title,
                author=track.author,
                duration_ms=track.length,
                source=getattr(track, "source", "?"),
            )

        startpayload: TrackStartEventPayload = TrackStartEventPayload(player=player, track=track)
        self.dispatch("track_start", startpayload)

        if player:
            task = asyncio.create_task(player._track_start(startpayload))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    def _handle_track_end_event(self, data: WebsocketOP, player: Player | None) -> None:
        payload = cast("TrackEndEvent", data)
        track: Playable = Playable(payload["track"])
        reason: str = payload["reason"]

        if player and reason != "replaced":
            player._current = None

        if revv_logger.enabled:
            revv_logger.player(
                "Track ended",
                node_id=self.node.identifier,
                guild_id=payload.get("guildId", "?"),
                track=track.title,
                reason=reason,
            )

        endpayload: TrackEndEventPayload = TrackEndEventPayload(
            player=player, track=track, reason=reason
        )
        self.dispatch("track_end", endpayload)

        if player:
            task = asyncio.create_task(player._auto_play_event(endpayload))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    def _handle_track_exception_event(self, data: WebsocketOP, player: Player | None) -> None:
        payload = cast("TrackExceptionEvent", data)
        track: Playable = Playable(payload["track"])
        exception: TrackExceptionPayload = payload["exception"]

        if revv_logger.enabled:
            revv_logger.error(
                "Track exception",
                node_id=self.node.identifier,
                guild_id=payload.get("guildId", "?"),
                track=track.title,
                error_message=exception.get("message", ""),
                cause=exception.get("cause", "?"),
                severity=exception.get("severity", "?"),
            )

        excpayload: TrackExceptionEventPayload = TrackExceptionEventPayload(
            player=player, track=track, exception=exception
        )

        LOGGER_TRACK.error(
            "A Lavalink TrackException was received on %r for player %r: %s, "
            "caused by: %s, with severity: %s%s",
            self.node,
            player,
            exception.get("message", ""),
            exception["cause"],
            exception["severity"],
            f"\nStack trace:\n{exception.get('causeStackTrace', '')}"
            if exception.get("causeStackTrace")
            else "",
        )
        self.dispatch("track_exception", excpayload)

    def _handle_track_stuck_event(self, data: WebsocketOP, player: Player | None) -> None:
        payload = cast("TrackStuckEvent", data)
        track: Playable = Playable(payload["track"])
        threshold: int = payload["thresholdMs"]

        if revv_logger.enabled:
            revv_logger.warning(
                "Track stuck",
                node_id=self.node.identifier,
                guild_id=payload.get("guildId", "?"),
                track=track.title,
                threshold_ms=threshold,
            )

        stuckpayload: TrackStuckEventPayload = TrackStuckEventPayload(
            player=player, track=track, threshold=threshold
        )
        self.dispatch("track_stuck", stuckpayload)

    def _handle_websocket_closed_event(self, data: WebsocketOP, player: Player | None) -> None:
        payload = cast("WebsocketClosedEvent", data)
        code: int = payload["code"]
        reason: str = payload["reason"]
        by_remote: bool = payload["byRemote"]

        if revv_logger.enabled:
            revv_logger.ws(
                "Voice WebSocket closed",
                node_id=self.node.identifier,
                guild_id=payload.get("guildId", "?"),
                code=code,
                reason=reason,
                by_remote=by_remote,
            )

        wcpayload: WebsocketClosedEventPayload = WebsocketClosedEventPayload(
            player=player, code=code, reason=reason, by_remote=by_remote
        )
        self.dispatch("websocket_closed", wcpayload)

        if player:
            task = asyncio.create_task(player._disconnected_wait(code, by_remote))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    def _handle_unknown_event(self, data: WebsocketOP, player: Player | None) -> None:
        other_payload: ExtraEventPayload = ExtraEventPayload(
            node=self.node, player=player, data=cast("dict[str, Any]", data)
        )
        self.dispatch("extra_event", other_payload)

    async def _process_op_dave(self, data: WebsocketOP) -> None:
        """Process DAVE protocol operations.

        This handles DAVE protocolChange and prepareTransition events
        for Discord's end-to-end encrypted voice communication.
        """
        payload = cast("dict[str, Any]", data)
        event_type: str = payload.get("type", "")
        guild_id: str = payload.get("guildId", "")
        player: Player | None = self.get_player(guild_id)

        if not player:
            logger.debug("DAVE event received for unknown guild %s, disregarding.", guild_id)
            return

        if event_type == "protocolChange":
            protocol_payload = cast("DAVEProtocolChangeEvent", payload)
            await player._on_dave_protocol_change(protocol_payload)
        elif event_type == "prepareTransition":
            transition_payload = cast("DAVEPrepareTransitionEvent", payload)
            await player._on_dave_prepare_transition(transition_payload)
        else:
            logger.debug(
                "Received unknown DAVE event type '%s' for guild %s, disregarding.",
                event_type,
                guild_id,
            )

    async def keep_alive(self) -> None:
        assert self.socket is not None

        try:
            while True:
                message: aiohttp.WSMessage = await self.socket.receive()

                if message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING):
                    if revv_logger.enabled:
                        revv_logger.ws(
                            "WS socket closed — triggering failover and reconnect",
                            node_id=self.node.identifier,
                            msg_type=str(message.type),
                        )
                    self._trigger_failover_and_reconnect()
                    break

                if message.data is None:
                    logger.debug("Received an empty message from Lavalink websocket. Disregarding.")
                    continue

                await self._handle_ws_message(message.json())

        except Exception as e:
            if revv_logger.enabled:
                revv_logger.error(
                    "WS keep_alive crashed with unexpected error — "
                    "triggering failover and reconnect",
                    node_id=self.node.identifier,
                    error=str(e),
                )
            self._trigger_failover_and_reconnect()

    async def _handle_ws_message(self, data: WebsocketOP) -> None:
        op = data["op"]

        if op == "ready":
            await self._process_op_ready(data)
        elif op == "playerUpdate":
            self._process_op_player_update(data)
        elif op == "stats":
            self._process_op_stats(data)
        elif op == "event":
            self._dispatch_ws_event(data)
        elif op == "dave":
            await self._process_op_dave(data)
        else:
            self._handle_unknown_op(op)

    def _dispatch_ws_event(self, data: WebsocketOP) -> None:
        if revv_logger.enabled:
            revv_logger.ws_debug(
                "OP event received",
                node_id=self.node.identifier,
                event_type=data.get("type", "?"),
                guild_id=data.get("guildId", "?"),
            )
        self._process_op_event(data)

    def _handle_unknown_op(self, op: str) -> None:
        if revv_logger.enabled:
            revv_logger.ws_debug(
                "Unknown OP received — disregarding",
                node_id=self.node.identifier,
                op=op,
            )
        logger.debug("'Received an unknown OP from Lavalink '%s'. Disregarding.", op)

    def _trigger_failover_and_reconnect(self) -> None:
        # TRIGGER FAILOVER: Move players away from this failing node immediately
        players = self.node.players
        from .node import Pool

        failover_task = asyncio.create_task(Pool._handle_node_failover(self.node, players=players))
        self._tasks.add(failover_task)
        failover_task.add_done_callback(self._tasks.discard)

        # Then attempt to reconnect in the background
        reconnect_task = asyncio.create_task(self.connect())
        self._tasks.add(reconnect_task)

    def get_player(self, guild_id: str | int) -> Player | None:
        return self.node.get_player(int(guild_id))

    def dispatch(self, event: str, /, *args: Any, **kwargs: Any) -> None:
        assert self.node.client is not None

        self.node.client.dispatch(f"revvlink_{event}", *args, **kwargs)
        logger.debug("%r dispatched the event 'on_revvlink_%s'", self.node, event)

    async def cleanup(self) -> None:
        if revv_logger.enabled:
            revv_logger.ws(
                "WS cleanup — closing socket and resetting state",
                node_id=self.node.identifier,
            )

        if not self.node._has_closed:
            # Capture players list BEFORE they are cleared in cleanup
            players = self.node.players
            from .node import Pool

            await Pool._handle_node_failover(self.node, players=players)

        task = self.keep_alive_task
        if task:
            try:
                task.cancel()
            except Exception:
                pass
        self.keep_alive_task = None

        socket = self.socket
        if socket:
            try:
                await socket.close()
            except Exception:
                pass
        self.socket = None

        self.node._status = NodeStatus.DISCONNECTED
        self.node._session_id = None
        self.node._players = {}

        self.node._websocket = None

        payload: NodeDisconnectedEventPayload = NodeDisconnectedEventPayload(node=self.node)
        self.dispatch("node_disconnected", payload)

        if revv_logger.enabled:
            revv_logger.node(
                "Node DISCONNECTED — cleanup complete",
                node_id=self.node.identifier,
            )

        logger.debug("Successfully cleaned up the websocket for %r", self.node)
