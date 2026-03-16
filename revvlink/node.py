"""
MIT License

Copyright (c) 2026-Present @JustNixx and @Dipendra-creator

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
import secrets
import urllib.parse
from typing import TYPE_CHECKING, Any, ClassVar, Literal, TypeAlias

import aiohttp
from discord.utils import classproperty

from . import __version__
from .enums import NodeStatus
from .exceptions import (
    AuthorizationFailedException,
    InvalidClientException,
    InvalidNodeException,
    LavalinkException,
    LavalinkLoadException,
    NodeException,
)
from .lfu import LFUCache
from .logger import revv_logger
from .payloads import (
    InfoResponsePayload,
    NodeInfo,
    PlayerResponsePayload,
    StatsEventPayload,
    StatsResponsePayload,
)
from .tracks import Playable, Playlist
from .websocket import Websocket

if TYPE_CHECKING:
    from collections.abc import Iterable

    import discord

    from .player import Player
    from .types.request import Request, UpdateSessionRequest
    from .types.response import (
        EmptyLoadedResponse,
        ErrorLoadedResponse,
        ErrorResponse,
        InfoResponse,
        PlayerResponse,
        PlaylistLoadedResponse,
        SearchLoadedResponse,
        StatsResponse,
        TrackLoadedResponse,
        UpdateResponse,
    )
    from .types.tracks import TrackPayload

    LoadedResponse: TypeAlias = (
        TrackLoadedResponse
        | SearchLoadedResponse
        | PlaylistLoadedResponse
        | EmptyLoadedResponse
        | ErrorLoadedResponse
    )


__all__ = ("Node", "Pool")


logger: logging.Logger = logging.getLogger(__name__)

_last_report_time: float = 0.0

_REQUEST_ERR_MSG: str = "An error occured making a request on %r: %s"

Method = Literal["GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS"]

REGIONS: dict[str, list[str]] = {
    "asia": [
        # India
        "bom",  # Mumbai
        "maa",  # Chennai
        # Japan
        "nrt",  # Tokyo (Narita)
        "hnd",  # Tokyo (Haneda)
        # Southeast Asia
        "sin",  # Singapore
        "kul",  # Kuala Lumpur
        "bkk",  # Bangkok
        "cgn",  # Guangzhou / China edge sometimes
        # Korea
        "icn",  # Seoul
        # Hong Kong / Taiwan
        "hkg",  # Hong Kong
        "tpe",  # Taipei
        # Oceania
        "syd",  # Sydney
        "mel",  # Melbourne
        "akl",  # Auckland
    ],
    "eu": [
        # Netherlands
        "ams",  # Amsterdam
        # Germany
        "fra",  # Frankfurt
        "ber",  # Berlin
        # United Kingdom
        "lhr",  # London
        "lon",  # London (legacy)
        # France
        "cdg",  # Paris
        # Spain
        "mad",  # Madrid
        "bcg",  # Barcelona (rare)
        # Poland
        "waw",  # Warsaw
        # Italy
        "mil",  # Milan
        "rom",  # Rome
        # Nordics
        "arn",  # Stockholm
        "hel",  # Helsinki
        "osl",  # Oslo
        "cph",  # Copenhagen
        # Central / East EU
        "prg",  # Prague
        "bud",  # Budapest
        "vie",  # Vienna
    ],
    "us": [
        # East
        "iad",  # Washington DC
        "atl",  # Atlanta
        "mia",  # Miami
        "bos",  # Boston
        "jfk",  # New York
        # Central
        "ord",  # Chicago
        "dfw",  # Dallas
        # West
        "lax",  # Los Angeles
        "sea",  # Seattle
        "sjc",  # San Jose
        "phx",  # Phoenix
        "den",  # Denver
    ],
    "southamerica": [
        "gru",  # São Paulo
        "scl",  # Santiago
        "eze",  # Buenos Aires
        "lim",  # Lima
        "bog",  # Bogotá
    ],
    "africa": [
        "jnb",  # Johannesburg
        "cpt",  # Cape Town
        "nbo",  # Nairobi
    ],
    "middleeast": [
        "dxb",  # Dubai
        "auh",  # Abu Dhabi
        "ruh",  # Riyadh
        "tel",  # Tel Aviv
    ],
}


class Node:
    """The Node represents a connection to Lavalink.

    The Node is responsible for keeping the websocket alive, resuming session,
    sending API requests and keeping track of connected all :class:`~revvlink.Player`.

    .. container:: operations

        .. describe:: node == other

            Equality check to determine whether this Node is equal to another reference of a Node.

        .. describe:: repr(node)

            The official string representation of this Node.

    Parameters
    ----------
    identifier: str | None
        A unique identifier for this Node. Could be ``None`` to generate a random one on creation.
    uri: str
        ``http://localhost:2333`` which includes the port. But you could also provide a
        domain which won't require a port like ``https://lavalink.example.com`` or a public
        IP address and port like ``http://111.333.444.55:2333``.
    password: str
        The password used to connect and authorize this Node.
    session: aiohttp.ClientSession | None
        An optional :class:`aiohttp.ClientSession` used to connect this Node over
        websocket and REST.
        If ``None``, one will be generated for you. Defaults to ``None``.
    heartbeat: Optional[float]
        A ``float`` in seconds to ping your websocket keep alive. Usually you would not change this.
    retries: int | None
        A ``int`` of retries to attempt when connecting or reconnecting this Node.
        When the retries are exhausted the Node will be closed and cleaned-up.
        ``None`` will retry forever. Defaults to ``None``.
    client: :class:`discord.Client` | None
        The :class:`discord.Client` or subclasses, E.g. ``commands.Bot`` used to
        connect this Node. If this is *not* passed you must pass this to
        :meth:`revvlink.Pool.connect`.
    resume_timeout: Optional[int]
        The seconds this Node should configure Lavalink for resuming its current
        session in case of network issues. If this is ``0`` or below, resuming
        will be disabled. Defaults to ``60``.
    inactive_player_timeout: int | None
        Set the default for :attr:`revvlink.Player.inactive_timeout` on every player
        that connects to this node. Defaults to ``300``.
    inactive_channel_tokens: int | None
        Sets the default for :attr:`revvlink.Player.inactive_channel_tokens` on every
        player that connects to this node. Defaults to ``3``.
    region : str | None
        An optional string representing the node's region (e.g. "us", "eu", "asia").
        Used for regional load balancing. Defaults to ``None``.

        See also: :func:`on_revvlink_inactive_player`.
    """

    def __init__(
        self,
        *,
        identifier: str | None = None,
        uri: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
        heartbeat: float = 15.0,
        retries: int | None = None,
        client: discord.Client | None = None,
        resume_timeout: int = 60,
        inactive_player_timeout: int | None = 300,
        inactive_channel_tokens: int | None = 3,
        region: str | None = None,
    ) -> None:
        self._identifier = identifier or secrets.token_urlsafe(12)
        self._uri = uri.removesuffix("/")
        self._password = password
        self._session = session or aiohttp.ClientSession()
        self._heartbeat = heartbeat
        self._retries = retries
        self._client = client
        self._resume_timeout = resume_timeout
        self.region: str | None = region

        self._status: NodeStatus = NodeStatus.DISCONNECTED
        self._has_closed: bool = False
        self._session_id: str | None = None

        self._players: dict[int, Player] = {}
        self._total_player_count: int | None = None

        self._spotify_enabled: bool = False

        self._websocket: Websocket | None = None

        self._info: InfoResponsePayload | None = None
        self.stats: StatsEventPayload | StatsResponsePayload | None = None

        if inactive_player_timeout and inactive_player_timeout < 10:
            logger.warning(
                'Setting "inactive_player_timeout" below 10 seconds '
                "may result in unwanted side effects."
            )

        self._inactive_player_timeout = (
            inactive_player_timeout
            if inactive_player_timeout and inactive_player_timeout > 0
            else None
        )

        self._inactive_channel_tokens = inactive_channel_tokens

    def __repr__(self) -> str:
        return (
            f"Node(identifier={self.identifier}, uri={self.uri}, "
            f"status={self.status}, players={len(self.players)})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented

        return other.identifier == self.identifier

    @property
    def headers(self) -> dict[str, str]:
        """A property that returns the headers configured for sending API and websocket requests.

        .. warning::

            This includes your Node password. Please be vigilant when using this property.
        """
        assert self.client is not None
        assert self.client.user is not None

        data = {
            "Authorization": self.password,
            "User-Id": str(self.client.user.id),
            "Client-Name": f"RevvLink/{__version__}",
        }

        return data

    @property
    def identifier(self) -> str:
        """The unique identifier for this :class:`Node`."""
        return self._identifier

    @property
    def uri(self) -> str:
        """The URI used to connect this :class:`Node` to Lavalink."""
        return self._uri

    @property
    def status(self) -> NodeStatus:
        """The current :class:`Node` status.

        Refer to: :class:`~revvlink.NodeStatus`
        """
        return self._status

    @property
    def penalty(self) -> float:
        """The composite load score for this node. Lower is better.

        Used by :meth:`Pool.get_node` to rank nodes within a region or globally.

        Components:
            - CPU system load (weighted exponentially)
            - Active player count (flat cost per player)
            - Frame deficit (huge penalty — indicates audio stuttering)

        Returns
        -------
        float
            The calculated penalty score.
        """
        if not self.stats:
            return 9e30  # effectively infinite — node has no stats yet

        cpu = 1.05 ** (100 * self.stats.cpu.system_load) * 10 - 10

        if self.stats.frames:
            frames_deficit = 1.03 ** (500 * (self.stats.frames.deficit / 3000)) * 300 - 300
            frames_nulled = (1.03 ** (500 * (self.stats.frames.nulled / 3000)) * 300 - 300) * 2
        else:
            frames_deficit = 0
            frames_nulled = 0

        players = self.stats.playing * 1.5

        return cpu + frames_deficit + frames_nulled + players

    @property
    def players(self) -> dict[int, Player]:
        """A mapping of :attr:`discord.Guild.id` to :class:`~revvlink.Player`.

        Returns
        -------
        dict[int, :class:`~revvlink.Player`]
            A shallow copy of the internal players mapping.
        """
        return self._players.copy()

    @property
    def client(self) -> discord.Client | None:
        """The :class:`discord.Client` associated with this :class:`Node`.

        Returns
        -------
        :class:`discord.Client` | None
            The client instance, or ``None`` if it has not been set.
        """
        return self._client

    @property
    def password(self) -> str:
        """The password used to connect and authorize this :class:`Node` to Lavalink.

        Returns
        -------
        str
            The node password.
        """
        return self._password

    @property
    def heartbeat(self) -> float:
        """The duration in seconds between WebSocket heartbeat pings.

        Returns
        -------
        float
            The heartbeat interval in seconds.
        """
        return self._heartbeat

    @property
    def session_id(self) -> str | None:
        """The Lavalink session ID for this node connection.

        Returns
        -------
        str | None
            The session ID, or ``None`` if the node is not connected.
        """
        return self._session_id

    @property
    def info(self) -> NodeInfo | None:
        """Returns the cached node info including source managers and plugins.

        This property returns a :class:`NodeInfo` dataclass with convenience methods
        for checking available sources and plugins.

        Could be ``None`` if the node has not fetched info yet.
        Use :meth:`refresh_info` to fetch the latest info.

        Returns
        -------
        NodeInfo | None
            The node info, or None if not yet fetched.
        """
        if self._info is None:
            return None
        return NodeInfo.from_payload(self._info)

    async def refresh_info(self) -> NodeInfo:
        """Fetch and cache the latest node info from Lavalink.

        This method updates the cached info with the latest data from the Lavalink
        server, including available source managers and plugins.

        Returns
        -------
        NodeInfo
            The updated node info.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occurred while making this request to Lavalink,
            and Lavalink was unable to send any error information.


        """
        self._info = await self.fetch_info()
        return NodeInfo.from_payload(self._info)

    async def _pool_closer(self) -> None:
        """Internal helper to safely close the session and node connection.

        This is usually called when the pool is being shut down.
        """
        if not self._has_closed:
            await self.close()

        try:
            await self._session.close()
        except Exception:
            pass

    async def close(self, eject: bool = False, failover: bool = True) -> None:
        """Method to close this Node and cleanup.

        After this method has finished, the event ``on_revvlink_node_closed`` will be fired.

        This method renders the Node websocket disconnected and disconnects all players.

        Parameters
        ----------
        eject: bool
            If ``True``, this will remove the Node from the Pool. Defaults to ``False``.
        failover: bool
            If ``True``, this will attempt to failover all players to another node.
            Defaults to ``True``.
        """
        if revv_logger.enabled:
            revv_logger.node(
                "Node closing",
                node_id=self.identifier,
                uri=self.uri,
                eject=eject,
                active_players=len(self._players),
                failover=failover,
            )

        if failover:
            await Pool._handle_node_failover(self)

        disconnected: list[Player] = []

        for player in self._players.copy().values():
            try:
                await player.disconnect()
            except Exception as e:
                logger.debug(
                    "An error occured while disconnecting a player in the close method of %r: %s",
                    self,
                    e,
                )

            disconnected.append(player)

        if self._websocket is not None:
            await self._websocket.cleanup()

        self._status = NodeStatus.DISCONNECTED
        self._session_id = None
        self._players = {}

        self._has_closed = True

        if eject:
            getattr(Pool, "_Pool__nodes").pop(self.identifier, None)

        if revv_logger.enabled:
            revv_logger.node(
                "Node closed",
                node_id=self.identifier,
                players_disconnected=len(disconnected),
                ejected=eject,
            )

        # Dispatch Node Closed Event... node, list of disconnected players
        if self.client is not None:
            self.client.dispatch("revvlink_node_closed", self, disconnected)

    async def _connect(self, *, client: discord.Client | None) -> None:
        """Internal method to initiate the WebSocket connection to Lavalink.

        Parameters
        ----------
        client: :class:`discord.Client` | None
            The Discord client to use for this connection.

        Raises
        ------
        InvalidClientException
            No valid Discord client was provided.
        """
        client_ = self._client or client

        if not client_:
            raise InvalidClientException(
                f"Unable to connect {self!r} as you have not provided a valid discord.Client."
            )

        self._client = client_

        self._has_closed = False
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()

        if revv_logger.enabled:
            revv_logger.node(
                "Node connecting",
                node_id=self.identifier,
                uri=self.uri,
                region=self.region or "global",
            )

        websocket: Websocket = Websocket(node=self)
        self._websocket = websocket
        await websocket.connect()

    async def send(
        self,
        method: Method = "GET",
        *,
        path: str,
        data: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Method for making requests to the Lavalink node.

        .. warning::

            Usually you wouldn't use this method. Please use the built in methods
            of :class:`~Node`, :class:`~Pool` and :class:`~revvlink.Player`,
            unless you need to send specific plugin data to Lavalink.

            Using this method may have unwanted side effects on your players and/or nodes.

        Parameters
        ----------
        method: Optional[str]
            The method to use when making this request. Available methods are
            "GET", "POST", "PATCH", "PUT", "DELETE" and "OPTIONS".
            Defaults to "GET".
        path: str
            The path to make this request to. E.g. "/v4/stats".
        data: Any | None
            The optional JSON data to send along with your request to Lavalink.
            This should be a dict[str, Any] and able to be converted to JSON.
        params: Optional[dict[str, Any]]
            An optional dict of query parameters to send with your request to Lavalink.
            If you include your query parameters in the ``path`` parameter,
            do not pass them here as well. E.g. {"thing": 1, "other": 2}
            would equate to "?thing=1&other=2".

        Returns
        -------
        Any
            The response from Lavalink which will either be None, a str or JSON.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occured while making this request to Lavalink,
            and Lavalink was unable to send any error information.
        """
        clean_path: str = path.removesuffix("/")
        uri: str = f"{self.uri}/{clean_path}"

        if params is None:
            params = {}

        if revv_logger.enabled:
            revv_logger.outgoing(
                "REST request",
                node_id=self.identifier,
                method=method,
                path=clean_path,
            )

        async with self._session.request(
            method=method, url=uri, params=params, json=data, headers=self.headers
        ) as resp:
            if revv_logger.enabled:
                revv_logger.incoming(
                    "REST response",
                    node_id=self.identifier,
                    method=method,
                    path=clean_path,
                    status=resp.status,
                )

            if resp.status == 204:
                return

            if resp.status >= 300:
                try:
                    exc_data: ErrorResponse = await resp.json()
                except Exception as e:
                    logger.warning(_REQUEST_ERR_MSG, self, e)
                    raise NodeException(status=resp.status)

                raise LavalinkException(data=exc_data)

            try:
                rdata: Any = await resp.json()
            except aiohttp.ContentTypeError:
                pass
            else:
                return rdata

            try:
                body: str = await resp.text()
            except aiohttp.ClientError:
                return

            return body

    async def _fetch_players(self) -> list[PlayerResponse]:
        """Internal helper to fetch all player states from Lavalink.

        Returns
        -------
        list[PlayerResponse]
            A list of dictionary payloads representing player states.
        """
        uri: str = f"{self.uri}/v4/sessions/{self.session_id}/players"

        async with self._session.get(url=uri, headers=self.headers) as resp:
            if resp.status == 200:
                resp_data: list[PlayerResponse] = await resp.json()
                return resp_data

            try:
                exc_data: ErrorResponse = await resp.json()
            except Exception as e:
                logger.warning(_REQUEST_ERR_MSG, self, e)
                raise NodeException(status=resp.status) from e

            raise LavalinkException(data=exc_data)

        # Explicitly return to satisfy Pyright's strict checks,
        # though all paths above either return or raise.
        return []

    async def fetch_players(self) -> list[PlayerResponsePayload]:
        """Method to fetch the player information Lavalink holds for every
        connected player on this node.

        .. warning::

            This payload is not the same as the :class:`revvlink.Player` class.
            This is the data received from Lavalink about the players.


        Returns
        -------
        list[:class:`PlayerResponsePayload`]
            A list of :class:`PlayerResponsePayload` representing each player
            connected to this node.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occured while making this request to Lavalink,
            and Lavalink was unable to send any error information.


        """
        data: list[PlayerResponse] = await self._fetch_players()

        payload: list[PlayerResponsePayload] = [PlayerResponsePayload(p) for p in data]
        return payload

    async def _fetch_player(self, guild_id: int, /) -> PlayerResponse:
        """Internal helper to fetch a specific player state from Lavalink.

        Parameters
        ----------
        guild_id: int
            The Discord guild ID.

        Returns
        -------
        PlayerResponse
            The player state payload.
        """
        uri: str = f"{self.uri}/v4/sessions/{self.session_id}/players/{guild_id}"

        async with self._session.get(url=uri, headers=self.headers) as resp:
            if resp.status == 200:
                resp_data: PlayerResponse = await resp.json()
                return resp_data

            else:
                try:
                    exc_data: ErrorResponse = await resp.json()
                except Exception as e:
                    logger.warning(_REQUEST_ERR_MSG, self, e)
                    raise NodeException(status=resp.status)

                raise LavalinkException(data=exc_data)

    async def fetch_player_info(self, guild_id: int, /) -> PlayerResponsePayload | None:
        """Method to fetch the player information Lavalink holds for the specific guild.

        .. warning::

            This payload is not the same as the :class:`revvlink.Player` class.
            This is the data received from Lavalink about the player.
            See: :meth:`~revvlink.Node.get_player`


        Parameters
        ----------
        guild_id: int
            The ID of the guild you want to fetch info for.

        Returns
        -------
        :class:`PlayerResponsePayload` | None
            The :class:`PlayerResponsePayload` representing the player info for the
            guild ID connected to this node. Could be ``None`` if no player is
            found with the given guild ID.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occured while making this request to Lavalink,
            and Lavalink was unable to send any error information.
        """
        try:
            data: PlayerResponse = await self._fetch_player(guild_id)
        except LavalinkException as e:
            if e.status == 404:
                return None

            raise e

        payload: PlayerResponsePayload = PlayerResponsePayload(data)
        return payload

    async def _update_player(
        self, guild_id: int, /, *, data: Request, replace: bool = False
    ) -> PlayerResponse:
        no_replace: bool = not replace

        uri: str = (
            f"{self.uri}/v4/sessions/{self.session_id}/players/{guild_id}?noReplace={no_replace}"
        )

        async with self._session.patch(url=uri, json=data, headers=self.headers) as resp:
            if resp.status == 200:
                resp_data: PlayerResponse = await resp.json()
                return resp_data

            else:
                try:
                    exc_data: ErrorResponse = await resp.json()
                except Exception as e:
                    logger.warning(_REQUEST_ERR_MSG, self, e)
                    raise NodeException(status=resp.status)

                raise LavalinkException(data=exc_data)

    async def _destroy_player(self, guild_id: int, /) -> None:
        uri: str = f"{self.uri}/v4/sessions/{self.session_id}/players/{guild_id}"

        async with self._session.delete(url=uri, headers=self.headers) as resp:
            if resp.status == 204:
                return

            try:
                exc_data: ErrorResponse = await resp.json()
            except Exception as e:
                logger.warning(_REQUEST_ERR_MSG, self, e)
                raise NodeException(status=resp.status)

            raise LavalinkException(data=exc_data)

    async def _update_session(self, *, data: UpdateSessionRequest) -> UpdateResponse:
        """Internal helper to update the Lavalink session configuration.

        Parameters
        ----------
        data: UpdateSessionRequest
            The update payload.

        Returns
        -------
        UpdateResponse
            The session update response.
        """
        uri: str = f"{self.uri}/v4/sessions/{self.session_id}"

        async with self._session.patch(url=uri, json=data, headers=self.headers) as resp:
            if resp.status == 200:
                resp_data: UpdateResponse = await resp.json()
                return resp_data

            else:
                try:
                    exc_data: ErrorResponse = await resp.json()
                except Exception as e:
                    logger.warning(_REQUEST_ERR_MSG, self, e)
                    raise NodeException(status=resp.status)

                raise LavalinkException(data=exc_data)

    async def _fetch_tracks(self, query: str) -> LoadedResponse:
        uri: str = f"{self.uri}/v4/loadtracks?identifier={query}"

        if revv_logger.enabled:
            revv_logger.outgoing(
                "loadtracks request",
                node_id=self.identifier,
                query=query[:80] if len(query) > 80 else query,
            )

        async with self._session.get(url=uri, headers=self.headers) as resp:
            if resp.status == 200:
                resp_data: LoadedResponse = await resp.json()
                if revv_logger.enabled:
                    revv_logger.incoming(
                        "loadtracks response",
                        node_id=self.identifier,
                        load_type=resp_data.get("loadType", "?"),
                    )
                return resp_data

            else:
                if revv_logger.enabled:
                    revv_logger.error(
                        "loadtracks request failed",
                        node_id=self.identifier,
                        status=resp.status,
                    )
                try:
                    exc_data: ErrorResponse = await resp.json()
                except Exception as e:
                    logger.warning(_REQUEST_ERR_MSG, self, e)
                    raise NodeException(status=resp.status)

                raise LavalinkException(data=exc_data)

    async def _decode_track(self, encoded: str) -> TrackPayload:
        uri: str = f"{self.uri}/v4/decodetrack"

        async with self._session.get(
            url=uri, params={"encodedTrack": encoded}, headers=self.headers
        ) as resp:
            if resp.status == 200:
                resp_data: TrackPayload = await resp.json()
                return resp_data

            try:
                exc_data: ErrorResponse = await resp.json()
            except Exception as e:
                logger.warning(_REQUEST_ERR_MSG, self, e)
                raise NodeException(status=resp.status)

            raise LavalinkException(data=exc_data)

    async def decode_track(self, encoded: str, /) -> Playable:
        """Decode a single base64 encoded track string back into a :class:`~revvlink.Playable`.

        Parameters
        ----------
        encoded: str
            The base64 encoded track string to decode.

        Returns
        -------
        :class:`~revvlink.Playable`
            The decoded :class:`~revvlink.Playable`.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occured while making this request to Lavalink,
            and Lavalink was unable to send any error information.


        """
        data: TrackPayload = await self._decode_track(encoded)
        return Playable(data=data)

    async def _decode_tracks(self, encoded: list[str]) -> list[TrackPayload]:
        uri: str = f"{self.uri}/v4/decodetracks"

        async with self._session.post(url=uri, json=encoded, headers=self.headers) as resp:
            if resp.status == 200:
                resp_data: list[TrackPayload] = await resp.json()
                return resp_data

            try:
                exc_data: ErrorResponse = await resp.json()
            except Exception as e:
                logger.warning(_REQUEST_ERR_MSG, self, e)
                raise NodeException(status=resp.status) from e

            raise LavalinkException(data=exc_data)

    async def decode_tracks(self, encoded: list[str], /) -> list[Playable]:
        """Decode a list of base64 encoded track strings back into a list of
        :class:`~revvlink.Playable`.

        Parameters
        ----------
        encoded: list[str]
            A list of base64 encoded track strings to decode.

        Returns
        -------
        list[:class:`~revvlink.Playable`]
            The decoded list of :class:`~revvlink.Playable`.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occured while making this request to Lavalink,
            and Lavalink was unable to send any error information.


        """
        data: list[TrackPayload] = await self._decode_tracks(encoded)
        return [Playable(data=t) for t in data]

    async def _get_routeplanner_status(self) -> Any:
        uri: str = f"{self.uri}/v4/routeplanner/status"

        async with self._session.get(url=uri, headers=self.headers) as resp:
            if resp.status == 204:
                return None

            if resp.status == 200:
                return await resp.json()

            try:
                exc_data: ErrorResponse = await resp.json()
            except Exception as e:
                logger.warning(_REQUEST_ERR_MSG, self, e)
                raise NodeException(status=resp.status)

            raise LavalinkException(data=exc_data)

    async def get_routeplanner_status(self) -> dict[str, Any] | None:
        """Fetch the RoutePlanner status for this Lavalink node.

        Returns
        -------
        dict[str, Any] | None
            A dictionary containing the RoutePlanner status, or ``None``
            if the RoutePlanner is not enabled on the server.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occured while making this request to Lavalink,
            and Lavalink was unable to send any error information.


        """
        return await self._get_routeplanner_status()

    async def unmark_failed_address(self, address: str, /) -> None:
        """Unmark a failed address in the RoutePlanner so it may be reused.

        Parameters
        ----------
        address: str
            The IP address to unmark as failed.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occured while making this request to Lavalink,
            and Lavalink was unable to send any error information.


        """
        uri: str = f"{self.uri}/v4/routeplanner/free/address"

        async with self._session.post(
            url=uri, json={"address": address}, headers=self.headers
        ) as resp:
            if resp.status == 204:
                return

            try:
                exc_data: ErrorResponse = await resp.json()
            except Exception as e:
                logger.warning(_REQUEST_ERR_MSG, self, e)
                raise NodeException(status=resp.status)

            raise LavalinkException(data=exc_data)

    async def unmark_all_failed_addresses(self) -> None:
        """Unmark all failed addresses in the RoutePlanner so they may be reused.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occured while making this request to Lavalink,
            and Lavalink was unable to send any error information.


        """
        uri: str = f"{self.uri}/v4/routeplanner/free/all"

        async with self._session.post(url=uri, headers=self.headers) as resp:
            if resp.status == 204:
                return

            try:
                exc_data: ErrorResponse = await resp.json()
            except Exception as e:
                logger.warning(_REQUEST_ERR_MSG, self, e)
                raise NodeException(status=resp.status)

            raise LavalinkException(data=exc_data)

    async def _fetch_info(self) -> InfoResponse:
        uri: str = f"{self.uri}/v4/info"

        async with self._session.get(url=uri, headers=self.headers) as resp:
            if resp.status == 200:
                resp_data: InfoResponse = await resp.json()
                return resp_data

            else:
                try:
                    exc_data: ErrorResponse = await resp.json()
                except Exception as e:
                    logger.warning(_REQUEST_ERR_MSG, self, e)
                    raise NodeException(status=resp.status)

                raise LavalinkException(data=exc_data)

    async def fetch_info(self) -> InfoResponsePayload:
        """Method to fetch this Lavalink Nodes info response data.

        Returns
        -------
        :class:`InfoResponsePayload`
            The :class:`InfoResponsePayload` associated with this Node.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occured while making this request to Lavalink,
            and Lavalink was unable to send any error information.


        """
        data: InfoResponse = await self._fetch_info()

        payload: InfoResponsePayload = InfoResponsePayload(data)
        return payload

    async def _fetch_stats(self) -> StatsResponse:
        uri: str = f"{self.uri}/v4/stats"

        async with self._session.get(url=uri, headers=self.headers) as resp:
            if resp.status == 200:
                resp_data: StatsResponse = await resp.json()
                return resp_data

            else:
                try:
                    exc_data: ErrorResponse = await resp.json()
                except Exception as e:
                    logger.warning(_REQUEST_ERR_MSG, self, e)
                    raise NodeException(status=resp.status)

                raise LavalinkException(data=exc_data)

    async def fetch_stats(self) -> StatsResponsePayload:
        """Method to fetch this Lavalink Nodes stats response data.

        Returns
        -------
        :class:`StatsResponsePayload`
            The :class:`StatsResponsePayload` associated with this Node.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occured while making this request to Lavalink,
            and Lavalink was unable to send any error information.


        """
        data: StatsResponse = await self._fetch_stats()

        payload: StatsResponsePayload = StatsResponsePayload(data)
        return payload

    async def _fetch_version(self) -> str:
        uri: str = f"{self.uri}/version"

        async with self._session.get(url=uri, headers=self.headers) as resp:
            if resp.status == 200:
                return await resp.text()

            try:
                exc_data: ErrorResponse = await resp.json()
            except Exception as e:
                logger.warning(_REQUEST_ERR_MSG, self, e)
                raise NodeException(status=resp.status) from e

            raise LavalinkException(data=exc_data)

    async def fetch_version(self) -> str:
        """Method to fetch this Lavalink version string.

        Returns
        -------
        str
            The version string associated with this Lavalink node.

        Raises
        ------
        LavalinkException
            An error occurred while making this request to Lavalink.
        NodeException
            An error occured while making this request to Lavalink,
            and Lavalink was unable to send any error information.


        """
        data: str = await self._fetch_version()
        return data

    def get_player(self, guild_id: int, /) -> Player | None:
        """Return a :class:`~revvlink.Player` associated with the
        provided :attr:`discord.Guild.id`.

        Parameters
        ----------
        guild_id: int
            The :attr:`discord.Guild.id` to retrieve a :class:`~revvlink.Player` for.

        Returns
        -------
        Optional[:class:`~revvlink.Player`]
            The Player associated with this guild ID. Could be None if no
            :class:`~revvlink.Player` exists for this guild.
        """
        return self._players.get(guild_id, None)


class Pool:
    """The revvlink Pool represents a collection of :class:`~revvlink.Node`
    and helper methods for searching tracks.

    To connect a :class:`~revvlink.Node` please use this Pool.

    .. note::

        All methods and attributes on this class are class level, not instance.
        Do not create an instance of this class.
    """

    __nodes: ClassVar[dict[str, Node]] = {}
    __cache: LFUCache | None = None
    _regions: dict[str, list[str]] = REGIONS
    _tasks: ClassVar[set[asyncio.Task[Any]]] = set()

    @classmethod
    def region_from_endpoint(cls, endpoint: str | None) -> str | None:
        """Parses a Discord voice endpoint string to map it back to a Region name.

        Parameters
        ----------
        endpoint: str | None
            The raw Discord voice endpoint (e.g., "us-east1.discord.gg:443").

        Returns
        -------
        str | None
            The region label string (e.g., "us", "eu", "asia"), or "global" if no match is found.
            Returns ``None`` if the endpoint is empty.
        """
        if not endpoint:
            return None

        # actual data -> c-bom11-ea4174e2.
        endpoint = endpoint.lower()
        for region, identifiers in cls._regions.items():
            for identifier in identifiers:
                if identifier in endpoint:
                    return region

        return "global"  # default to global if no match, since it's the default region on Lavalink

    @classmethod
    async def connect(
        cls,
        *,
        nodes: Iterable[Node],
        client: discord.Client | None = None,
        cache_capacity: int | None = None,
        regions: dict[str, list[str]] | None = None,
    ) -> dict[str, Node]:
        """Connect the provided Iterable[:class:`Node`] to Lavalink.

        Parameters
        ----------
        nodes: Iterable[:class:`Node`]
            The :class:`Node`'s to connect to Lavalink.
        client: :class:`discord.Client` | None
            The :class:`discord.Client` to use to connect the :class:`Node`.
            If the Node already has a client set, this method will **not**
            override it. Defaults to None.
        cache_capacity: int | None
            An optional integer of the amount of track searches to cache.
            This is an experimental mode.
            Passing ``None`` will disable this experiment. Defaults to ``None``.
        regions : dict[str, list[str]] | None
            An optional mapping of region label to a list of Discord voice
            endpoint substrings (e.g. ``{"us": ["iad", "atl"], "eu": ["ams"]}``).
            When provided, this overrides the built-in ``REGIONS`` map used by
            `Pool.region_from_endpoint` and `Pool.get_node`.
            Defaults to ``None``, which keeps the built-in map.

        Returns
        -------
        dict[str, :class:`Node`]
            A mapping of :attr:`Node.identifier` to :class:`Node` associated with the :class:`Pool`.


        Raises
        ------
        AuthorizationFailedException
            The node password was incorrect.
        InvalidClientException
            The :class:`discord.Client` passed was not valid.
        NodeException
            The node failed to connect properly. Please check that your
            Lavalink version is version 4.The ``client`` parameter is no longer required.
        """
        if regions is not None:
            cls._regions = regions

        coros = []
        for node in nodes:
            client_ = node.client or client
            coros.append(cls._connect_node(node, client_))

        await asyncio.gather(*coros)

        cls._display_connection_report()

        if cache_capacity is not None and cls.nodes:
            cls._setup_cache(cache_capacity)

        return cls.nodes

    @classmethod
    def _display_connection_report(cls) -> None:
        """Internal method to display a summary of connected and failed nodes.

        Uses ANSI color codes to format the output for the console.
        """
        import time

        global _last_report_time
        now = time.time()

        # Guard: Don't print more than once every 60 seconds to prevent spam
        # if Pool.connect is called multiple times (e.g. on multiple shards/ready events).
        if now - _last_report_time < 60.0:
            return

        _last_report_time = now

        nodes = cls.__nodes.values()
        if not nodes:
            return

        connected = [n for n in nodes if n.status is NodeStatus.CONNECTED]
        failed = [n for n in nodes if n.status is not NodeStatus.CONNECTED]

        # ANSI Color Constants
        Y = "\033[93m"  # Bright Yellow
        G = "\033[92m"  # Bright Green
        R = "\033[91m"  # Bright Red
        B = "\033[94m"  # Blue
        C = "\033[36m"  # Cyan
        D = "\033[2m"  # Dim
        E = "\033[0m"  # Reset

        print(
            f"\n{Y}[Lavalink]{E} Node connection report "
            f"({G}{len(connected)}{E}/{Y}{len(nodes)}{E} connected)\n"
        )

        for node in connected:
            print(
                f"  {G}[CONNECTED]{E} {B}{node.identifier:<10}{E} {G}{node.uri:<30}{E} "
                f"{D}region={E}{C}{node.region or 'global'}{E}"
            )

        for node in failed:
            print(
                f"  {R}[FAILED]{E}    {B}{node.identifier:<10}{E} {R}{node.uri:<30}{E} "
                f"{D}region={E}{C}{node.region or 'global'}{E}"
            )

        print("")

    @classmethod
    async def _connect_node(cls, node: Node, client: discord.Client | None) -> None:
        """Internal method to register and connect a node to the pool.

        Parameters
        ----------
        node: :class:`Node`
            The node instance to connect.
        client: :class:`discord.Client` | None
            The Discord client to associate with the node.
        """
        if node.identifier in cls.__nodes:
            logger.error(
                'Unable to connect %r as you already have a node with identifier "%s"',
                node,
                node.identifier,
            )
            return

        if node.status in (NodeStatus.CONNECTING, NodeStatus.CONNECTED):
            logger.error(
                "Unable to connect %r as it is already in a connecting or connected state.",
                node,
            )
            return

        if await cls._attempt_connect(node, client):
            cls.__nodes[node.identifier] = node

    @classmethod
    async def _attempt_connect(cls, node: Node, client: discord.Client | None) -> bool:
        """Internal method to attempt a connection for a specific node.

        Parameters
        ----------
        node: :class:`Node`
            The node to attempt connection on.
        client: :class:`discord.Client` | None
            The Discord client to use.

        Returns
        -------
        bool
            Whether the connection was successful.
        """
        try:
            await node._connect(client=client)
        except InvalidClientException as e:
            logger.error(e)
        except AuthorizationFailedException:
            logger.error("Failed to authenticate %r on Lavalink with the provided password.", node)
        except NodeException:
            logger.error(
                "Failed to connect to %r. Check that your Lavalink major "
                "version is '4' and that you are trying to connect to "
                "Lavalink on the correct port.",
                node,
            )
        else:
            return True

        return False

    @classmethod
    def _setup_cache(cls, capacity: int) -> None:
        """Internal method to initialize the LFU track cache.

        Parameters
        ----------
        capacity: int
            The number of track items to cache. Must be greater than 0.
        """
        if capacity <= 0:
            logger.warning("LFU Request cache capacity must be > 0. Not enabling cache.")
            return

        cls.__cache = LFUCache(capacity=capacity)
        logger.info(
            "Experimental request caching has been toggled ON. To disable run Pool.toggle_cache()"
        )

    @classmethod
    async def reconnect(cls) -> dict[str, Node]:
        """Reconnect all nodes in the pool that are currently disconnected.

        Returns
        -------
        dict[str, :class:`Node`]
            The mapping of nodes in the pool.

        """
        for node in cls.__nodes.values():
            if node.status is not NodeStatus.DISCONNECTED:
                continue

            await cls._attempt_connect(node, None)

        return cls.nodes

    @classmethod
    async def close(cls) -> None:
        """Close and clean up all :class:`~revvlink.Node` on this Pool.

        This calls :meth:`revvlink.Node.close` on each node.


        """
        for node in cls.__nodes.values():
            await node.close()

    @classproperty
    def nodes(cls) -> dict[str, Node]:
        """A mapping of :attr:`Node.identifier` to :class:`Node` that have
        previously been successfully connected.


            This property now returns a copy.
        """
        nodes = cls.__nodes.copy()
        return nodes

    @classmethod
    def get_node(cls, identifier: str | None = None, /, *, region: str | None = None) -> Node:
        """Retrieve a :class:`Node` from the :class:`Pool` with the given identifier.

        If no identifier is provided, this method returns the ``best`` node.
        If a ``region`` is provided, it tries to find the best node matching that region.

        Parameters
        ----------
        identifier: str | None
            An optional identifier to retrieve a :class:`Node`.
        region : str | None
            An optional region string to filter nodes for load balancing.

        Raises
        ------
        InvalidNodeException
            Raised when a Node can not be found, or no :class:`Node` exists
            on the :class:`Pool`.


            The ``id`` parameter was changed to ``identifier`` and is positional only.
        """
        if identifier:
            if identifier not in cls.__nodes:
                raise InvalidNodeException(
                    f'A Node with the identifier "{identifier}" does not exist.'
                )

            node = cls.__nodes[identifier]
            if revv_logger.enabled:
                revv_logger.debug(
                    "get_node — by identifier",
                    identifier=identifier,
                    node_id=node.identifier,
                    uri=node.uri,
                )
            return node

        nodes: list[Node] = [n for n in cls.__nodes.values() if n.status is NodeStatus.CONNECTED]
        if not nodes:
            raise InvalidNodeException(
                "No nodes are currently assigned to the revvlink.Pool in a CONNECTED state."
            )

        if region:
            region_nodes = [n for n in nodes if n.region == region]
            if region_nodes:
                selected = min(region_nodes, key=lambda n: n.penalty)
                if revv_logger.enabled:
                    revv_logger.debug(
                        "get_node — regional selection",
                        region=region,
                        node_id=selected.identifier,
                        penalty=round(selected.penalty, 2),
                        candidates=len(region_nodes),
                    )
                return selected
            if revv_logger.enabled:
                revv_logger.debug(
                    "get_node — no nodes in requested region, falling back to global best",
                    requested_region=region,
                )

        selected = min(nodes, key=lambda n: n.penalty)
        if revv_logger.enabled:
            revv_logger.debug(
                "get_node — global best selection",
                node_id=selected.identifier,
                penalty=round(selected.penalty, 2),
                total_connected=len(nodes),
            )
        return selected

    @classmethod
    async def _wait_for_healthy_nodes(cls, node: Node) -> list[Node]:
        """Internal helper to wait for at least one healthy node to become available.

        Used during failover to ensure there's a destination for player migration.

        Parameters
        ----------
        node: :class:`Node`
            The node that is currently failing.

        Returns
        -------
        list[:class:`Node`]
            A list of healthy nodes, or an empty list if none became available within the timeout.
        """
        retries = 50
        while retries > 0:
            connected_nodes = [
                n for n in cls.__nodes.values() if n.status is NodeStatus.CONNECTED and n != node
            ]
            if connected_nodes:
                return connected_nodes

            if revv_logger.enabled:
                revv_logger.debug(
                    "Node failover — waiting for healthy nodes...",
                    node_id=node.identifier,
                    retries_left=retries,
                )

            await asyncio.sleep(0.1)
            retries -= 1
        return []

    @classmethod
    async def _notify_failover(cls, player: Player, node: Node, new_node: Node) -> None:
        """Internal helper to notify the user via Discord about a node failover.

        Parameters
        ----------
        player: :class:`~revvlink.Player`
            The player being migrated.
        node: :class:`Node`
            The node that failed.
        new_node: :class:`Node`
            The node the player was moved to.
        """
        home = player.home
        if not home:
            logger.warning(
                "Node failover — shift successful for guild %s, "
                "but 'player.home' is NOT set. No notification sent.",
                player.guild.id if player.guild else "Unknown",
            )
            return

        from .utils import build_basic_layout

        description = "⚠️ Lavalink Node went down! Shifting player to healthy node..."
        view = build_basic_layout(description=description)

        _task = asyncio.create_task(home.send(view=view))
        cls._tasks.add(_task)
        _task.add_done_callback(cls._tasks.discard)
        logger.info(
            "Node failover — V2 shift notification sent to guild %s channel %s",
            player.guild.id if player.guild else "Unknown",
            home.id,
        )

    @classmethod
    async def _handle_node_failover(
        cls,
        node: Node,
        *,
        players: dict[int, Player] | None = None,
    ) -> None:
        """Internal method to migrate players from a failing or disconnecting node.

        Parameters
        ----------
        node: :class:`Node`
            The failing node.
        players: dict[int, :class:`~revvlink.Player`] | None
            A specific mapping of players to migrate. If ``None``, uses all players on the node.
        """
        players = players or node.players
        if not players:
            if revv_logger.enabled:
                revv_logger.debug("Node failover — no players to migrate", node_id=node.identifier)
            return

        connected_nodes = await cls._wait_for_healthy_nodes(node)

        if not connected_nodes:
            logger.warning(
                "Node %r is failing with %s active players, but no other "
                "CONNECTED nodes became available for failover after waiting.",
                node.identifier,
                len(players),
            )
            return

        if revv_logger.enabled:
            revv_logger.node(
                "Node failover initiated",
                node_id=node.identifier,
                active_players=len(players),
                available_nodes=len(connected_nodes),
            )

        for player in players.values():
            if player.node != node:
                continue

            endpoint = player._voice_state.get("voice", {}).get("endpoint")
            region = Pool.region_from_endpoint(endpoint)

            region_candidates = [n for n in connected_nodes if n.region == region]
            new_node = min(region_candidates or connected_nodes, key=lambda n: n.penalty)

            logger.info(
                "Node failover — migrating player in guild %s from %s to %s",
                player.guild.id if player.guild else "Unknown",
                node.identifier,
                new_node.identifier,
            )

            try:
                await player.switch_node(new_node)
                await cls._notify_failover(player, node, new_node)
            except Exception as e:
                logger.error(
                    "Automatic failover failed for player in guild %s "
                    "while switching from %s to %s: %s",
                    getattr(player.guild, "id", "Unknown"),
                    node.identifier,
                    new_node.identifier,
                    e,
                )

    @classmethod
    async def fetch_tracks(
        cls, query: str, /, *, node: Node | None = None
    ) -> list[Playable] | Playlist:
        """Search for tracks through the Pool.

        This method will use the provided ``node`` or find the best available node
        to perform the search. Results are automatically cached if the LFU cache is active.

        Parameters
        ----------
        query: str
            The search query to perform.
        node: :class:`Node` | None
            An optional node to use for the search. Defaults to None.

        Returns
        -------
        list[:class:`~revvlink.Playable`] | :class:`~revvlink.Playlist`
            The search results.

        Raises
        ------
        LavalinkLoadException
            Exception raised when Lavalink fails to load results based on your query.
        """

        encoded_query: str = urllib.parse.quote(query)

        if cls.__cache is not None:
            potential: list[Playable] | Playlist = cls.__cache.get(encoded_query, None)

            if potential:
                return potential

        node_: Node = node or cls.get_node()
        resp: LoadedResponse = await node_._fetch_tracks(encoded_query)

        return cls._handle_fetch_response(resp, encoded_query)

    @classmethod
    def _handle_fetch_response(
        cls, resp: LoadedResponse, encoded_query: str
    ) -> list[Playable] | Playlist:
        if resp["loadType"] == "track":
            track = Playable(data=resp["data"])
            if cls.__cache is not None and not track.is_stream:
                cls.__cache.put(encoded_query, [track])

            return [track]

        if resp["loadType"] == "search":
            tracks = [Playable(data=tdata) for tdata in resp["data"]]
            if cls.__cache is not None:
                cls.__cache.put(encoded_query, tracks)

            return tracks

        if resp["loadType"] == "playlist":
            playlist = Playlist(data=resp["data"])
            if cls.__cache is not None:
                cls.__cache.put(encoded_query, playlist)

            return playlist

        if resp["loadType"] == "error":
            raise LavalinkLoadException(data=resp["data"])

        return []

    @classmethod
    def cache(cls, capacity: int | None | bool = None) -> None:
        """Configure or resize the LFU track cache.

        Parameters
        ----------
        capacity: int | None | bool
            The new capacity for the cache.
            Passing ``None``, ``False``, or a value ``<= 0`` will disable the cache.

        Raises
        ------
        ValueError
            The capacity provided was not an integer, None, or boolean.
        """
        if capacity in (None, False) or capacity <= 0:
            cls.__cache = None
            return

        if not isinstance(capacity, int):  # type: ignore
            raise ValueError("The LFU cache expects an integer, None or bool.")

        cls.__cache = LFUCache(capacity=capacity)

    @classmethod
    def has_cache(cls) -> bool:
        """Whether the LFU track cache is currently active.

        Returns
        -------
        bool
            True if active, False otherwise.
        """
        return cls.__cache is not None
