"""
Tests for revvlink.queue.Queue.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from revvlink.enums import QueueMode
from revvlink.exceptions import QueueEmpty
from revvlink.queue import Queue
from revvlink.tracks import Playable

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_track(identifier="test_id"):
    """Create a mock Playable track."""
    track = MagicMock(spec=Playable)
    track.identifier = identifier
    track.encoded = f"encoded_{identifier}"
    # Mocking __eq__ is important for queue operations
    track.__eq__.side_effect = lambda other: (
        isinstance(other, Playable) and other.identifier == track.identifier
    )
    return track


# ─── Tests ───────────────────────────────────────────────────────────────────


def test_queue_init():
    """Queue initializes with correct defaults."""
    q = Queue()
    assert len(q) == 0
    assert q.mode == QueueMode.normal
    assert q.history is not None
    assert isinstance(q.history, Queue)
    assert q.history.history is None


def test_queue_put_and_get():
    """put and get work as expected."""
    q = Queue()
    t1 = _make_track("1")
    t2 = _make_track("2")

    q.put(t1)
    q.put(t2)
    assert len(q) == 2

    assert q.get() == t1
    assert len(q) == 1
    assert q.get() == t2
    assert len(q) == 0

    with pytest.raises(QueueEmpty):
        q.get()


def test_queue_put_list():
    """put works with a list of tracks."""
    q = Queue()
    tracks = [_make_track(str(i)) for i in range(3)]
    added = q.put(tracks)
    assert added == 3
    assert len(q) == 3


def test_queue_put_invalid_type():
    """put raises TypeError for non-Playable objects."""
    q = Queue()
    with pytest.raises(TypeError):
        q.put("not a track")


def test_queue_peek():
    """peek returns track without removing it."""
    q = Queue()
    t = _make_track()
    q.put(t)
    assert q.peek() == t
    assert len(q) == 1


def test_queue_pop():
    """get_at (aliased to pop in some contexts, but let's test get_at) removes at index."""
    q = Queue()
    t1 = _make_track("1")
    t2 = _make_track("2")
    q.put([t1, t2])

    assert q.get_at(1) == t2
    assert len(q) == 1
    assert q[0] == t1


def test_queue_delete():
    """delete removes track at index."""
    q = Queue()
    t1 = _make_track("1")
    t2 = _make_track("2")
    q.put([t1, t2])

    q.delete(0)
    assert len(q) == 1
    assert q[0] == t2


def test_queue_clear():
    """clear removes all items."""
    q = Queue()
    q.put([_make_track("1"), _make_track("2")])
    q.clear()
    assert len(q) == 0


def test_queue_shuffle():
    """shuffle reorders items (probabilistic)."""
    q = Queue()
    tracks = [_make_track(str(i)) for i in range(100)]
    q.put(tracks)
    original = list(q)
    q.shuffle()
    shuffled = list(q)
    assert len(shuffled) == 100
    assert shuffled != original  # Highly unlikely to be same


def test_queue_swap():
    """swap exchanges items at two indices."""
    q = Queue()
    t1 = _make_track("1")
    t2 = _make_track("2")
    q.put([t1, t2])
    q.swap(0, 1)
    assert q[0] == t2
    assert q[1] == t1


def test_queue_loop_mode():
    """QueueMode.loop returns same track again."""
    q = Queue()
    t = _make_track()
    q.put(t)
    q.mode = QueueMode.loop

    assert q.get() == t
    assert q.get() == t  # Still there
    assert len(q) == 0  # It's "loaded", not in _items


def test_queue_loop_all_mode():
    """QueueMode.loop_all refills from history."""
    q = Queue()
    t = _make_track()
    q.put(t)
    q.mode = QueueMode.loop_all

    # Simulate track being played and added to history
    played = q.get()
    q.history.put(played)

    # Now queue is empty, next get should refill from history
    assert len(q) == 0
    refilled = q.get()
    assert refilled == t
    assert len(q) == 0  # because it moved from history to loaded


@pytest.mark.asyncio
async def test_queue_get_wait():
    """get_wait waits for an item to be put."""
    q = Queue()
    t = _make_track()

    async def delayed_put():
        await asyncio.sleep(0.1)
        q.put(t)

    task = asyncio.create_task(delayed_put())
    result = await q.get_wait()
    assert result == t
    await task


@pytest.mark.asyncio
async def test_queue_put_wait():
    """put_wait adds item asynchronously."""
    q = Queue()
    t = _make_track()
    added = await q.put_wait(t)
    assert added == 1
    assert len(q) == 1


def test_queue_protocols():
    """Test various python protocols."""
    q = Queue()
    t = _make_track()
    q.put(t)

    assert len(q) == 1
    assert t in q
    assert bool(q) is True
    assert str(q).startswith("Queue")

    for item in q:
        assert item == t

    q.clear()
    assert bool(q) is False


def test_queue_copy():
    """copy creates a new queue with same items."""
    q = Queue()
    t = _make_track()
    q.put(t)
    cp = q.copy()
    assert len(cp) == 1
    assert cp[0] == t
    assert cp is not q


def test_queue_reset():
    """reset clears everything and cancels waiters."""
    q = Queue()
    q.put(_make_track())
    q.history.put(_make_track())
    q.mode = QueueMode.loop

    q.reset()
    assert len(q) == 0
    assert len(q.history) == 0
    assert q.mode == QueueMode.normal
    assert q.loaded is None


def test_queue_remove():
    """remove removes specific track."""
    q = Queue()
    t1 = _make_track("1")
    t2 = _make_track("2")
    q.put([t1, t2, t1])

    removed = q.remove(t1, count=1)
    assert removed == 1
    assert len(q) == 2
    assert q[0] == t2
    assert q[1] == t1

    q.remove(t1, count=None)  # remove all
    assert len(q) == 1
    assert q[0] == t2


def test_queue_properties():
    """Test count and is_empty properties."""
    q = Queue()
    q.put(_make_track())
    assert q.count == 1
    assert q.is_empty is False
    q.clear()
    assert q.is_empty is True


def test_queue_repr_and_call():
    """Test __repr__ and __call__ protocols."""
    q = Queue()
    t = _make_track()
    q(t)  # __call__
    assert len(q) == 1
    assert "Queue(items=1" in repr(q)


def test_queue_del_and_reversed():
    """Test __delitem__ and __reversed__ protocols."""
    q = Queue()
    t1 = _make_track("1")
    t2 = _make_track("2")
    q.put([t1, t2])
    del q[0]
    assert len(q) == 1
    assert q[0] == t2

    q.put(t1)
    rev = list(reversed(q))
    assert rev[0] == t1
    assert rev[1] == t2


def test_queue_put_at():
    """Test put_at method."""
    q = Queue()
    t1 = _make_track("1")
    t2 = _make_track("2")
    q.put(t1)
    q.put_at(0, t2)
    assert q[0] == t2


def test_queue_put_non_atomic():
    """Test put in non-atomic mode."""
    q = Queue()
    t1 = _make_track("1")
    # Using a list with mixed valid/invalid items
    tracks = [t1, "invalid", _make_track("3")]
    added = q.put(tracks, atomic=False)
    assert added == 2
    assert len(q) == 2


@pytest.mark.asyncio
async def test_queue_put_wait_non_atomic():
    """Test put_wait in non-atomic mode."""
    q = Queue()
    t1 = _make_track("1")
    tracks = [t1, "invalid", _make_track("3")]
    added = await q.put_wait(tracks, atomic=False)
    assert added == 2
    assert len(q) == 2


def test_queue_get_at_empty():
    """Test get_at raises QueueEmpty on empty queue."""
    q = Queue()
    with pytest.raises(QueueEmpty):
        q.get_at(0)


def test_queue_index_method():
    """Test index method."""
    q = Queue()
    t = _make_track()
    q.put(t)
    assert q.index(t) == 0


def test_queue_loaded_setter():
    """Test loaded setter and compatibility check."""
    q = Queue()
    t = _make_track()
    q.loaded = t
    assert q.loaded == t
    with pytest.raises(TypeError):
        q.loaded = "not a track"


@pytest.mark.asyncio
async def test_queue_get_wait_cancel():
    """Test get_wait cancellation and error handling."""
    q = Queue()

    task = asyncio.create_task(q.get_wait())
    await asyncio.sleep(0)  # let it start and append to _waiters

    assert len(q._waiters) == 1
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert len(q._waiters) == 0


@pytest.mark.asyncio
async def test_queue_put_wait_atomic_list():
    """Test put_wait with a list of items in atomic mode."""
    q = Queue()
    tracks = [_make_track("1"), _make_track("2")]
    added = await q.put_wait(tracks, atomic=True)
    assert added == 2
    assert len(q) == 2


def test_reset_with_waiters():
    """Test reset cancels active waiters."""
    q = Queue()
    loop = asyncio.get_event_loop()
    waiter = loop.create_future()
    q._waiters.append(waiter)

    q.reset()
    assert waiter.cancelled()
    assert len(q._waiters) == 0
