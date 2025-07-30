import pytest
from unittest.mock import Mock, MagicMock
import requests
from slack_sdk.errors import SlackApiError
from slack_sdk.web.client import WebClient

from clementine import (
    SlackEvent, TangerineResponse, MessageFormatter, SlackClient,
    TangerineClient, ErrorHandler, ClementineBot
)


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


class TestTangerineResponse:
    """Test TangerineResponse value object."""
    
    def test_from_dict_with_content_and_metadata(self):
        """Test creating response with content and metadata."""
        data = {
            "text_content": "Here's your answer",
            "search_metadata": [
                {"metadata": {"citation_url": "http://example.com", "title": "Example"}},
                {"metadata": {"citation_url": "http://test.com", "title": "Test"}}
            ]
        }
        
        response = TangerineResponse.from_dict(data)
        
        assert response.text == "Here's your answer"
        assert len(response.metadata) == 2
        assert response.metadata[0]["metadata"]["title"] == "Example"
    
    def test_from_dict_missing_content(self):
        """Test default message when content is missing."""
        data = {"search_metadata": []}
        
        response = TangerineResponse.from_dict(data)
        
        assert response.text == "(No response from assistant)"
        assert response.metadata == []
    
    def test_from_dict_strips_whitespace(self):
        """Test that text content is stripped."""
        data = {"text_content": "  Answer  "}
        
        response = TangerineResponse.from_dict(data)
        
        assert response.text == "Answer"


class TestMessageFormatter:
    """Test MessageFormatter functionality."""
    
    def test_format_with_sources_no_metadata(self):
        """Test formatting when no metadata is provided."""
        formatter = MessageFormatter()
        response = TangerineResponse(text="Hello", metadata=[])
        
        result = formatter.format_with_sources(response)
        
        assert result == "Hello"
    
    def test_format_with_sources_valid_metadata(self):
        """Test formatting with valid source metadata."""
        formatter = MessageFormatter()
        metadata = [
            {"metadata": {"citation_url": "http://example.com", "title": "Example"}},
            {"metadata": {"citation_url": "http://test.com", "title": "Test"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata)
        
        result = formatter.format_with_sources(response)
        
        expected = "Hello\n\n*Sources:*\n<http://example.com|Example>\n<http://test.com|Test>"
        assert result == expected
    
    def test_format_with_sources_malformed_metadata(self):
        """Test handling of malformed metadata entries."""
        formatter = MessageFormatter()
        metadata = [
            {"metadata": {"citation_url": "http://example.com", "title": "Example"}},
            {"invalid": "structure"},  # Malformed - should be skipped
            {"metadata": {"citation_url": "http://test.com"}}  # Missing title - gets default "Source"
        ]
        response = TangerineResponse(text="Hello", metadata=metadata)
        
        result = formatter.format_with_sources(response)
        
        expected = "Hello\n\n*Sources:*\n<http://example.com|Example>\n<http://test.com|Source>"
        assert result == expected
    
    def test_format_with_sources_limits_to_three(self):
        """Test that only first 3 sources are included."""
        formatter = MessageFormatter()
        metadata = [
            {"metadata": {"citation_url": f"http://example{i}.com", "title": f"Example {i}"}}
            for i in range(5)
        ]
        response = TangerineResponse(text="Hello", metadata=metadata)
        
        result = formatter.format_with_sources(response)
        
        # Should only have 3 sources
        assert result.count("<http://") == 3
        assert "Example 0" in result
        assert "Example 1" in result
        assert "Example 2" in result
        assert "Example 3" not in result


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


class MockHTTPAdapter:
    """Mock HTTP adapter for testing TangerineClient."""
    
    def __init__(self):
        self.post_responses = []
        self.call_count = 0
    
    def add_response(self, status_code, json_data):
        """Add a mock response."""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data
        mock_response.raise_for_status = Mock()
        if status_code >= 400:
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        self.post_responses.append(mock_response)
    
    def post(self, url, **kwargs):
        """Mock post method."""
        if self.call_count >= len(self.post_responses):
            raise Exception("No more mock responses available")
        response = self.post_responses[self.call_count]
        self.call_count += 1
        return response


class TestTangerineClient:
    """Test TangerineClient with dependency injection."""
    
    def test_chat_success(self):
        """Test successful chat request."""
        mock_adapter = MockHTTPAdapter()
        mock_adapter.add_response(200, {
            "text_content": "Hello response",
            "search_metadata": [{"metadata": {"citation_url": "http://example.com", "title": "Example"}}]
        })
        
        # Use dependency injection to replace requests
        client = TangerineClient("http://api.example.com", "token123")
        client._http_adapter = mock_adapter
        
        # Inject the adapter into the _make_request method
        original_make_request = client._make_request
        def mock_make_request(payload):
            return mock_adapter.post("fake_url", json=payload).json()
        client._make_request = mock_make_request
        
        result = client.chat(
            assistants=["assistant1"],
            query="Hello",
            session_id="session123",
            client_name="TestBot",
            prompt="You are helpful"
        )
        
        assert isinstance(result, TangerineResponse)
        assert result.text == "Hello response"
        assert len(result.metadata) == 1
    
    def test_initialization_validation(self):
        """Test client initialization validation."""
        with pytest.raises(ValueError, match="Both api_url and api_token are required"):
            TangerineClient("", "token")
        
        with pytest.raises(ValueError, match="Both api_url and api_token are required"):
            TangerineClient("http://example.com", "")
    
    def test_url_normalization(self):
        """Test that trailing slashes are removed from URLs."""
        client = TangerineClient("http://example.com/", "token")
        
        assert client.api_url == "http://example.com"
        assert client.chat_endpoint == "http://example.com/api/assistants/chat"


class TestErrorHandler:
    """Test ErrorHandler functionality."""
    
    def test_format_error_message(self):
        """Test error message formatting."""
        error_handler = ErrorHandler("TestBot")
        test_error = Exception("Test error")
        
        result = error_handler.format_error_message(test_error)
        
        assert result == "Oops, TestBot hit a snag. Please try again in a moment."
    
    def test_format_error_message_different_bot_name(self):
        """Test error message with different bot name."""
        error_handler = ErrorHandler("DifferentBot")
        test_error = ValueError("Test error")
        
        result = error_handler.format_error_message(test_error)
        
        assert result == "Oops, DifferentBot hit a snag. Please try again in a moment."


class TestClementineBot:
    """Test ClementineBot orchestration with full dependency injection."""
    
    def test_handle_mention_success_flow(self):
        """Test complete successful mention handling flow."""
        # Setup mocks
        mock_tangerine = Mock()
        mock_tangerine.chat.return_value = TangerineResponse(
            text="Response from AI",
            metadata=[{"metadata": {"citation_url": "http://example.com", "title": "Example"}}]
        )
        
        mock_slack_client = Mock()
        mock_slack_client.post_loading_message.return_value = "1234567890.123"
        mock_slack_client.update_message.return_value = True
        
        mock_web_client = Mock(spec=WebClient)
        
        # Create bot with injected dependencies
        bot = ClementineBot(
            tangerine_client=mock_tangerine,
            slack_client=mock_slack_client,
            bot_name="TestBot",
            assistant_list=["assistant1"],
            default_prompt="Be helpful"
        )
        
        # Test event
        event_dict = {
            "text": "Hello bot",
            "user": "U123",
            "channel": "C456",
            "ts": "1234567890.100"
        }
        
        # Execute
        bot.handle_mention(event_dict, mock_web_client)
        
        # Verify interactions
        mock_slack_client.post_loading_message.assert_called_once_with("C456", "1234567890.100")
        mock_tangerine.chat.assert_called_once_with(
            assistants=["assistant1"],
            query="Hello bot",
            session_id="U123",
            client_name="TestBot",
            prompt="Be helpful"
        )
        mock_slack_client.update_message.assert_called_once()
        # Verify the formatted message includes sources
        call_args = mock_slack_client.update_message.call_args
        assert "Response from AI" in call_args[0][2]
        assert "*Sources:*" in call_args[0][2]
    
    def test_handle_mention_loading_message_fails(self):
        """Test handling when loading message fails to post."""
        mock_tangerine = Mock()
        mock_slack_client = Mock()
        mock_slack_client.post_loading_message.return_value = None  # Failure
        mock_web_client = Mock(spec=WebClient)
        
        bot = ClementineBot(
            tangerine_client=mock_tangerine,
            slack_client=mock_slack_client,
            bot_name="TestBot",
            assistant_list=["assistant1"],
            default_prompt="Be helpful"
        )
        
        event_dict = {
            "text": "Hello bot",
            "user": "U123",
            "channel": "C456",
            "ts": "1234567890.100"
        }
        
        bot.handle_mention(event_dict, mock_web_client)
        
        # Should not proceed to tangerine call
        mock_tangerine.chat.assert_not_called()
    
    def test_handle_mention_tangerine_error(self):
        """Test handling when Tangerine API fails."""
        mock_tangerine = Mock()
        mock_tangerine.chat.side_effect = requests.exceptions.ConnectionError("API down")
        
        mock_slack_client = Mock()
        mock_slack_client.post_loading_message.return_value = "1234567890.123"
        mock_slack_client.update_message.return_value = True
        
        mock_web_client = Mock(spec=WebClient)
        
        bot = ClementineBot(
            tangerine_client=mock_tangerine,
            slack_client=mock_slack_client,
            bot_name="TestBot",
            assistant_list=["assistant1"],
            default_prompt="Be helpful"
        )
        
        event_dict = {
            "text": "Hello bot",
            "user": "U123",
            "channel": "C456",
            "ts": "1234567890.100"
        }
        
        bot.handle_mention(event_dict, mock_web_client)
        
        # Should post error message
        mock_slack_client.update_message.assert_called()
        call_args = mock_slack_client.update_message.call_args
        assert "TestBot hit a snag" in call_args[0][2]
    
    def test_handle_mention_invalid_event(self):
        """Test handling of malformed event data."""
        mock_tangerine = Mock()
        mock_slack_client = Mock()
        mock_web_client = Mock(spec=WebClient)
        
        bot = ClementineBot(
            tangerine_client=mock_tangerine,
            slack_client=mock_slack_client,
            bot_name="TestBot",
            assistant_list=["assistant1"],
            default_prompt="Be helpful"
        )
        
        # Invalid event (missing required fields)
        event_dict = {"text": "Hello"}
        
        bot.handle_mention(event_dict, mock_web_client)
        
        # Should not proceed with any operations
        mock_slack_client.post_loading_message.assert_not_called()
        mock_tangerine.chat.assert_not_called() 