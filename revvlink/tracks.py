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

from typing import TYPE_CHECKING, Any, TypeAlias, overload

import yarl

import revvlink

from .enums import TrackSource
from .utils import ExtrasNamespace

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .node import Node
    from .types.tracks import (
        PlaylistInfoPayload,
        PlaylistPayload,
        TrackInfoPayload,
        TrackPayload,
    )


__all__ = ("Album", "Artist", "Playable", "Playlist", "PlaylistInfo", "Search")


_source_mapping: dict[TrackSource | str | None, str] = {
    TrackSource.YouTube: "ytsearch",
    TrackSource.SoundCloud: "scsearch",
    TrackSource.YouTubeMusic: "ytmsearch",
}

# Plugin to source manager mapping for validation
_plugin_sources: dict[str, str] = {
    "spsearch": "sp",
    "spotify": "sp",
    "scsearch": "soundcloud",
    "ytsearch": "youtube",
    "ytmsearch": "youtube",
}


Search: TypeAlias = "list[Playable] | Playlist"


class Album:
    """Container class representing Album data received via Lavalink.

    Attributes
    ----------
    name: str | None
        The album name. Could be ``None``.
    url: str | None
        The album url. Could be ``None``.
    """

    def __init__(self, *, data: dict[Any, Any]) -> None:
        self.name: str | None = data.get("albumName")
        self.url: str | None = data.get("albumUrl")


class Artist:
    """Container class representing Artist data received via Lavalink.

    Attributes
    ----------
    url: str | None
        The artist url. Could be ``None``.
    artwork: str | None
        The artist artwork url. Could be ``None``.
    """

    def __init__(self, *, data: dict[Any, Any]) -> None:
        self.url: str | None = data.get("artistUrl")
        self.artwork: str | None = data.get("artistArtworkUrl")


class Playable:
    """The RevvLink Playable object which represents all tracks in RevvLink 3.

    .. note::

        You should not construct this class manually.

    .. container:: operations

        .. describe:: str(track)

            The title of this playable.

        .. describe:: repr(track)

            The official string representation of this playable.

        .. describe:: track == other

            Whether this track is equal to another. Checks both the track encoding and identifier.
    """

    def __init__(self, data: TrackPayload, *, playlist: PlaylistInfo | None = None) -> None:
        info: TrackInfoPayload = data["info"]

        self._encoded: str = data["encoded"]
        self._identifier: str = info["identifier"]
        self._is_seekable: bool = info["isSeekable"]
        self._author: str = info["author"]
        self._length: int = info["length"]
        self._is_stream: bool = info["isStream"]
        self._position: int = info["position"]
        self._title: str = info["title"]
        self._uri: str | None = info.get("uri")
        self._artwork: str | None = info.get("artworkUrl")
        self._isrc: str | None = info.get("isrc")
        self._source: str = info["sourceName"]

        plugin: dict[Any, Any] = data["pluginInfo"]
        self._album: Album = Album(data=plugin)
        self._artist: Artist = Artist(data=plugin)

        self._preview_url: str | None = plugin.get("previewUrl")
        self._is_preview: bool | None = plugin.get("isPreview")

        self._playlist = playlist
        self._recommended: bool = False

        self._extras: ExtrasNamespace = ExtrasNamespace(data.get("userData", {}))

        self._raw_data = data

    def __hash__(self) -> int:
        return hash(self.encoded)

    def __str__(self) -> str:
        return self.title

    def __repr__(self) -> str:
        return f"Playable(source={self.source}, title={self.title}, identifier={self.identifier})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Playable):
            return NotImplemented

        return self.encoded == other.encoded or self.identifier == other.identifier

    @property
    def encoded(self) -> str:
        """The encoded track string from Lavalink.

        Returns
        -------
        str
            The base64 encoded track string.
        """
        return self._encoded

    @property
    def identifier(self) -> str:
        """The identifier of this track from its source.

        E.g. YouTube ID or Spotify ID.

        Returns
        -------
        str
            The track identifier.
        """
        return self._identifier

    @property
    def is_seekable(self) -> bool:
        """Whether this track supports seeking.

        Returns
        -------
        bool
            True if seekable, False otherwise.
        """
        return self._is_seekable

    @property
    def author(self) -> str:
        """The author or artist of this track.

        Returns
        -------
        str
            The track author.
        """
        return self._author

    @property
    def length(self) -> int:
        """The duration of this track in milliseconds.

        Returns
        -------
        int
            The track length in ms.
        """
        return self._length

    @property
    def is_stream(self) -> bool:
        """Whether this track is an ongoing stream.

        Returns
        -------
        bool
            True if a stream, False otherwise.
        """
        return self._is_stream

    @property
    def position(self) -> int:
        """The starting position of this track in milliseconds.

        Returns
        -------
        int
            The start position in ms.
        """
        return self._position

    @property
    def title(self) -> str:
        """The title or name of this track.

        Returns
        -------
        str
            The track title.
        """
        return self._title

    @property
    def uri(self) -> str | None:
        """The URL to this track.

        Returns
        -------
        str | None
            The track URI, or ``None`` if not available.
        """
        return self._uri

    @property
    def artwork(self) -> str | None:
        """The URL to the artwork for this track.

        Returns
        -------
        str | None
            The artwork URL, or ``None`` if not available.
        """
        return self._artwork

    @property
    def isrc(self) -> str | None:
        """The International Standard Recording Code (ISRC) for this track.

        Returns
        -------
        str | None
            The ISRC, or ``None`` if not available.
        """
        return self._isrc

    @property
    def source(self) -> str:
        """The source name for this track.

        E.g. "spotify" or "youtube".

        Returns
        -------
        str
            The source name.
        """
        return self._source

    @property
    def album(self) -> Album:
        """The album data associated with this track.

        Returns
        -------
        :class:`Album`
            The album information.
        """
        return self._album

    @property
    def artist(self) -> Artist:
        """The artist data associated with this track.

        Returns
        -------
        :class:`Artist`
            The artist information.
        """
        return self._artist

    @property
    def preview_url(self) -> str | None:
        """The URL to a short preview of this track.

        Returns
        -------
        str | None
            The preview URL, or ``None`` if not available.
        """
        return self._preview_url

    @property
    def is_preview(self) -> bool | None:
        """Whether this track is a short preview.

        Returns
        -------
        bool | None
            True if a preview, False otherwise, or ``None`` if unknown.
        """
        return self._is_preview

    @property
    def playlist(self) -> PlaylistInfo | None:
        """The playlist information if this track part of one.

        Returns
        -------
        :class:`PlaylistInfo` | None
            The playlist info, or ``None`` if not in a playlist.
        """
        return self._playlist

    @property
    def recommended(self) -> bool:
        """Whether this track was added via the AutoPlay feature.

        Returns
        -------
        bool
            True if recommended, False otherwise.
        """
        return self._recommended

    @property
    def extras(self) -> ExtrasNamespace:
        """Property returning a :class:`~revvlink.ExtrasNamespace` of extras
        for this :class:`Playable`.

        You can set this property with a :class:`dict` of valid :class:`str`
        keys to any valid ``JSON`` value, or a :class:`~revvlink.ExtrasNamespace`.

        If a dict is passed, it will be converted into an
        :class:`~revvlink.ExtrasNamespace`, which can be converted back to a
        dict with dict(...). Additionally, you can also use list or tuple on
        :class:`~revvlink.ExtrasNamespace`.

        The extras dict will be sent to Lavalink as the ``userData`` field.


        .. warning::

            This is only available when using Lavalink 4+ (**Non BETA**) versions.


        Examples
        --------

            .. code:: python

                track: revvlink.Playable = revvlink.Playable.search("QUERY")
                track.extras = {"requester_id": 1234567890}

                # later...
                print(track.extras.requester_id)
                # or
                print(dict(track.extras)["requester_id"])


        """
        return self._extras

    @extras.setter
    def extras(self, value: ExtrasNamespace | dict[str, Any]) -> None:
        if isinstance(value, ExtrasNamespace):
            self._extras = value
        else:
            self._extras = ExtrasNamespace(value)

    @property
    def raw_data(self) -> TrackPayload:
        """The raw data for this ``Playable`` received via ``Lavalink``.

        You can use this data to reconstruct this ``Playable`` object.


        Examples
        --------

            .. code:: python3

                # For example purposes...
                old_data = track.raw_data

                # Later...
                track: revvlink.Playable = revvlink.Playable(old_data)
        """
        return self._raw_data

    @staticmethod
    async def _ensure_node_info(node: Node | None) -> Node | None:
        try:
            n = node or revvlink.Pool.get_node()
        except Exception:
            return None

        if n._info is None:
            try:
                await n.refresh_info()
            except Exception:
                pass
        return n

    @classmethod
    async def search(
        cls,
        query: str,
        /,
        *,
        source: TrackSource | str | None = TrackSource.YouTubeMusic,
        node: Node | None = None,
    ) -> Search:
        """Search for a list of :class:`~revvlink.Playable` or a
        :class:`~revvlink.Playlist`, with the given query.

        .. note::

            This method differs from :meth:`revvlink.Pool.fetch_tracks` in that
            it will apply a relevant search prefix for you when a URL is
            **not** provided. This prefix can be controlled via the
            ``source`` keyword argument.


        .. note::

            This method of searching is preferred over, :meth:`revvlink.Pool.fetch_tracks`.


        Parameters
        ----------
        query: str
            The query to search tracks for. If this is **not** a URL based search,
            this method will provide an appropriate search prefix based on what is
            provided to the ``source`` keyword only parameter, or it's default.

            If this query **is a URL**, a search prefix will **not** be used.
        source: :class:`TrackSource` | str | None
            This parameter determines which search prefix to use when searching for tracks.
            If ``None`` is provided, no prefix will be used, however this behaviour is
            default regardless of what is provided **when a URL is found**.

            For basic searches, E.g. YouTube, YouTubeMusic and SoundCloud,
            see: :class:`revvlink.TrackSource`. Otherwise, a ``str`` may be
            provided for plugin based searches, E.g. "spsearch:" for the
            LavaSrc Spotify based search.

            Defaults to :attr:`revvlink.TrackSource.YouTubeMusic` which is
            equivalent to "ytmsearch:".
        node: :class:`~revvlink.Node` | None
            An optional :class:`~revvlink.Node` to use when searching for
            tracks. Defaults to ``None``, which uses the
            :class:`~revvlink.Pool`'s automatic node selection.


        Returns
        -------
        :class:`revvlink.Search`
            A list of [:class:`Playable`] or a [:class:`Playlist`].

        Raises
        ------
        LavalinkLoadException
            Exception raised when Lavalink fails to load results based on your query.


        Examples
        --------

        .. code:: python3

            # Search for tracks, with the default "ytsearch:" prefix.
            tracks: revvlink.Search = await revvlink.Playable.search("Ocean Drive")
            if not tracks:
                # No tracks were found...
                ...

            # Search for tracks, with a URL.
            tracks: revvlink.Search = await revvlink.Playable.search("https://www.youtube.com/watch?v=KDxJlW6cxRk")
            ...

            # Search for tracks, using Spotify and the LavaSrc Plugin.
            tracks: revvlink.Search = await revvlink.Playable.search(
                "4b93D55xv3YCH5mT4p6HPn", source="spsearch"
            )
            ...

            # Search for tracks, using Spotify and the LavaSrc Plugin, with a URL.
            tracks: revvlink.Search = await revvlink.Playable.search("https://open.spotify.com/track/4b93D55xv3YCH5mT4p6HPn")
            ...

            # Search for a playlist, using Spotify and the LavaSrc Plugin.
            # or alternatively any other playlist URL from another source like YouTube.
            tracks: revvlink.Search = await revvlink.Playable.search("https://open.spotify.com/playlist/37i9dQZF1DWXRqgorJj26U")
            ...

            # Set extras on a playlist result.
            playlist: revvlink.Playlist = await revvlink.Playable.search("https://open.spotify.com/playlist/37i9dQZF1DWXRqgorJj26U")
            playlist.extras = {"requester_id": 1234567890}

            # later...
            print(track.extras.requester_id)
            # or
            print(dict(track.extras)["requester_id"])


        """
        prefix: TrackSource | str | None = _source_mapping.get(source, source)
        check = yarl.URL(query)

        # Validate source/plugin if not a URL
        if not check.host and prefix:
            await cls._ensure_node_info(node)

        if check.host:
            return await revvlink.Pool.fetch_tracks(query, node=node)

        if not prefix:
            term: str = query
        else:
            term = (
                f"{prefix.removesuffix(':')}:{query}"
                if isinstance(prefix, str)
                else f"{prefix}:{query}"
            )

        return await revvlink.Pool.fetch_tracks(term, node=node)


class Playlist:
    """The revvlink Playlist container class.

    This class is created and returned via both :meth:`Playable.search` and
    :meth:`revvlink.Pool.fetch_tracks`.

    It contains various information about the playlist and a list of
    :class:`Playable` that can be used directly in
    :meth:`revvlink.Player.play`. See below for various supported operations.


    .. warning::

        You should not instantiate this class manually,
        use :meth:`Playable.search` or :meth:`revvlink.Pool.fetch_tracks` instead.


    .. warning::

        You can not use ``.search`` directly on this class, see: :meth:`Playable.search`.


    .. note::

        This class can be directly added to :class:`revvlink.Queue` identical
        to :class:`Playable`. When added, all tracks contained in this
        playlist, will be individually added to the :class:`revvlink.Queue`.


    .. container:: operations

        .. describe:: str(x)

            Return the name associated with this playlist.

        .. describe:: repr(x)

            Return the official string representation of this playlist.

        .. describe:: x == y

            Compare the equality of playlist.

        .. describe:: len(x)

            Return an integer representing the amount of tracks contained in this playlist.

        .. describe:: x[0]

            Return a track contained in this playlist with the given index.

        .. describe:: x[0:2]

            Return a slice of tracks contained in this playlist.

        .. describe:: for x in y

            Iterate over the tracks contained in this playlist.

        .. describe:: reversed(x)

            Reverse the tracks contained in this playlist.

        .. describe:: x in y

            Check if a :class:`Playable` is contained in this playlist.


    Attributes
    ----------
    name: str
        The name of this playlist.
    selected: int
        The index of the selected track from Lavalink.
    tracks: list[:class:`Playable`]
        A list of :class:`Playable` contained in this playlist.
    type: str | None
        An optional ``str`` identifying the type of playlist this is.
        Only available when a plugin is used.
    url: str | None
        An optional ``str`` to the URL of this playlist. Only available when a plugin is used.
    artwork: str | None
        An optional ``str`` to the artwork of this playlist. Only available when a plugin is used.
    author: str | None
        An optional ``str`` of the author of this playlist. Only available when a plugin is used.
    """

    def __init__(self, data: PlaylistPayload) -> None:
        info: PlaylistInfoPayload = data["info"]
        self.name: str = info["name"]
        self.selected: int = info["selectedTrack"]

        playlist_info: PlaylistInfo = PlaylistInfo(data)
        self.tracks: list[Playable] = [
            Playable(data=track, playlist=playlist_info) for track in data["tracks"]
        ]

        plugin: dict[Any, Any] = data["pluginInfo"]
        self.type: str | None = plugin.get("type")
        self.url: str | None = plugin.get("url")
        self.artwork: str | None = plugin.get("artworkUrl")
        self.author: str | None = plugin.get("author")
        self._extras: ExtrasNamespace = ExtrasNamespace(data.get("userData", {}))

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Playlist(name={self.name}, tracks={len(self.tracks)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Playlist):
            return NotImplemented

        return self.name == other.name and self.tracks == other.tracks

    def __len__(self) -> int:
        return len(self.tracks)

    @overload
    def __getitem__(self, index: int) -> Playable: ...

    @overload
    def __getitem__(self, index: slice) -> list[Playable]: ...

    def __getitem__(self, index: int | slice) -> Playable | list[Playable]:
        return self.tracks[index]

    def __iter__(self) -> Iterator[Playable]:
        return self.tracks.__iter__()

    def __reversed__(self) -> Iterator[Playable]:
        return self.tracks.__reversed__()

    def __contains__(self, item: Playable) -> bool:
        return item in self.tracks

    def pop(self, index: int = -1) -> Playable:
        return self.tracks.pop(index)

    def track_extras(self, **attrs: object) -> None:
        """Method which sets attributes to all :class:`Playable` in this
        playlist, with the provided keyword arguments.

        This is useful when you need to attach state to your :class:`Playable`,
        E.g. create a requester attribute.

        .. warning::

            If you try to override any existing property of :class:`Playable` this method will fail.


        Parameters
        ----------
        **attrs
            The keyword arguments to set as attribute name=value on each :class:`Playable`.

        Examples
        --------

            .. code:: python3

                playlist.track_extras(requester=ctx.author)

                track: revvlink.Playable = playlist[0]
                print(track.requester)
        """
        for track in self.tracks:
            for name, value in attrs.items():
                setattr(track, name, value)

    @property
    def extras(self) -> ExtrasNamespace:
        """The extras associated with this :class:`Playlist`.

        This property can be set with a :class:`dict` of valid :class:`str`
        keys to any valid ``JSON`` value, or a :class:`~revvlink.ExtrasNamespace`.

        If a dict is passed, it will be converted into an
        :class:`~revvlink.ExtrasNamespace`, which can be converted back to a
        dict with ``dict(...)``. Additionally, you can also use list or tuple
        on :class:`~revvlink.ExtrasNamespace`.

        The extras dict will be sent to Lavalink as the ``userData`` field for
        each track in the playlist.

        .. warning::

            This is only available when using Lavalink 4+ (**Non BETA**) versions.

        Examples
        --------
        .. code:: python

            playlist: revvlink.Search = revvlink.Playable.search("QUERY")
            playlist.extras = {"requester_id": 1234567890}

            # later...
            print(track.extras.requester_id)
            # or
            print(dict(track.extras)["requester_id"])

        Returns
        -------
        :class:`~revvlink.ExtrasNamespace`
            The playlist extras.
        """
        return self._extras

    @extras.setter
    def extras(self, value: ExtrasNamespace | dict[str, Any]) -> None:
        if isinstance(value, ExtrasNamespace):
            self._extras = value
        else:
            self._extras = ExtrasNamespace(value)

        for track in self.tracks:
            track.extras = value


class PlaylistInfo:
    """The revvlink PlaylistInfo container class.

    It contains various information about the playlist but **does not**
    contain the tracks associated with this playlist.

    This class provides information about the original
    :class:`revvlink.Playlist` on tracks.

    Attributes
    ----------
    name: str
        The name of this playlist.
    selected: int
        The index of the selected track from Lavalink.
    tracks: int
        The amount of tracks this playlist originally contained.
    type: str | None
        An optional ``str`` identifying the type of playlist this is.
        Only available when a plugin is used.
    url: str | None
        An optional ``str`` to the URL of this playlist.
        Only available when a plugin is used.
    artwork: str | None
        An optional ``str`` to the artwork of this playlist.
        Only available when a plugin is used.
    author: str | None
        An optional ``str`` of the author of this playlist.
        Only available when a plugin is used.
    """

    __slots__ = ("artwork", "author", "name", "selected", "tracks", "type", "url")

    def __init__(self, data: PlaylistPayload) -> None:
        info: PlaylistInfoPayload = data["info"]
        self.name: str = info["name"]
        self.selected: int = info["selectedTrack"]

        self.tracks: int = len(data["tracks"])

        plugin: dict[Any, Any] = data["pluginInfo"]
        self.type: str | None = plugin.get("type")
        self.url: str | None = plugin.get("url")
        self.artwork: str | None = plugin.get("artworkUrl")
        self.author: str | None = plugin.get("author")

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"PlaylistInfo(name={self.name}, tracks={self.tracks})"

    def __len__(self) -> int:
        """The number of tracks in the playlist.

        Returns
        -------
        int
            The number of tracks.
        """
        return self.tracks
