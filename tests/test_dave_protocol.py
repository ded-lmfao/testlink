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

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from revvlink.types.websocket import (
        DAVEPrepareTransitionEvent,
        DAVEProtocolChangeEvent,
    )


class TestDAVETypedDicts:
    """Tests for DAVE TypedDicts."""

    def test_dave_protocol_change_event_structure(self):
        """Test DAVEProtocolChangeEvent has correct structure."""
        event: DAVEProtocolChangeEvent = {
            "op": "dave",
            "type": "protocolChange",
            "guildId": "123456789",
            "protocol": "udp",
            "encryptionKey": "test_key_123",
        }

        assert event["op"] == "dave"
        assert event["type"] == "protocolChange"
        assert event["guildId"] == "123456789"
        assert event["protocol"] == "udp"
        assert event["encryptionKey"] == "test_key_123"

    def test_dave_protocol_change_event_with_kcp_protocol(self):
        """Test DAVEProtocolChangeEvent with KCP protocol."""
        event: DAVEProtocolChangeEvent = {
            "op": "dave",
            "type": "protocolChange",
            "guildId": "987654321",
            "protocol": "kcp",
            "encryptionKey": "another_key",
        }

        assert event["protocol"] == "kcp"

    def test_dave_prepare_transition_event_structure(self):
        """Test DAVEPrepareTransitionEvent has correct structure."""
        event: DAVEPrepareTransitionEvent = {
            "op": "dave",
            "type": "prepareTransition",
            "guildId": "123456789",
            "epoch": 2,
            "nextEncryptionKey": "new_rotation_key",
        }

        assert event["op"] == "dave"
        assert event["type"] == "prepareTransition"
        assert event["guildId"] == "123456789"
        assert event["epoch"] == 2
        assert event["nextEncryptionKey"] == "new_rotation_key"

    def test_dave_prepare_transition_event_multiple_epochs(self):
        """Test DAVEPrepareTransitionEvent with different epochs."""
        for epoch in [1, 5, 10, 100]:
            event: DAVEPrepareTransitionEvent = {
                "op": "dave",
                "type": "prepareTransition",
                "guildId": "123",
                "epoch": epoch,
                "nextEncryptionKey": f"key_{epoch}",
            }
            assert event["epoch"] == epoch


class TestPlayerDAVE:
    """Tests for Player DAVE integration."""

    @pytest.fixture
    def mock_player(self):
        """Create a mock player for testing."""
        with patch("revvlink.player.davey", None):
            from revvlink.player import Player

            # Create a mock client
            mock_client = MagicMock()
            mock_client.user = MagicMock()
            mock_client.user.id = 123456789
            mock_client.dispatch = MagicMock()

            # Create player with mock
            player = Player.__new__(Player)
            player.client = mock_client
            player._dave_session = None
            # guild is a property, need to use _guild
            player._guild = MagicMock()
            player._guild.id = 123456789
            player._connected = False
            player._connection_event = MagicMock()

            return player

    @pytest.mark.asyncio
    async def test_is_e2ee_property_false_when_no_session(self, mock_player):
        """Test is_e2ee returns False when no DAVE session."""
        mock_player._dave_session = None
        assert mock_player.is_e2ee is False

    @pytest.mark.asyncio
    async def test_is_e2ee_property_true_with_session(self, mock_player):
        """Test is_e2ee returns True when DAVE session exists."""
        mock_session = MagicMock()
        mock_player._dave_session = mock_session
        assert mock_player.is_e2ee is True

    @pytest.mark.asyncio
    async def test_on_dave_protocol_change_no_davey_library(self, mock_player):
        """Test _on_dave_protocol_change handles missing davey library."""
        payload: DAVEProtocolChangeEvent = {
            "op": "dave",
            "type": "protocolChange",
            "guildId": "123456789",
            "protocol": "udp",
            "encryptionKey": "test_key",
        }

        # When davey is None, should log warning and return
        with patch("revvlink.player.davey", None):
            await mock_player._on_dave_protocol_change(payload)

        # Session should remain None
        assert mock_player._dave_session is None

    @pytest.mark.asyncio
    async def test_on_dave_protocol_change_no_encryption_key(self, mock_player):
        """Test _on_dave_protocol_change handles missing encryption key."""
        payload: DAVEProtocolChangeEvent = {
            "op": "dave",
            "type": "protocolChange",
            "guildId": "123456789",
            "protocol": "udp",
            "encryptionKey": "",  # Empty key
        }

        with patch("revvlink.player.davey", None):
            await mock_player._on_dave_protocol_change(payload)

        # Session should remain None
        assert mock_player._dave_session is None

    @pytest.mark.asyncio
    async def test_on_dave_prepare_transition_no_session(self, mock_player):
        """Test _on_dave_prepare_transition handles no session."""
        mock_player._dave_session = None

        payload: DAVEPrepareTransitionEvent = {
            "op": "dave",
            "type": "prepareTransition",
            "guildId": "123456789",
            "epoch": 2,
            "nextEncryptionKey": "new_key",
        }

        await mock_player._on_dave_prepare_transition(payload)
        # Should not raise, just log warning

    @pytest.mark.asyncio
    async def test_on_dave_prepare_transition_no_next_key(self, mock_player):
        """Test _on_dave_prepare_transition handles missing next key."""
        mock_session = MagicMock()
        mock_player._dave_session = mock_session

        payload: DAVEPrepareTransitionEvent = {
            "op": "dave",
            "type": "prepareTransition",
            "guildId": "123456789",
            "epoch": 2,
            "nextEncryptionKey": "",  # Empty key
        }

        await mock_player._on_dave_prepare_transition(payload)
        # Session should not have rotate_key called
        mock_session.rotate_key.assert_not_called()


class TestWebsocketDAVE:
    """Tests for Websocket DAVE routing."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock websocket for testing."""
        from revvlink.node import Node
        from revvlink.websocket import Websocket

        # Create mock node
        mock_node = MagicMock(spec=Node)
        mock_node.client = MagicMock()
        mock_node.client.user = MagicMock()
        mock_node.client.user.id = 123456789
        mock_node._session = MagicMock()
        mock_node._status = MagicMock()
        mock_node._resume_timeout = 0
        mock_node._session_id = None

        # Create websocket
        ws = Websocket.__new__(Websocket)
        ws.node = mock_node
        ws.socket = None
        ws._tasks = set()

        return ws

    @pytest.mark.asyncio
    async def test_process_op_dave_protocol_change(self, mock_websocket):
        """Test _process_op_dave handles protocolChange event."""
        # Create mock player
        mock_player = MagicMock()
        mock_player._on_dave_protocol_change = AsyncMock()

        mock_websocket.get_player = MagicMock(return_value=mock_player)

        payload = {
            "op": "dave",
            "type": "protocolChange",
            "guildId": "123456789",
            "protocol": "udp",
            "encryptionKey": "test_key",
        }

        await mock_websocket._process_op_dave(payload)

        mock_player._on_dave_protocol_change.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_op_dave_prepare_transition(self, mock_websocket):
        """Test _process_op_dave handles prepareTransition event."""
        # Create mock player
        mock_player = MagicMock()
        mock_player._on_dave_prepare_transition = AsyncMock()

        mock_websocket.get_player = MagicMock(return_value=mock_player)

        payload = {
            "op": "dave",
            "type": "prepareTransition",
            "guildId": "123456789",
            "epoch": 2,
            "nextEncryptionKey": "new_key",
        }

        await mock_websocket._process_op_dave(payload)

        mock_player._on_dave_prepare_transition.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_op_dave_unknown_player(self, mock_websocket):
        """Test _process_op_dave handles unknown guild."""
        mock_websocket.get_player = MagicMock(return_value=None)

        payload = {
            "op": "dave",
            "type": "protocolChange",
            "guildId": "999999999",
            "protocol": "udp",
            "encryptionKey": "test_key",
        }

        # Should not raise
        await mock_websocket._process_op_dave(payload)

    @pytest.mark.asyncio
    async def test_process_op_dave_unknown_event_type(self, mock_websocket):
        """Test _process_op_dave handles unknown event type."""
        mock_player = MagicMock()

        mock_websocket.get_player = MagicMock(return_value=mock_player)

        payload = {
            "op": "dave",
            "type": "unknownEvent",
            "guildId": "123456789",
        }

        # Should not raise
        await mock_websocket._process_op_dave(payload)


class TestDAVEIntegration:
    """Integration tests for DAVE protocol."""

    def test_dave_protocol_change_roundtrip(self):
        """Test DAVE protocol change event can be created and accessed."""
        event: DAVEProtocolChangeEvent = {
            "op": "dave",
            "type": "protocolChange",
            "guildId": "guild_123",
            "protocol": "udp",
            "encryptionKey": "key_abc",
        }

        # Verify all fields accessible
        assert event["op"]
        assert event["type"]
        assert event["guildId"]
        assert event["protocol"]
        assert event["encryptionKey"]

    def test_dave_prepare_transition_roundtrip(self):
        """Test DAVE prepare transition event can be created and accessed."""
        event: DAVEPrepareTransitionEvent = {
            "op": "dave",
            "type": "prepareTransition",
            "guildId": "guild_456",
            "epoch": 5,
            "nextEncryptionKey": "key_xyz",
        }

        # Verify all fields accessible
        assert event["op"]
        assert event["type"]
        assert event["guildId"]
        assert event["epoch"]
        assert event["nextEncryptionKey"]

    def test_websocket_op_union_includes_dave(self):
        """Test WebsocketOP type alias includes DAVE events."""
        # Import at runtime for type checking
        from revvlink.types.websocket import WebsocketOP  # noqa: TC001

        # These should all be valid WebsocketOP types
        protocol_change: WebsocketOP = {
            "op": "dave",
            "type": "protocolChange",
            "guildId": "123",
            "protocol": "udp",
            "encryptionKey": "key",
        }

        prepare_transition: WebsocketOP = {
            "op": "dave",
            "type": "prepareTransition",
            "guildId": "456",
            "epoch": 1,
            "nextEncryptionKey": "key2",
        }

        assert protocol_change["op"] == "dave"
        assert prepare_transition["op"] == "dave"
