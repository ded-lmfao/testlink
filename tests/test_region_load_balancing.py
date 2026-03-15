from unittest.mock import MagicMock

import pytest

from revvlink import Node, Pool
from revvlink.enums import NodeStatus
from revvlink.node import REGIONS


@pytest.fixture(autouse=True)
def reset_pool():
    Pool._Pool__nodes = {}
    Pool._regions = REGIONS  # Reset to default regions
    yield
    Pool._Pool__nodes = {}
    Pool._regions = REGIONS


def test_region_from_endpoint():
    assert Pool.region_from_endpoint("iad1.discord.gg:443") == "us"
    assert Pool.region_from_endpoint("ams-central.discord.gg") == "eu"
    assert Pool.region_from_endpoint("hkg.discord.gg") == "asia"
    # Implementation returns 'global' when no match, not None
    # Use endpoint that doesn't contain any region identifiers (avoid 'ord' in 'discord')
    assert Pool.region_from_endpoint("unknown123.gg") == "global"


def test_node_penalty_no_stats():
    node = Node(uri="http://localhost:2333", password="test", region="us", session=MagicMock())
    node.stats = None
    assert node.penalty == 9e30


def test_node_penalty_with_stats():
    node = Node(uri="http://localhost:2333", password="test", region="us", session=MagicMock())

    class MockCPU:
        system_load = 0.5  # 50%
        cores = 4
        lavalink_load = 0.1

    class MockFrames:
        deficit = 1500
        nulled = 1500
        sent = 3000

    class MockStats:
        cpu = MockCPU()
        frames = MockFrames()
        playing = 10
        players = 20

    node.stats = MockStats()
    score = node.penalty
    # Cpu: 1.05 ^ 50 * 10 - 10 ≈ 104.67
    # Deficit: 1.03 ^ (500 * (1500/3000)) * 300 - 300 = 1.03^250 * 300 - 300
    # Nulled: (1.03 ^ 250 * 300 - 300) * 2
    # Playing: 10 * 1.5 = 15
    assert score > 0
    assert score < 9e30


def test_pool_get_node_region():
    n_us = Node(
        identifier="US",
        uri="http://localhost:2333",
        password="test",
        region="us",
        session=MagicMock(),
    )
    n_us._status = NodeStatus.CONNECTED
    n_eu = Node(
        identifier="EU",
        uri="http://localhost:2334",
        password="test",
        region="eu",
        session=MagicMock(),
    )
    n_eu._status = NodeStatus.CONNECTED

    # Mock no stats - they default to infinite penalty but we can override
    class MStats:
        def __init__(self, sys_load, playing):
            self.cpu = type("C", (), {"system_load": sys_load})()
            self.frames = None
            self.playing = playing

    n_us.stats = MStats(0.1, 5)
    n_eu.stats = MStats(0.1, 5)

    Pool._Pool__nodes = {"US": n_us, "EU": n_eu}

    assert Pool.get_node(region="us") == n_us
    assert Pool.get_node(region="eu") == n_eu


def test_pool_get_node_fallback():
    n_us = Node(
        identifier="US",
        uri="http://localhost:2333",
        password="test",
        region="us",
        session=MagicMock(),
    )
    n_us._status = NodeStatus.CONNECTED
    n_eu = Node(
        identifier="EU",
        uri="http://localhost:2334",
        password="test",
        region="eu",
        session=MagicMock(),
    )
    n_eu._status = NodeStatus.CONNECTED

    class MStats:
        def __init__(self, sys_load, playing):
            self.cpu = type("C", (), {"system_load": sys_load})()
            self.frames = None
            self.playing = playing

    n_us.stats = MStats(0.8, 100)  # High load
    n_eu.stats = MStats(0.1, 5)  # Low load

    Pool._Pool__nodes = {"US": n_us, "EU": n_eu}

    # Requesting asia, but none exist, should fallback to best node overall (EU)
    assert Pool.get_node(region="asia") == n_eu


@pytest.mark.asyncio
async def test_player_voice_server_update():
    from revvlink.player import Player

    n_us = Node(
        identifier="US",
        uri="http://localhost:2333",
        password="test",
        region="us",
        session=MagicMock(),
    )
    n_us._status = NodeStatus.CONNECTED
    n_eu = Node(
        identifier="EU",
        uri="http://localhost:2334",
        password="test",
        region="eu",
        session=MagicMock(),
    )
    n_eu._status = NodeStatus.CONNECTED

    Pool._Pool__nodes = {"US": n_us, "EU": n_eu}

    class MockClient:
        user = MagicMock(id=123)

    class MockGuild:
        id = 456

    class MockChannel:
        id = 789
        guild = MockGuild()

    player = Player(MockClient(), MockChannel())
    player._guild = MockGuild()

    # Force the player to be initially assigned to EU (e.g. default)
    player._node = n_eu
    n_eu._players[player._guild.id] = player

    # We simulate not being connected yet
    player._connected = False

    await player.on_voice_server_update(
        {"token": "test_token", "guild_id": "456", "endpoint": "iad-east1.discord.gg"}
    )

    # The player should have been moved to the US node due to the region match
    assert player.node == n_us
    assert player._guild.id in n_us._players
    assert player._guild.id not in n_eu._players
