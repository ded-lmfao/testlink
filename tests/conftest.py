from typing import Any

import pytest

from revvlink.node import REGIONS
from revvlink.tracks import Playable


@pytest.fixture(autouse=True)
def reset_pool_regions():
    """Reset Pool._regions to default before and after each test."""
    from revvlink.node import Pool

    original = Pool._regions
    Pool._regions = REGIONS
    yield
    Pool._regions = original


@pytest.fixture
def dummy_track_payload() -> dict[str, Any]:
    return {
        "encoded": "QAAAjwIAJVJpY2sgQXN0bGV5IC0gTmV2ZXIgR29ubmEgR2l2ZSBZb3UgVXAAAAAOUmljayBBc3RsZXkAAAAAAANZPAAAACtRRzRyd08tY19PNAAAABN5b3V0dWJlAAAAA3l0bQAAAAEAAAA=",  # noqa: E501
        "info": {
            "identifier": "dQw4w9WgXcQ",
            "isSeekable": True,
            "author": "Rick Astley",
            "length": 213000,
            "isStream": False,
            "position": 0,
            "title": "Never Gonna Give You Up",
            "uri": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "artworkUrl": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "isrc": None,
            "sourceName": "youtube",
        },
        "pluginInfo": {},
    }


@pytest.fixture
def dummy_track_payload2() -> dict[str, Any]:
    return {
        "encoded": "QAAAjwIAJVJpY2sgQXN0bGV5IC0gTmV2ZXIgR29ubmEgR2l2ZSBZb3UgVXAAAAAOUmljayBBc3RsZXkAAAAAAANZPAAAACtRRzRyd08tY19PNAAAABN5b3V0dWJlAAAAA3l0bQAAAAEAAAAy",  # noqa: E501
        "info": {
            "identifier": "oHg5SJYRHA0",
            "isSeekable": True,
            "author": "Rick Astley",
            "length": 213000,
            "isStream": False,
            "position": 0,
            "title": "Never Gonna Give You Up 2",
            "uri": "https://www.youtube.com/watch?v=oHg5SJYRHA0",
            "artworkUrl": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "isrc": None,
            "sourceName": "youtube",
        },
        "pluginInfo": {},
    }


@pytest.fixture
def dummy_playlist_payload(dummy_track_payload) -> dict[str, Any]:
    return {
        "info": {"name": "My Playlist", "selectedTrack": 0},
        "pluginInfo": {
            "type": "playlist",
            "url": "https://example.com/playlist",
            "artworkUrl": "https://example.com/art.jpg",
            "author": "Author",
        },
        "tracks": [dummy_track_payload],
    }


@pytest.fixture
def dummy_playable(dummy_track_payload) -> Playable:
    return Playable(dummy_track_payload)


@pytest.fixture
def dummy_playable2(dummy_track_payload2) -> Playable:
    return Playable(dummy_track_payload2)
