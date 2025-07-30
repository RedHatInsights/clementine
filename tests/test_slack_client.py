import pytest
from unittest.mock import Mock
from slack_sdk.errors import SlackApiError
from slack_sdk.web.client import WebClient

from clementine.slack_client import SlackEvent, SlackClient


class TestSlackEvent:
    """Test SlackEvent value object."""
    
    def test_from_dict_valid_event(self):
        """Test creating SlackEvent from valid event dict."""
        event_dict = {
            "text": "Hello bot!",
            "user": "U123456",
            "channel": "C789012",
            "ts": "1234567890.123",
            "thread_ts": "1234567890.100"
        }
        
        event = SlackEvent.from_dict(event_dict)
        
        assert event.text == "Hello bot!"
        assert event.user_id == "U123456"
        assert event.channel == "C789012"
        assert event.thread_ts == "1234567890.100"
    
    def test_from_dict_uses_ts_when_no_thread_ts(self):
        """Test that ts is used as thread_ts when thread_ts is missing."""
        event_dict = {
            "text": "Hello bot!",
            "user": "U123456",
            "channel": "C789012",
            "ts": "1234567890.123"
        }
        
        event = SlackEvent.from_dict(event_dict)
        
        assert event.thread_ts == "1234567890.123"
    
    def test_from_dict_strips_whitespace(self):
        """Test that text whitespace is stripped."""
        event_dict = {
            "text": "  Hello bot!  ",
            "user": "U123456",
            "channel": "C789012",
            "ts": "1234567890.123"
        }
        
        event = SlackEvent.from_dict(event_dict)
        
        assert event.text == "Hello bot!"
    
    def test_from_dict_missing_required_fields(self):
        """Test error when required fields are missing."""
        event_dict = {
            "text": "Hello bot!",
            "user": "U123456"
            # Missing channel and ts
        }
        
        with pytest.raises(ValueError, match="Missing required event fields"):
            SlackEvent.from_dict(event_dict)
    
    def test_from_dict_empty_text(self):
        """Test error when text is empty after stripping."""
        event_dict = {
            "text": "   ",
            "user": "U123456",
            "channel": "C789012",
            "ts": "1234567890.123"
        }
        
        with pytest.raises(ValueError, match="Event text cannot be empty"):
            SlackEvent.from_dict(event_dict)
    
    def test_strips_bot_mention_from_text(self):
        """Test that bot mentions are stripped from the beginning of text."""
        event_dict = {
            "text": "<@U098PF40S1E> what is tekton?",
            "user": "U123456",
            "channel": "C789012",
            "ts": "1234567890.123"
        }
        
        event = SlackEvent.from_dict(event_dict)
        
        assert event.text == "what is tekton?"
    
    def test_strips_bot_mention_with_extra_whitespace(self):
        """Test that bot mentions and extra whitespace are properly stripped."""
        event_dict = {
            "text": "<@U098PF40S1E>   what is tekton?",
            "user": "U123456",
            "channel": "C789012",
            "ts": "1234567890.123"
        }
        
        event = SlackEvent.from_dict(event_dict)
        
        assert event.text == "what is tekton?"
    
    def test_text_without_bot_mention_unchanged(self):
        """Test that text without bot mention at start is unchanged."""
        event_dict = {
            "text": "what is tekton?",
            "user": "U123456",
            "channel": "C789012",
            "ts": "1234567890.123"
        }
        
        event = SlackEvent.from_dict(event_dict)
        
        assert event.text == "what is tekton?"
    
    def test_error_when_only_bot_mention(self):
        """Test error when text contains only bot mention."""
        event_dict = {
            "text": "<@U098PF40S1E>",
            "user": "U123456",
            "channel": "C789012",
            "ts": "1234567890.123"
        }
        
        with pytest.raises(ValueError, match="Event text cannot be empty after removing bot mention"):
            SlackEvent.from_dict(event_dict)
    
    def test_strips_enterprise_user_mention(self):
        """Test that Enterprise user mentions (W prefix) are stripped."""
        event_dict = {
            "text": "<@W098PF40S1E> what is enterprise slack?",
            "user": "U123456",
            "channel": "C789012",
            "ts": "1234567890.123"
        }
        
        event = SlackEvent.from_dict(event_dict)
        
        assert event.text == "what is enterprise slack?"
    
    def test_strips_user_mention_with_underscores_and_hyphens(self):
        """Test that user mentions with underscores and hyphens are stripped."""
        event_dict = {
            "text": "<@U098_PF-40S1E> what is tekton?",
            "user": "U123456",
            "channel": "C789012",
            "ts": "1234567890.123"
        }
        
        event = SlackEvent.from_dict(event_dict)
        
        assert event.text == "what is tekton?"
    
    def test_mixed_case_user_id_stripped(self):
        """Test that user mentions with mixed case characters are stripped."""
        event_dict = {
            "text": "<@U098pF40s1E> what is tekton?",
            "user": "U123456",
            "channel": "C789012",
            "ts": "1234567890.123"
        }
        
        event = SlackEvent.from_dict(event_dict)
        
        assert event.text == "what is tekton?"


class TestSlackClient:
    """Test SlackClient with mocked WebClient."""
    
    def test_post_loading_message_success(self):
        """Test successful loading message posting."""
        mock_web_client = Mock(spec=WebClient)
        mock_web_client.chat_postMessage.return_value = {"ts": "1234567890.123"}
        
        slack_client = SlackClient(mock_web_client)
        
        result = slack_client.post_loading_message("C123", "1234567890.100")
        
        assert result == "1234567890.123"
        mock_web_client.chat_postMessage.assert_called_once_with(
            channel="C123",
            text=":hourglass_flowing_sand: Thinking...",
            thread_ts="1234567890.100"
        )
    
    def test_post_loading_message_custom_text(self):
        """Test loading message with custom text."""
        mock_web_client = Mock(spec=WebClient)
        mock_web_client.chat_postMessage.return_value = {"ts": "1234567890.123"}
        
        slack_client = SlackClient(mock_web_client, loading_text="Processing...")
        slack_client.post_loading_message("C123", "1234567890.100")
        
        mock_web_client.chat_postMessage.assert_called_once_with(
            channel="C123",
            text="Processing...",
            thread_ts="1234567890.100"
        )
    
    def test_post_loading_message_slack_error(self):
        """Test handling of Slack API errors."""
        mock_web_client = Mock(spec=WebClient)
        mock_response = Mock()
        mock_response.get.return_value = "channel_not_found"
        slack_error = SlackApiError("Error", mock_response)
        slack_error.response = mock_response
        mock_web_client.chat_postMessage.side_effect = slack_error
        
        slack_client = SlackClient(mock_web_client)
        
        result = slack_client.post_loading_message("C123", "1234567890.100")
        
        assert result is None
    
    def test_update_message_success(self):
        """Test successful message update."""
        mock_web_client = Mock(spec=WebClient)
        mock_web_client.chat_update.return_value = {"ok": True}
        
        slack_client = SlackClient(mock_web_client)
        
        result = slack_client.update_message("C123", "1234567890.123", "Updated text")
        
        assert result is True
        mock_web_client.chat_update.assert_called_once_with(
            channel="C123",
            ts="1234567890.123",
            text="Updated text"
        )
    
    def test_update_message_slack_error(self):
        """Test handling of update message errors."""
        mock_web_client = Mock(spec=WebClient)
        mock_response = Mock()
        mock_response.get.return_value = "message_not_found"
        slack_error = SlackApiError("Error", mock_response)
        slack_error.response = mock_response
        mock_web_client.chat_update.side_effect = slack_error
        
        slack_client = SlackClient(mock_web_client)
        
        result = slack_client.update_message("C123", "1234567890.123", "Updated text")
        
        assert result is False 