"""Slack question bot for answering questions about channel context."""

import logging
from typing import Dict, Union
from slack_sdk.web.client import WebClient

from .slack_client import SlackClient
from .slack_context_extractor import SlackContextExtractor
from .advanced_chat_client import AdvancedChatClient, ChunksRequest
from .tangerine import generate_session_id
from .formatters import ResponseFormatter, MessageFormatter
from .error_handling import ErrorHandler
from .room_config_service import RoomConfigService

logger = logging.getLogger(__name__)

# Slack analysis prompts are loaded from files at startup:
# - System prompt: slack_analysis_system_prompt.txt (NEVER overridden by room config)
# - User prompt: default_user_prompt.txt (same for ALL code paths)


class SlackQuestionBot:
    """Bot for answering questions about Slack channel context.
    
    This class orchestrates the entire workflow of:
    1. Extracting context from Slack channels/threads
    2. Sending questions with context to the advanced chat API
    3. Formatting and posting responses back to Slack
    
    It follows the single responsibility principle by focusing only on
    the Slack context question workflow.
    """
    
    def __init__(self, 
                 slack_client: SlackClient,
                 context_extractor: SlackContextExtractor,
                 advanced_chat_client: AdvancedChatClient,
                 bot_name: str,
                 room_config_service: RoomConfigService,
                 user_prompt: str,
                 system_prompt: str,
                 formatter: ResponseFormatter = None):
        self.slack_client = slack_client
        self.context_extractor = context_extractor
        self.advanced_chat_client = advanced_chat_client
        self.bot_name = bot_name
        self.room_config_service = room_config_service
        self.formatter = formatter or MessageFormatter()
        self.error_handler = ErrorHandler(bot_name)
        # Slack analysis system prompt is NEVER overridden by room config
        if not system_prompt:
            raise ValueError("system_prompt is required and must be loaded from slack_analysis_system_prompt.txt")
        self.system_prompt = system_prompt
        # User prompt is always loaded from default_user_prompt.txt (same for all code paths)
        if not user_prompt:
            raise ValueError("user_prompt is required and must be loaded from default_user_prompt.txt")
        self.user_prompt = user_prompt
    
    def handle_question(self, question: str, channel: str, thread_ts: str, 
                       user_id: str, slack_web_client: WebClient, ephemeral: bool = False) -> None:
        """Handle a question about the current Slack context.
        
        Args:
            question: The user's question
            channel: Slack channel ID
            thread_ts: Thread timestamp (may be None for channel questions)
            user_id: User who asked the question
            slack_web_client: Slack web client for posting responses
            ephemeral: If True, response will be visible only to the user (for slash commands)
        """
        logger.info("Processing Slack context question from user %s in channel %s (ephemeral: %s)", 
                   user_id, channel, ephemeral)
        
        # Post loading message (ephemeral if requested)
        loading_ts = self.slack_client.post_loading_message(
            channel, thread_ts, user_id if ephemeral else None
        )
        if not loading_ts:
            logger.warning("Failed to post loading message, aborting question handling")
            return
        
        try:
            # Extract context from Slack
            context_chunks = self._extract_context(channel, thread_ts)
            
            if not context_chunks:
                error_message = "I couldn't find any recent conversation context to answer your question about."
                self._update_message_with_error(channel, loading_ts, error_message, 
                                               user_id if ephemeral else None)
                return
            
            # Get response from advanced chat API
            response = self._get_chat_response(question, context_chunks, channel, thread_ts)
            
            # Format and post response
            formatted_message = self.formatter.format_with_sources(response)
            self._update_message(channel, loading_ts, formatted_message, 
                               user_id if ephemeral else None)
            
            logger.info("Successfully handled Slack context question for user %s", user_id)
            
        except Exception as error:
            logger.error("Error handling Slack context question: %s", error)
            error_message = self.error_handler.format_error_message(error)
            self._update_message_with_error(channel, loading_ts, error_message, 
                                           user_id if ephemeral else None)
    
    def _extract_context(self, channel: str, thread_ts: str) -> list[str]:
        """Extract context from Slack channel or thread using room-specific context size."""
        # Get room-specific configuration
        room_config = self.room_config_service.get_room_config(channel)
        context_limit = room_config.slack_context_size
        
        if thread_ts:
            # Extract from specific thread
            logger.debug("Extracting context from thread %s with limit %d", thread_ts, context_limit)
            return self.context_extractor.extract_thread_context(channel, thread_ts, limit=context_limit)
        else:
            # Extract from recent channel history
            logger.debug("Extracting context from channel %s with limit %d", channel, context_limit)
            return self.context_extractor.extract_channel_context(channel, limit=context_limit)
    
    def _get_chat_response(self, question: str, context_chunks: list[str], 
                          channel: str, thread_ts: str):
        """Get response from advanced chat API using context chunks."""
        # Create deterministic session ID
        session_id = generate_session_id(channel, thread_ts or channel)
        
        chunks_request = ChunksRequest(
            query=question,
            chunks=context_chunks,
            session_id=session_id,
            client_name=self.bot_name,
            prompt=self.system_prompt,
            user_prompt=self.user_prompt,
            model=self.advanced_chat_client.model_override
        )
        
        logger.debug("Requesting response from advanced chat API with %d chunks", 
                    len(context_chunks))
        return self.advanced_chat_client.chat_with_chunks(chunks_request)
    
    def _update_message(self, channel: str, ts: str, formatted_message: Union[str, Dict], 
                       user_id: str = None) -> None:
        """Update Slack message with response (text or Block Kit).
        
        Args:
            channel: Slack channel ID
            ts: Message timestamp
            formatted_message: Response message (text or Block Kit dict)
            user_id: If provided, updates an ephemeral message for this user
        """
        if isinstance(formatted_message, dict):
            # Block Kit message
            success = self.slack_client.update_message_with_blocks(
                channel, ts, formatted_message, user_id
            )
        else:
            # Plain text message
            success = self.slack_client.update_message(channel, ts, formatted_message, user_id)
        
        if not success:
            logger.warning("Failed to update message %s in channel %s", ts, channel)
    
    def _update_message_with_error(self, channel: str, ts: str, error_message: str, 
                                  user_id: str = None) -> None:
        """Update message with error text.
        
        Args:
            channel: Slack channel ID
            ts: Message timestamp
            error_message: Error message text
            user_id: If provided, updates an ephemeral message for this user
        """
        success = self.slack_client.update_message(channel, ts, error_message, user_id)
        if not success:
            logger.warning("Failed to update message %s with error in channel %s", ts, channel)