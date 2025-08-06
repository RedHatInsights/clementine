"""Tests for SlackContextExtractor."""

import pytest
from unittest.mock import Mock, patch
from slack_sdk.errors import SlackApiError

from clementine.slack_context_extractor import SlackContextExtractor, SlackMessage


class TestSlackMessage:
    """Test SlackMessage value object."""
    
    def test_to_context_string(self):
        """Test converting message to context string with user ID."""
        message = SlackMessage(
            text="Hello world",
            user_id="U123456",
            timestamp="1234567890.123"
        )
        
        result = message.to_context_string()
        assert result == "U123456: Hello world"
    
    def test_to_context_string_with_thread(self):
        """Test converting threaded message to context string."""
        message = SlackMessage(
            text="Reply in thread",
            user_id="U789012",
            timestamp="1234567890.456",
            thread_ts="1234567890.123"
        )
        
        result = message.to_context_string()
        assert result == "U789012: Reply in thread"
    
    def test_to_context_string_with_user_name(self):
        """Test converting message to context string with user name."""
        message = SlackMessage(
            text="Hello world",
            user_id="U123456",
            timestamp="1234567890.123",
            user_name="Andrew Chen"
        )
        
        result = message.to_context_string()
        assert result == "Andrew Chen: Hello world"


class TestSlackContextExtractor:
    """Test SlackContextExtractor functionality."""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock Slack client."""
        return Mock()
    
    @pytest.fixture
    def extractor(self, mock_client):
        """Create SlackContextExtractor with mocked client."""
        return SlackContextExtractor(mock_client, max_messages=10)
    
    def test_init(self, mock_client):
        """Test initialization."""
        extractor = SlackContextExtractor(mock_client, max_messages=25)
        assert extractor.client == mock_client
        assert extractor.max_messages == 25
    
    def test_init_default_max_messages(self, mock_client):
        """Test initialization with default max_messages."""
        extractor = SlackContextExtractor(mock_client)
        assert extractor.max_messages == 50
    
    def test_extract_thread_context_success(self, extractor, mock_client):
        """Test successful thread context extraction."""
        # Mock API response
        mock_response = {
            "messages": [
                {
                    "text": "First message",
                    "user": "U123456",
                    "ts": "1234567890.123"
                },
                {
                    "text": "Second message",
                    "user": "U789012",
                    "ts": "1234567890.456"
                },
                {
                    "text": "Bot message",
                    "bot_id": "B12345",
                    "ts": "1234567890.789"
                }
            ]
        }
        mock_client.conversations_replies.return_value = mock_response
        
        # Mock user name lookup to fail so it uses user IDs
        mock_client.users_info.side_effect = SlackApiError("User not found", response={"error": "user_not_found"})
        
        result = extractor.extract_thread_context("C123456", "1234567890.123")
        
        # Should filter out bot message  
        expected = [
            "U123456: First message",
            "U789012: Second message"
        ]
        assert result == expected
        
        # Verify API call
        mock_client.conversations_replies.assert_called_once_with(
            channel="C123456",
            ts="1234567890.123",
            limit=10
        )
    
    def test_extract_thread_context_slack_error(self, extractor, mock_client):
        """Test thread context extraction with Slack API error."""
        mock_client.conversations_replies.side_effect = SlackApiError("API Error", response={"error": "channel_not_found"})
        
        result = extractor.extract_thread_context("C123456", "1234567890.123")
        
        assert result == []
    
    def test_extract_channel_context_success(self, extractor, mock_client):
        """Test successful channel context extraction."""
        # Mock API response (newest first, should be reversed)
        mock_response = {
            "messages": [
                {
                    "text": "Newest message",
                    "user": "U789012",
                    "ts": "1234567890.456"
                },
                {
                    "text": "Older message",
                    "user": "U123456",
                    "ts": "1234567890.123"
                }
            ]
        }
        mock_client.conversations_history.return_value = mock_response
        
        # Mock user name lookup to fail so it uses user IDs
        mock_client.users_info.side_effect = SlackApiError("User not found", response={"error": "user_not_found"})
        
        result = extractor.extract_channel_context("C123456")
        
        # Should be in chronological order (oldest first)
        expected = [
            "U123456: Older message",
            "U789012: Newest message"
        ]
        assert result == expected
        
        # Verify API call
        mock_client.conversations_history.assert_called_once_with(
            channel="C123456",
            limit=10  # extractor was initialized with max_messages=10
        )
    
    def test_extract_channel_context_with_limit(self, extractor, mock_client):
        """Test channel context extraction with custom limit."""
        mock_response = {"messages": []}
        mock_client.conversations_history.return_value = mock_response
        
        extractor.extract_channel_context("C123456", limit=20)
        
        mock_client.conversations_history.assert_called_once_with(
            channel="C123456",
            limit=20
        )
    
    def test_extract_channel_context_slack_error(self, extractor, mock_client):
        """Test channel context extraction with Slack API error."""
        mock_client.conversations_history.side_effect = SlackApiError("API Error", response={"error": "channel_not_found"})
        
        result = extractor.extract_channel_context("C123456")
        
        assert result == []
    
    def test_messages_to_context_filters_bot_messages(self, extractor, mock_client):
        """Test that bot messages are filtered out."""
        # Mock user name lookup to fail so it uses user IDs
        mock_client.users_info.side_effect = SlackApiError("User not found", response={"error": "user_not_found"})
        
        messages = [
            {
                "text": "Human message",
                "user": "U123456",
                "ts": "1234567890.123"
            },
            {
                "text": "Bot message",
                "bot_id": "B12345",
                "ts": "1234567890.456"
            },
            {
                "text": "System message",
                "subtype": "channel_join",
                "ts": "1234567890.789"
            }
        ]
        
        result = extractor._messages_to_context(messages)
        
        assert result == ["U123456: Human message"]
    
    def test_messages_to_context_filters_empty_text(self, extractor, mock_client):
        """Test that messages without text are filtered out."""
        # Mock user name lookup to fail so it uses user IDs
        mock_client.users_info.side_effect = SlackApiError("User not found", response={"error": "user_not_found"})
        
        messages = [
            {
                "text": "Valid message",
                "user": "U123456",
                "ts": "1234567890.123"
            },
            {
                "text": "",
                "user": "U789012",
                "ts": "1234567890.456"
            },
            {
                "user": "U111111",  # No text field
                "ts": "1234567890.789"
            }
        ]
        
        result = extractor._messages_to_context(messages)
        
        assert result == ["U123456: Valid message"]
    
    def test_messages_to_context_handles_missing_user(self, extractor):
        """Test that messages with missing user field use 'unknown'."""
        messages = [
            {
                "text": "Message without user",
                "ts": "1234567890.123"
            }
        ]
        
        result = extractor._messages_to_context(messages)
        
        assert result == ["unknown: Message without user"]
    
    def test_get_user_name_success(self, extractor, mock_client):
        """Test successful user name lookup."""
        mock_response = {
            "user": {
                "real_name": "Andrew Chen",
                "profile": {"display_name": "andrew"},
                "name": "andrew.chen"
            }
        }
        mock_client.users_info.return_value = mock_response
        
        result = extractor._get_user_name("U123456")
        
        assert result == "Andrew Chen"
        mock_client.users_info.assert_called_once_with(user="U123456")
        
        # Test caching - second call should not hit API
        result2 = extractor._get_user_name("U123456")
        assert result2 == "Andrew Chen"
        assert mock_client.users_info.call_count == 1  # Still only one call
    
    def test_get_user_name_fallback_display_name(self, extractor, mock_client):
        """Test user name lookup fallback to display name."""
        mock_response = {
            "user": {
                "real_name": "",  # No real name
                "profile": {"display_name": "andrew"},
                "name": "andrew.chen"
            }
        }
        mock_client.users_info.return_value = mock_response
        
        result = extractor._get_user_name("U123456")
        
        assert result == "andrew"
    
    def test_get_user_name_fallback_username(self, extractor, mock_client):
        """Test user name lookup fallback to username."""
        mock_response = {
            "user": {
                "real_name": "",  # No real name
                "profile": {"display_name": ""},  # No display name
                "name": "andrew.chen"
            }
        }
        mock_client.users_info.return_value = mock_response
        
        result = extractor._get_user_name("U123456")
        
        assert result == "andrew.chen"
    
    def test_get_user_name_api_error(self, extractor, mock_client):
        """Test user name lookup with API error."""
        mock_client.users_info.side_effect = SlackApiError("User not found", response={"error": "user_not_found"})
        
        result = extractor._get_user_name("U123456")
        
        assert result is None
        
        # Test caching of failures
        result2 = extractor._get_user_name("U123456")
        assert result2 is None
        assert mock_client.users_info.call_count == 1  # Only called once due to caching
    
    def test_get_user_name_invalid_user_id(self, extractor):
        """Test user name lookup with invalid user ID."""
        result1 = extractor._get_user_name("")
        result2 = extractor._get_user_name("unknown")
        
        assert result1 is None
        assert result2 is None
    
    def test_extract_context_with_user_names(self, extractor, mock_client):
        """Test context extraction using real user names."""
        # Mock conversations API (newest first, as Slack returns)
        mock_conversations_response = {
            "messages": [
                {
                    "text": "How's the project going?",
                    "user": "U789012",
                    "ts": "1234567890.456"
                },
                {
                    "text": "Hello everyone",
                    "user": "U123456",
                    "ts": "1234567890.123"
                }
            ]
        }
        mock_client.conversations_history.return_value = mock_conversations_response
        
        # Mock user info API
        def mock_users_info(user):
            if user == "U123456":
                return {
                    "user": {
                        "real_name": "Andrew Chen",
                        "profile": {"display_name": "andrew"},
                        "name": "andrew.chen"
                    }
                }
            elif user == "U789012":
                return {
                    "user": {
                        "real_name": "Psav Kumar",
                        "profile": {"display_name": "psav"},
                        "name": "psav.kumar"
                    }
                }
        
        mock_client.users_info.side_effect = mock_users_info
        
        result = extractor.extract_channel_context("C123456")
        
        # Should use real names in chronological order (oldest first)
        expected = [
            "Andrew Chen: Hello everyone",
            "Psav Kumar: How's the project going?"
        ]
        assert result == expected