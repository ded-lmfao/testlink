import pytest

from revvlink import backoff, enums, exceptions


def test_enums():
    assert enums.NodeStatus.CONNECTED.value == 2
    assert enums.TrackSource.YouTube.value == 0
    assert enums.AutoPlayMode.enabled.value == 0


def test_exceptions_base():
    err = exceptions.AuthorizationFailedException("Auth failed")
    assert str(err) == "Auth failed"

    with pytest.raises(exceptions.RevvLinkException):
        raise exceptions.RevvLinkException("Base error")


def test_exception_node_exception():
    ex = exceptions.NodeException("Node broke", status=503)
    assert ex.status == 503
    assert str(ex) == "Node broke"

    ex_no_status = exceptions.NodeException()
    assert ex_no_status.status is None


def test_exception_lavalink_exception():
    data = {"timestamp": 1000, "status": 404, "error": "Not Found", "path": "/v4/players"}
    ex = exceptions.LavalinkException(data=data)
    assert ex.status == 404
    assert ex.error == "Not Found"
    assert ex.path == "/v4/players"
    assert ex.trace is None
    assert "404" in str(ex)

    # With trace
    data_trace = dict(data)
    data_trace["trace"] = "stack trace"
    ex2 = exceptions.LavalinkException("Custom msg", data=data_trace)
    assert str(ex2) == "Custom msg"
    assert ex2.trace == "stack trace"


def test_exception_lavalink_load_exception():
    data = {"message": "No matches", "severity": "COMMON", "cause": "track not found"}
    ex = exceptions.LavalinkLoadException(data=data)
    assert ex.error == "No matches"
    assert ex.severity == "COMMON"
    assert ex.cause == "track not found"
    assert "No matches" in str(ex)

    # With custom message
    ex2 = exceptions.LavalinkLoadException("Custom", data=data)
    assert str(ex2) == "Custom"


def test_exception_subclasses():
    for cls in [
        exceptions.InvalidClientException,
        exceptions.InvalidNodeException,
        exceptions.InvalidChannelStateException,
        exceptions.ChannelTimeoutException,
        exceptions.QueueEmpty,
    ]:
        with pytest.raises(cls):
            raise cls("test")


@pytest.mark.asyncio
async def test_backoff():
    bo = backoff.Backoff(base=10, maximum_time=100)
    delay = bo.calculate()
    assert delay >= 0


def test_backoff_reset_on_maximum_tries():
    # Set very small tries so we hit the reset
    bo = backoff.Backoff(base=1, maximum_time=1000.0, maximum_tries=2)
    for _ in range(5):
        delay = bo.calculate()
        assert delay >= 0


def test_backoff_reset_on_maximum_time():
    # Force wait > maximum_time by setting maximum_time very small
    bo = backoff.Backoff(base=100, maximum_time=0.01, maximum_tries=None)
    for _ in range(5):
        delay = bo.calculate()
        assert delay >= 0


def test_backoff_small_wait():
    # Force the wait <= last_wait path
    bo = backoff.Backoff(base=1, maximum_time=1000.0, maximum_tries=None)
    # Run many times to hit the <= last_wait branch
    for _ in range(20):
        bo.calculate()
