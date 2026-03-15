import pytest

from revvlink.lfu import MISSING, CapacityZero, LFUCache, NotFound


def test_missing_sentinel():
    assert bool(MISSING) is False
    assert repr(MISSING) == "..."
    assert hash(MISSING) == 0
    assert MISSING != 1


def test_notfound_sentinel():
    assert bool(NotFound) is False
    assert repr(NotFound) == "NotFound"


def test_lfu_cache_basic():
    cache = LFUCache(capacity=2)
    assert cache.capacity == 2
    assert len(cache) == 0

    # put and get
    cache["a"] = 1
    assert cache["a"] == 1
    assert len(cache) == 1

    cache.put("b", 2)
    assert cache.get("b") == 2
    assert len(cache) == 2


def test_lfu_cache_eviction():
    cache = LFUCache(capacity=2)
    cache["a"] = 1
    cache["b"] = 2

    # Access a to increase frequency
    _ = cache["a"]

    # Put c, which should evict b (least frequently used)
    cache["c"] = 3

    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.get("b") is NotFound
    assert cache.get("b", default=None) is None


def test_lfu_cache_exceptions():
    cache = LFUCache(capacity=0)

    with pytest.raises(CapacityZero):
        cache.put("a", 1)

    cache2 = LFUCache(capacity=2)
    with pytest.raises(KeyError):
        _ = cache2["doesntexist"]


def test_lfu_cache_update_existing():
    cache = LFUCache(capacity=2)
    cache["a"] = 1
    cache["a"] = 10
    assert cache["a"] == 10


def test_lfu_popleft_empty_and_remove_none():
    """popleft returns None on empty cache, remove(None) returns gracefully."""
    cache = LFUCache(capacity=2)

    # head.later is None
    assert cache._freq_map[1].popleft() is None

    # remove(None) does nothing
    cache._freq_map[1].remove(None)
