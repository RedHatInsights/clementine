import pytest
from unittest.mock import Mock
import requests
from slack_sdk.web.client import WebClient

from clementine.bot import ClementineBot
from clementine.tangerine import TangerineResponse


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
            session_id=generate_session_id(user="U123", channel="C456"),
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