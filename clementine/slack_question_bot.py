"""Slack question bot for answering questions about channel context."""

import logging
import uuid
from typing import Dict, Union
from slack_sdk.web.client import WebClient

from .slack_client import SlackClient
from .slack_context_extractor import SlackContextExtractor
from .advanced_chat_client import AdvancedChatClient, ChunksRequest
from .formatters import ResponseFormatter, MessageFormatter
from .error_handling import ErrorHandler

logger = logging.getLogger(__name__)


class SlackQuestionBot:
    """Bot for answering questions about Slack channel context.
    
    This class orchestrates the entire workflow of:
    1. Extracting context from Slack channels/threads
    2. Sending questions with context to the advanced chat API
    3. Formatting and posting responses back to Slack
    
    It follows the single responsibility principle by focusing only on
    the Slack context question workflow.
    """
    
    # Optimized system prompt for Slack RAG responses
    SLACK_SYSTEM_PROMPT = """You are a helpful Slack bot that answers questions based on conversation history.

Instructions:
- Answer questions directly using the conversation context provided
- Use plain text only (no markdown, bold, italic, or special formatting)
- Be conversational and helpful, providing sufficient detail to be useful
- Don't mention sources, citations, or explain your methodology
- Don't use numbered lists or bullet points for simple answers
- If you need to list multiple things, use natural language instead
- If information is unclear or missing, say so naturally
- Focus on being accurate and helpful rather than overly brief

If you don't see any information in the context or a question, say so.

"""
    
    def __init__(self, 
                 slack_client: SlackClient,
                 context_extractor: SlackContextExtractor,
                 advanced_chat_client: AdvancedChatClient,
                 bot_name: str,
                 formatter: ResponseFormatter = None):
        self.slack_client = slack_client
        self.context_extractor = context_extractor
        self.advanced_chat_client = advanced_chat_client
        self.bot_name = bot_name
        self.formatter = formatter or MessageFormatter()
        self.error_handler = ErrorHandler(bot_name)
    
    def handle_question(self, question: str, channel: str, thread_ts: str, 
                       user_id: str, slack_web_client: WebClient) -> None:
        """Handle a question about the current Slack context.
        
        Args:
            question: The user's question
            channel: Slack channel ID
            thread_ts: Thread timestamp (may be None for channel questions)
            user_id: User who asked the question
            slack_web_client: Slack web client for posting responses
        """
        logger.info("Processing Slack context question from user %s in channel %s", user_id, channel)
        
        # Post loading message
        loading_ts = self.slack_client.post_loading_message(channel, thread_ts)
        if not loading_ts:
            logger.warning("Failed to post loading message, aborting question handling")
            return
        
        try:
            # Extract context from Slack
            context_chunks = self._extract_context(channel, thread_ts)
            
            if not context_chunks:
                error_message = "I couldn't find any recent conversation context to answer your question about."
                self._update_message_with_error(channel, loading_ts, error_message)
                return
            
            # Get response from advanced chat API
            response = self._get_chat_response(question, context_chunks, channel, thread_ts)
            
            # Format and post response
            formatted_message = self.formatter.format_with_sources(response)
            self._update_message(channel, loading_ts, formatted_message)
            
            logger.info("Successfully handled Slack context question for user %s", user_id)
            
        except Exception as error:
            logger.error("Error handling Slack context question: %s", error)
            error_message = self.error_handler.format_error_message(error)
            self._update_message_with_error(channel, loading_ts, error_message)
    
    def _extract_context(self, channel: str, thread_ts: str) -> list[str]:
        """Extract context from Slack channel or thread."""
        if thread_ts:
            # Extract from specific thread
            logger.info("SLACK RAG DEBUG: Extracting context from THREAD %s in channel %s", thread_ts, channel)
            context = self.context_extractor.extract_thread_context(channel, thread_ts)
        else:
            # Extract from recent channel history
            logger.info("SLACK RAG DEBUG: Extracting context from CHANNEL %s", channel)
            context = self.context_extractor.extract_channel_context(channel)
        
        # Log first few context items for debugging
        if context:
            logger.info("SLACK RAG DEBUG: Retrieved %d context chunks. First chunk: %s", 
                       len(context), context[0][:100] + "..." if len(context[0]) > 100 else context[0])
        else:
            logger.warning("SLACK RAG DEBUG: No context retrieved!")
            
        return context
    
    def _get_chat_response(self, question: str, context_chunks: list[str], 
                          channel: str, thread_ts: str):
        """Get response from advanced chat API using context chunks."""
        # Create unique session ID for each Slack RAG query to avoid cached responses
        # We want each slash command to be treated as a fresh conversation
        session_id = str(uuid.uuid4())
        
        logger.info("SLACK RAG DEBUG: Sending to API - Channel: %s, Thread: %s, Session ID: %s", 
                   channel, thread_ts, session_id)
        logger.info("SLACK RAG DEBUG: Question: %s", question)
        logger.info("SLACK RAG DEBUG: Using %d context chunks", len(context_chunks))
        
        # Log first few chunks to verify we're getting correct context
        if context_chunks:
            logger.info("SLACK RAG DEBUG: First chunk: %s", context_chunks[0][:150] + "..." if len(context_chunks[0]) > 150 else context_chunks[0])
            if len(context_chunks) > 1:
                logger.info("SLACK RAG DEBUG: Second chunk: %s", context_chunks[1][:150] + "..." if len(context_chunks[1]) > 150 else context_chunks[1])
        
        # Create optimized user prompt with question and context interpolation
        user_prompt = f"""Question: {question}

Context: The following are recent messages from this Slack channel: {context_chunks}

Please answer the question above using the context provided. Be helpful and conversational, but don't mention sources or explain your methodology.

Take care to differentiate between the various users in the context. The context you are provided are chat messages from users in a chat room. You'll see
the usernames and what they said. Make sure to differentiate between users correctly and if you are asked about specific users, look at the usernames and make sure you are answering the question about the correct user.
"""
        
        chunks_request = ChunksRequest(
            query=question,
            chunks=context_chunks,
            session_id=session_id,
            client_name=self.bot_name,
            system_prompt=self.SLACK_SYSTEM_PROMPT,
            user_prompt=user_prompt
        )
        
        return self.advanced_chat_client.chat_with_chunks(chunks_request)
    
    def _update_message(self, channel: str, ts: str, formatted_message: Union[str, Dict]) -> None:
        """Update Slack message with response (text or Block Kit)."""
        if isinstance(formatted_message, dict):
            # Block Kit message
            success = self.slack_client.update_message_with_blocks(
                channel, ts, formatted_message
            )
        else:
            # Plain text message
            success = self.slack_client.update_message(channel, ts, formatted_message)
        
        if not success:
            logger.warning("Failed to update message %s in channel %s", ts, channel)
    
    def _update_message_with_error(self, channel: str, ts: str, error_message: str) -> None:
        """Update message with error text."""
        success = self.slack_client.update_message(channel, ts, error_message)
        if not success:
            logger.warning("Failed to update message %s with error in channel %s", ts, channel)