"""Tests for feedback handler functionality."""

import pytest
from unittest.mock import Mock, MagicMock

from clementine.feedback_handler import FeedbackHandler, FeedbackInteraction
from clementine.feedback_client import FeedbackClient, FeedbackRequest


class TestFeedbackInteraction:
    """Test cases for FeedbackInteraction value object."""
    
    def test_feedback_interaction_creation(self):
        """Test creating a FeedbackInteraction."""
        interaction = FeedbackInteraction(
            interaction_id="test-interaction-123",
            channel="C1234567890",
            message_ts="1234567890.123456",
            user_id="U1234567890"
        )
        
        assert interaction.interaction_id == "test-interaction-123"
        assert interaction.channel == "C1234567890"
        assert interaction.message_ts == "1234567890.123456"
        assert interaction.user_id == "U1234567890"


class TestFeedbackHandler:
    """Test cases for FeedbackHandler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_feedback_client = Mock(spec=FeedbackClient)
        self.mock_slack_client = Mock()
        self.handler = FeedbackHandler(self.mock_feedback_client, self.mock_slack_client)
    
    def test_init(self):
        """Test FeedbackHandler initialization."""
        assert self.handler.feedback_client == self.mock_feedback_client
        assert self.handler.slack_client == self.mock_slack_client
    
    def test_parse_interaction_like_button(self):
        """Test parsing like button interaction payload."""
        payload = {
            "container": {
                "channel_id": "C1234567890",
                "message_ts": "1234567890.123456"
            },
            "user": {
                "id": "U1234567890"
            },
            "actions": [
                {
                    "value": "feedback_like_test-interaction-123",
                    "action_id": "feedback_like"
                }
            ]
        }
        
        interaction = self.handler._parse_interaction(payload)
        
        assert interaction.interaction_id == "test-interaction-123"
        assert interaction.channel == "C1234567890"
        assert interaction.message_ts == "1234567890.123456"
        assert interaction.user_id == "U1234567890"
    
    def test_parse_interaction_dislike_button(self):
        """Test parsing dislike button interaction payload."""
        payload = {
            "container": {
                "channel_id": "C1234567890", 
                "message_ts": "1234567890.123456"
            },
            "user": {
                "id": "U1234567890"
            },
            "actions": [
                {
                    "value": "feedback_dislike_test-interaction-456",
                    "action_id": "feedback_dislike"
                }
            ]
        }
        
        interaction = self.handler._parse_interaction(payload)
        
        assert interaction.interaction_id == "test-interaction-456"
        assert interaction.channel == "C1234567890"
        assert interaction.message_ts == "1234567890.123456"
        assert interaction.user_id == "U1234567890"
    
    def test_parse_interaction_missing_actions(self):
        """Test parsing interaction payload with missing actions."""
        payload = {
            "container": {
                "channel_id": "C1234567890",
                "message_ts": "1234567890.123456"
            },
            "user": {
                "id": "U1234567890"
            },
            "actions": []
        }
        
        with pytest.raises(ValueError, match="No actions found in interaction payload"):
            self.handler._parse_interaction(payload)
    
    def test_parse_interaction_invalid_action_value(self):
        """Test parsing interaction payload with invalid action value."""
        payload = {
            "container": {
                "channel_id": "C1234567890",
                "message_ts": "1234567890.123456"
            },
            "user": {
                "id": "U1234567890"
            },
            "actions": [
                {
                    "value": "invalid_action_value",
                    "action_id": "invalid"
                }
            ]
        }
        
        with pytest.raises(ValueError, match="Invalid action value format"):
            self.handler._parse_interaction(payload)
    
    def test_parse_interaction_missing_container(self):
        """Test parsing interaction payload with missing container."""
        payload = {
            "user": {
                "id": "U1234567890"
            },
            "actions": [
                {
                    "value": "feedback_like_test-interaction-123",
                    "action_id": "feedback_like"
                }
            ]
        }
        
        # Should still work but with empty strings for missing container fields
        interaction = self.handler._parse_interaction(payload)
        assert interaction.interaction_id == "test-interaction-123"
        assert interaction.channel == ""
        assert interaction.message_ts == ""
        assert interaction.user_id == "U1234567890"
    
    def test_build_feedback_request_like(self):
        """Test building feedback request for like button."""
        payload = {
            "actions": [
                {
                    "value": "feedback_like_test-interaction-123",
                    "action_id": "feedback_like"
                }
            ]
        }
        
        interaction = FeedbackInteraction(
            interaction_id="test-interaction-123",
            channel="C1234567890",
            message_ts="1234567890.123456",
            user_id="U1234567890"
        )
        
        request = self.handler._build_feedback_request(payload, interaction)
        
        assert request.like is True
        assert request.dislike is False
        assert request.feedback == ""
        assert request.interaction_id == "test-interaction-123"
    
    def test_build_feedback_request_dislike(self):
        """Test building feedback request for dislike button."""
        payload = {
            "actions": [
                {
                    "value": "feedback_dislike_test-interaction-456",
                    "action_id": "feedback_dislike"
                }
            ]
        }
        
        interaction = FeedbackInteraction(
            interaction_id="test-interaction-456",
            channel="C1234567890",
            message_ts="1234567890.123456",
            user_id="U1234567890"
        )
        
        request = self.handler._build_feedback_request(payload, interaction)
        
        assert request.like is False
        assert request.dislike is True
        assert request.feedback == ""
        assert request.interaction_id == "test-interaction-456"
    
    def test_handle_feedback_button_success(self):
        """Test successful feedback button handling."""
        payload = {
            "container": {
                "channel_id": "C1234567890",
                "message_ts": "1234567890.123456"
            },
            "user": {
                "id": "U1234567890"
            },
            "actions": [
                {
                    "value": "feedback_like_test-interaction-123",
                    "action_id": "feedback_like"
                }
            ]
        }
        
        # Mock successful feedback submission
        self.mock_feedback_client.send_feedback.return_value = True
        
        # Mock getting current message
        current_message = {
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": "Test response"}},
                {"type": "actions", "block_id": "feedback_actions", "elements": []}
            ],
            "text": "Test response"
        }
        self.mock_slack_client.get_message.return_value = current_message
        self.mock_slack_client.update_message_with_blocks.return_value = True
        
        # Execute
        self.handler.handle_feedback_button(payload)
        
        # Verify feedback was sent
        self.mock_feedback_client.send_feedback.assert_called_once()
        sent_request = self.mock_feedback_client.send_feedback.call_args[0][0]
        assert sent_request.like is True
        assert sent_request.dislike is False
        assert sent_request.interaction_id == "test-interaction-123"
        
        # Verify thank you message was shown
        self.mock_slack_client.get_message.assert_called_once_with("C1234567890", "1234567890.123456")
        self.mock_slack_client.update_message_with_blocks.assert_called_once()
    
    def test_handle_feedback_button_api_failure(self):
        """Test feedback button handling with API failure."""
        payload = {
            "container": {
                "channel_id": "C1234567890",
                "message_ts": "1234567890.123456"
            },
            "user": {
                "id": "U1234567890"
            },
            "actions": [
                {
                    "value": "feedback_like_test-interaction-123",
                    "action_id": "feedback_like"
                }
            ]
        }
        
        # Mock failed feedback submission
        self.mock_feedback_client.send_feedback.return_value = False
        
        # Mock getting current message
        current_message = {
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": "Test response"}},
                {"type": "actions", "block_id": "feedback_actions", "elements": []}
            ],
            "text": "Test response"
        }
        self.mock_slack_client.get_message.return_value = current_message
        self.mock_slack_client.update_message_with_blocks.return_value = True
        
        # Execute
        self.handler.handle_feedback_button(payload)
        
        # Verify feedback was attempted
        self.mock_feedback_client.send_feedback.assert_called_once()
        
        # Verify error message was shown
        self.mock_slack_client.get_message.assert_called_once_with("C1234567890", "1234567890.123456")
        self.mock_slack_client.update_message_with_blocks.assert_called_once()
    
    def test_remove_feedback_buttons_and_add_thanks(self):
        """Test removing feedback buttons and adding thank you message."""
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "Test response"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "Sources: ..."}]},
            {"type": "actions", "block_id": "feedback_actions", "elements": []},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": "AI disclosure"}]}
        ]
        
        result = self.handler._remove_feedback_buttons_and_add_thanks(blocks)
        
        # Should have all blocks except feedback_actions, plus thank you
        assert len(result) == 4
        assert result[0]["type"] == "section"
        assert result[1]["type"] == "context"  # Sources
        assert result[2]["type"] == "context"  # AI disclosure
        assert result[3]["type"] == "context"  # Thank you
        assert result[3]["block_id"] == "feedback_thanks"
        assert "Thank you for your feedback!" in result[3]["elements"][0]["text"]
    
    def test_remove_feedback_buttons_and_add_error(self):
        """Test removing feedback buttons and adding error message."""
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "Test response"}},
            {"type": "actions", "block_id": "feedback_actions", "elements": []},
            {"type": "context", "block_id": "feedback_thanks", "elements": []}  # Existing thank you
        ]
        
        result = self.handler._remove_feedback_buttons_and_add_error(blocks)
        
        # Should have section block plus error
        assert len(result) == 2
        assert result[0]["type"] == "section"
        assert result[1]["type"] == "context"  # Error
        assert result[1]["block_id"] == "feedback_error"
        assert "Oops, something went wrong sending feedback!" in result[1]["elements"][0]["text"] 