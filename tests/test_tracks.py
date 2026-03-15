from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from revvlink.tracks import Album, Artist, Playable, Playlist, PlaylistInfo


def test_playable_initialization(dummy_track_payload: dict[str, Any]):
    track = Playable(dummy_track_payload)

    assert track.encoded == dummy_track_payload["encoded"]
    assert track.identifier == "dQw4w9WgXcQ"
    assert track.is_seekable is True
    assert track.author == "Rick Astley"
    assert track.length == 213000
    assert track.is_stream is False
    assert track.position == 0
    assert track.title == "Never Gonna Give You Up"
    assert track.uri == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert track.artwork == "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
    assert track.isrc is None
    assert track.source == "youtube"
    assert track.raw_data == dummy_track_payload

    # testing methods
    assert str(track) == "Never Gonna Give You Up"
    assert "Never Gonna Give You Up" in repr(track)
    assert hash(track) == hash(track.encoded)

    # test extras
    track.extras = {"req": "test_user"}
    assert track.extras.req == "test_user"


def test_playable_equality(
    dummy_track_payload: dict[str, Any], dummy_track_payload2: dict[str, Any]
):
    t1 = Playable(dummy_track_payload)
    t2 = Playable(dummy_track_payload)
    t3 = Playable(dummy_track_payload2)

    assert t1 == t2
    assert t1 != t3
    assert t1 != "not_a_track"


def test_playlist_info_initialization(dummy_playlist_payload: dict[str, Any]):
    info = PlaylistInfo(dummy_playlist_payload)

    assert info.name == "My Playlist"
    assert info.selected == 0
    assert info.tracks == 1
    assert info.type == "playlist"
    assert info.url == "https://example.com/playlist"
    assert info.artwork == "https://example.com/art.jpg"
    assert info.author == "Author"

    assert str(info) == "My Playlist"
    assert "My Playlist" in repr(info)
    assert len(info) == 1


def test_playlist_initialization(dummy_playlist_payload: dict[str, Any]):
    pl = Playlist(dummy_playlist_payload)

    assert pl.name == "My Playlist"
    assert len(pl) == 1
    assert str(pl) == "My Playlist"
    assert "My Playlist" in repr(pl)

    track = pl[0]
    assert isinstance(track, Playable)
    assert track.title == "Never Gonna Give You Up"
    assert track.playlist is not None
    assert track.playlist.name == "My Playlist"


def test_playlist_operations(dummy_playlist_payload: dict[str, Any]):
    pl = Playlist(dummy_playlist_payload)
    t1 = pl[0]

    assert t1 in pl

    # Equality
    pl2 = Playlist(dummy_playlist_payload)
    assert pl == pl2
    assert pl != "not_a_playlist"

    # Extras
    pl.extras = {"pl_req": "user_id"}
    assert t1.extras.pl_req == "user_id"

    # Iteration
    items = list(iter(pl))
    assert len(items) == 1

    # Pop
    track = pl.pop(0)
    assert track == t1
    assert len(pl) == 0


def test_album_artist():
    data = {
        "albumName": "Best Album",
        "albumUrl": "http://album",
        "artistUrl": "http://artist",
        "artistArtworkUrl": "http://art",
    }

    album = Album(data=data)
    assert album.name == "Best Album"
    assert album.url == "http://album"

    artist = Artist(data=data)
    assert artist.url == "http://artist"
    assert artist.artwork == "http://art"


def test_playlist_reversed_and_contains(dummy_playlist_payload: dict[str, Any]):
    pl = Playlist(dummy_playlist_payload)
    t = pl[0]

    # __reversed__
    rev = list(reversed(pl))
    assert len(rev) == 1
    assert rev[0] == t

    # __contains__
    assert t in pl


def test_playlist_track_extras(dummy_playlist_payload: dict[str, Any]):
    pl = Playlist(dummy_playlist_payload)
    pl.track_extras(requester="user_123")
    assert pl[0].requester == "user_123"  # type: ignore[attr-defined]


def test_playlist_extras_setter_with_namespace(dummy_playlist_payload: dict[str, Any]):
    from revvlink.utils import ExtrasNamespace

    pl = Playlist(dummy_playlist_payload)
    ns = ExtrasNamespace({"hello": "world"})
    pl.extras = ns
    assert pl.extras.hello == "world"
    assert pl[0].extras.hello == "world"


def test_playlist_slice(dummy_playlist_payload: dict[str, Any]):
    pl = Playlist(dummy_playlist_payload)
    sliced = pl[0:1]
    assert len(sliced) == 1


def test_playable_extras_namespace(dummy_track_payload: dict[str, Any]):
    from revvlink.utils import ExtrasNamespace

    track = Playable(dummy_track_payload)
    ns = ExtrasNamespace({"key": "val"})
    track.extras = ns
    assert track.extras.key == "val"

    track.extras = {"k2": "v2"}
    assert track.extras.k2 == "v2"
    assert dict(track.extras) == {"k2": "v2"}


def test_playable_plugin_fields(dummy_track_payload: dict[str, Any]):
    # Test with plugin info populated
    payload = dict(dummy_track_payload)
    payload["pluginInfo"] = {
        "albumName": "My Album",
        "albumUrl": "http://album.com",
        "artistUrl": "http://artist.com",
        "artistArtworkUrl": "http://art.com",
        "previewUrl": "http://preview.com",
        "isPreview": True,
    }
    track = Playable(payload)
    assert track.album.name == "My Album"
    assert track.artist.url == "http://artist.com"
    assert track.preview_url == "http://preview.com"
    assert track.is_preview is True
    assert track.recommended is False


@pytest.mark.asyncio
async def test_playable_search_default():
    with patch("revvlink.Pool.fetch_tracks", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = "mocked_search_result"

        res = await Playable.search("hello")
        mock_fetch.assert_called_once_with("ytmsearch:hello", node=None)
        assert res == "mocked_search_result"


@pytest.mark.asyncio
async def test_playable_search_url():
    with patch("revvlink.Pool.fetch_tracks", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = "mocked_search_result"

        # When querying a URL, it ignores source
        await Playable.search("https://youtube.com/watch?v=123")
        mock_fetch.assert_called_once_with("https://youtube.com/watch?v=123", node=None)


@pytest.mark.asyncio
async def test_playable_search_no_source():
    with patch("revvlink.Pool.fetch_tracks", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = "mocked_search_result"

        # When querying without source
        await Playable.search("hello", source=None)
        mock_fetch.assert_called_once_with("hello", node=None)
