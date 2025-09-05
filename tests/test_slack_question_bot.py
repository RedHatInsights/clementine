"""Tests for SlackQuestionBot."""

import pytest
from unittest.mock import Mock, patch
from slack_sdk.web.client import WebClient

from clementine.slack_question_bot import SlackQuestionBot
from clementine.slack_client import SlackClient
from clementine.slack_context_extractor import SlackContextExtractor
from clementine.advanced_chat_client import AdvancedChatClient, ChunksRequest
from clementine.tangerine import TangerineResponse
from clementine.formatters import MessageFormatter
from clementine.error_handling import ErrorHandler
from clementine.room_config_service import RoomConfigService, ProcessedRoomConfig


class TestSlackQuestionBot:
    """Test SlackQuestionBot functionality."""
    
    @pytest.fixture
    def mock_slack_client(self):
        """Create mock SlackClient."""
        return Mock(spec=SlackClient)
    
    @pytest.fixture
    def mock_context_extractor(self):
        """Create mock SlackContextExtractor."""
        return Mock(spec=SlackContextExtractor)
    
    @pytest.fixture
    def mock_advanced_chat_client(self):
        """Create mock AdvancedChatClient."""
        mock_client = Mock(spec=AdvancedChatClient)
        mock_client.model_override = None  # Default to None
        return mock_client
    
    @pytest.fixture
    def mock_formatter(self):
        """Create mock ResponseFormatter."""
        return Mock(spec=MessageFormatter)
    
    @pytest.fixture
    def mock_slack_web_client(self):
        """Create mock Slack WebClient."""
        return Mock(spec=WebClient)
    
    @pytest.fixture
    def mock_room_config_service(self):
        """Create mock RoomConfigService."""
        mock_service = Mock(spec=RoomConfigService)
        # Setup default return value for get_room_config
        mock_service.get_room_config.return_value = ProcessedRoomConfig(
            room_id="test_channel",
            assistant_list=["test_assistant"],
            system_prompt="Test prompt",
            slack_context_size=50
        )
        return mock_service
    
    @pytest.fixture
    def bot(self, mock_slack_client, mock_context_extractor, mock_advanced_chat_client, mock_formatter, mock_room_config_service):
        """Create SlackQuestionBot for testing."""
        return SlackQuestionBot(
            slack_client=mock_slack_client,
            context_extractor=mock_context_extractor,
            advanced_chat_client=mock_advanced_chat_client,
            bot_name="TestBot",
            room_config_service=mock_room_config_service,
            user_prompt="User's Question:\n{question}\n\nContext:\n{context}",
            system_prompt="Test system prompt for analysis",
            formatter=mock_formatter
        )
    
    def test_init(self, mock_slack_client, mock_context_extractor, mock_advanced_chat_client, mock_room_config_service):
        """Test initialization."""
        bot = SlackQuestionBot(
            slack_client=mock_slack_client,
            context_extractor=mock_context_extractor,
            advanced_chat_client=mock_advanced_chat_client,
            bot_name="TestBot",
            room_config_service=mock_room_config_service,
            user_prompt="User's Question:\n{question}\n\nContext:\n{context}",
            system_prompt="Test system prompt for analysis"
        )
        
        assert bot.slack_client == mock_slack_client
        assert bot.context_extractor == mock_context_extractor
        assert bot.advanced_chat_client == mock_advanced_chat_client
        assert bot.bot_name == "TestBot"
        assert bot.room_config_service == mock_room_config_service
        assert isinstance(bot.formatter, MessageFormatter)  # default
        assert isinstance(bot.error_handler, ErrorHandler)
    
    def test_handle_question_success_with_thread(self, bot, mock_slack_client, mock_context_extractor, 
                                                 mock_advanced_chat_client, mock_formatter, mock_slack_web_client):
        """Test successful question handling with thread context."""
        # Setup mocks
        mock_slack_client.post_loading_message.return_value = "loading_ts_123"
        mock_context_extractor.extract_thread_context.return_value = [
            "User A: Working on the feature",
            "User B: Looks good to me"
        ]
        
        mock_response = TangerineResponse(
            text="They are discussing feature development.",
            metadata=[],
            interaction_id="interaction_123"
        )
        mock_advanced_chat_client.chat_with_chunks.return_value = mock_response
        mock_formatter.format_with_sources.return_value = "Formatted response"
        
        # Execute
        bot.handle_question(
            question="What are they talking about?",
            channel="C123456",
            thread_ts="1234567890.123",
            user_id="U123456",
            slack_web_client=mock_slack_web_client
        )
        
        # Verify calls
        mock_slack_client.post_loading_message.assert_called_once_with("C123456", "1234567890.123")
        mock_context_extractor.extract_thread_context.assert_called_once_with("C123456", "1234567890.123", limit=50)
        mock_context_extractor.extract_channel_context.assert_not_called()
        
        # Verify advanced chat client call
        mock_advanced_chat_client.chat_with_chunks.assert_called_once()
        call_args = mock_advanced_chat_client.chat_with_chunks.call_args[0][0]
        assert isinstance(call_args, ChunksRequest)
        assert call_args.query == "What are they talking about?"
        assert call_args.chunks == ["User A: Working on the feature", "User B: Looks good to me"]
        assert call_args.client_name == "TestBot"
        assert call_args.prompt  # Should have a prompt
        
        mock_formatter.format_with_sources.assert_called_once_with(mock_response)
        mock_slack_client.update_message.assert_called_once_with("C123456", "loading_ts_123", "Formatted response")
    
    def test_handle_question_success_without_thread(self, bot, mock_slack_client, mock_context_extractor, 
                                                   mock_advanced_chat_client, mock_formatter, mock_slack_web_client):
        """Test successful question handling without thread context (channel history)."""
        # Setup mocks
        mock_slack_client.post_loading_message.return_value = "loading_ts_123"
        mock_context_extractor.extract_channel_context.return_value = [
            "User A: Good morning",
            "User B: How's the project going?"
        ]
        
        mock_response = TangerineResponse(
            text="They are having a morning check-in about the project.",
            metadata=[],
            interaction_id="interaction_123"
        )
        mock_advanced_chat_client.chat_with_chunks.return_value = mock_response
        mock_formatter.format_with_sources.return_value = "Formatted response"
        
        # Execute
        bot.handle_question(
            question="What's the conversation about?",
            channel="C123456",
            thread_ts=None,  # No thread
            user_id="U123456",
            slack_web_client=mock_slack_web_client
        )
        
        # Verify calls
        mock_slack_client.post_loading_message.assert_called_once_with("C123456", None)
        mock_context_extractor.extract_channel_context.assert_called_once_with("C123456", limit=50)
        mock_context_extractor.extract_thread_context.assert_not_called()
        
        # Verify advanced chat client call
        mock_advanced_chat_client.chat_with_chunks.assert_called_once()
        call_args = mock_advanced_chat_client.chat_with_chunks.call_args[0][0]
        assert call_args.chunks == ["User A: Good morning", "User B: How's the project going?"]
        assert call_args.prompt  # Should have a prompt
    
    def test_handle_question_no_loading_message(self, bot, mock_slack_client, mock_slack_web_client):
        """Test handling when loading message fails to post."""
        mock_slack_client.post_loading_message.return_value = None
        
        bot.handle_question(
            question="Test question",
            channel="C123456",
            thread_ts="1234567890.123",
            user_id="U123456",
            slack_web_client=mock_slack_web_client
        )
        
        # Should return early without further processing
        mock_slack_client.post_loading_message.assert_called_once()
        # No other methods should be called
        assert not hasattr(mock_slack_client, 'update_message') or not mock_slack_client.update_message.called
    
    def test_handle_question_no_context(self, bot, mock_slack_client, mock_context_extractor, mock_slack_web_client):
        """Test handling when no context is available."""
        mock_slack_client.post_loading_message.return_value = "loading_ts_123"
        mock_context_extractor.extract_thread_context.return_value = []  # No context
        
        bot.handle_question(
            question="What are they talking about?",
            channel="C123456",
            thread_ts="1234567890.123",
            user_id="U123456",
            slack_web_client=mock_slack_web_client
        )
        
        # Should update message with error
        mock_slack_client.update_message.assert_called_once_with(
            "C123456", 
            "loading_ts_123", 
            "I couldn't find any recent conversation context to answer your question about."
        )
    
    def test_handle_question_exception_handling(self, bot, mock_slack_client, mock_context_extractor, 
                                               mock_slack_web_client):
        """Test exception handling during question processing."""
        mock_slack_client.post_loading_message.return_value = "loading_ts_123"
        mock_context_extractor.extract_thread_context.side_effect = Exception("API Error")
        
        bot.handle_question(
            question="Test question",
            channel="C123456",
            thread_ts="1234567890.123",
            user_id="U123456",
            slack_web_client=mock_slack_web_client
        )
        
        # Should update message with error
        mock_slack_client.update_message.assert_called_once()
        call_args = mock_slack_client.update_message.call_args[0]
        assert call_args[0] == "C123456"
        assert call_args[1] == "loading_ts_123"
        assert "TestBot hit a snag" in call_args[2]  # Error message from ErrorHandler
    
    def test_handle_question_with_block_kit_response(self, bot, mock_slack_client, mock_context_extractor, 
                                                    mock_advanced_chat_client, mock_formatter, mock_slack_web_client):
        """Test handling with Block Kit formatted response."""
        # Setup mocks
        mock_slack_client.post_loading_message.return_value = "loading_ts_123"
        mock_context_extractor.extract_thread_context.return_value = ["User A: Hello"]
        
        mock_response = TangerineResponse(text="Response", metadata=[], interaction_id="123")
        mock_advanced_chat_client.chat_with_chunks.return_value = mock_response
        
        # Mock formatter returns Block Kit format
        mock_formatter.format_with_sources.return_value = {
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Response"}}],
            "text": "Response"
        }
        
        # Execute
        bot.handle_question(
            question="Test",
            channel="C123456", 
            thread_ts="1234567890.123",
            user_id="U123456",
            slack_web_client=mock_slack_web_client
        )
        
        # Should call update_message_with_blocks instead of update_message
        mock_slack_client.update_message_with_blocks.assert_called_once()
        mock_slack_client.update_message.assert_not_called()
    
    @patch('clementine.slack_question_bot.generate_session_id')
    def test_get_chat_response_session_id_generation(self, mock_generate_session_id, bot, mock_advanced_chat_client):
        """Test session ID generation for chat response."""
        mock_generate_session_id.return_value = "generated_session_id"
        
        mock_response = TangerineResponse(text="Response", metadata=[], interaction_id="123")
        mock_advanced_chat_client.chat_with_chunks.return_value = mock_response
        
        result = bot._get_chat_response(
            question="Test question",
            context_chunks=["chunk1", "chunk2"],
            channel="C123456",
            thread_ts="1234567890.123"
        )
        
        # Verify session ID generation
        mock_generate_session_id.assert_called_once_with("C123456", "1234567890.123")
        
        # Verify chat call
        mock_advanced_chat_client.chat_with_chunks.assert_called_once()
        call_args = mock_advanced_chat_client.chat_with_chunks.call_args[0][0]
        assert call_args.session_id == "generated_session_id"
    
    @patch('clementine.slack_question_bot.generate_session_id')
    def test_get_chat_response_no_thread(self, mock_generate_session_id, bot, mock_advanced_chat_client):
        """Test session ID generation when no thread timestamp."""
        mock_generate_session_id.return_value = "generated_session_id"
        
        mock_response = TangerineResponse(text="Response", metadata=[], interaction_id="123")
        mock_advanced_chat_client.chat_with_chunks.return_value = mock_response
        
        bot._get_chat_response(
            question="Test question",
            context_chunks=["chunk1"],
            channel="C123456",
            thread_ts=None
        )
        
        # Should use channel as fallback for session ID
        mock_generate_session_id.assert_called_once_with("C123456", "C123456")
    
    def test_model_override_passed_to_chunks_request(self, bot, mock_advanced_chat_client, mock_context_extractor):
        """Test that model_override is properly passed to ChunksRequest."""
        # Setup mock with model override
        mock_advanced_chat_client.model_override = "chatgpt-4o"
        mock_context_extractor.extract_thread_context.return_value = ["Test context"]
        
        mock_response = TangerineResponse(text="Response", metadata=[], interaction_id="123")
        mock_advanced_chat_client.chat_with_chunks.return_value = mock_response
        
        # Call the method
        bot._get_chat_response(
            question="Test question",
            context_chunks=["Test context"],
            channel="C123456",
            thread_ts="1234567890.123"
        )
        
        # Verify the ChunksRequest includes the model override
        mock_advanced_chat_client.chat_with_chunks.assert_called_once()
        call_args = mock_advanced_chat_client.chat_with_chunks.call_args[0][0]
        assert isinstance(call_args, ChunksRequest)
        assert call_args.model == "chatgpt-4o"
    
    def test_model_override_none_not_passed_to_chunks_request(self, bot, mock_advanced_chat_client, mock_context_extractor):
        """Test that None model_override is not passed to ChunksRequest."""
        # Setup mock with no model override
        mock_advanced_chat_client.model_override = None
        mock_context_extractor.extract_thread_context.return_value = ["Test context"]
        
        mock_response = TangerineResponse(text="Response", metadata=[], interaction_id="123")
        mock_advanced_chat_client.chat_with_chunks.return_value = mock_response
        
        # Call the method
        bot._get_chat_response(
            question="Test question",
            context_chunks=["Test context"],
            channel="C123456",
            thread_ts="1234567890.123"
        )
        
        # Verify the ChunksRequest model is None
        mock_advanced_chat_client.chat_with_chunks.assert_called_once()
        call_args = mock_advanced_chat_client.chat_with_chunks.call_args[0][0]
        assert isinstance(call_args, ChunksRequest)
        assert call_args.model is None