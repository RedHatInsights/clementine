"""Slack context extraction for question answering."""

import logging
from typing import List, Optional
from dataclasses import dataclass
from slack_sdk.errors import SlackApiError
from slack_sdk.web.client import WebClient

logger = logging.getLogger(__name__)


@dataclass
class SlackMessage:
    """Value object representing a Slack message for context."""
    text: str
    user_id: str
    timestamp: str
    user_name: Optional[str] = None
    thread_ts: Optional[str] = None
    
    def to_context_string(self) -> str:
        """Convert message to a context string for LLM consumption."""
        # Use real name if available, otherwise fall back to user ID
        display_name = self.user_name or self.user_id
        return f"{display_name}: {self.text}"


class SlackContextExtractor:
    """Extracts Slack channel/thread context for question answering.
    
    This class follows the single responsibility principle by only handling
    the extraction of Slack conversation context. It doesn't know about
    LLM APIs or question processing.
    """
    
    def __init__(self, client: WebClient, max_messages: int = 50):
        self.client = client
        self.max_messages = max_messages
        self._user_name_cache = {}  # Cache user names to avoid repeated API calls
    
    def extract_thread_context(self, channel: str, thread_ts: str) -> List[str]:
        """Extract context from a specific thread.
        
        Args:
            channel: Slack channel ID
            thread_ts: Thread timestamp
            
        Returns:
            List of context strings suitable for LLM consumption
        """
        try:
            logger.debug("Extracting thread context for channel %s, thread %s", channel, thread_ts)
            
            response = self.client.conversations_replies(
                channel=channel,
                ts=thread_ts,
                limit=self.max_messages
            )
            
            messages = response.get("messages", [])
            logger.debug("Retrieved %d messages from thread", len(messages))
            
            return self._messages_to_context(messages)
            
        except SlackApiError as e:
            logger.error("Failed to extract thread context: %s", e)
            return []
    
    def extract_channel_context(self, channel: str, limit: Optional[int] = None) -> List[str]:
        """Extract context from recent channel history.
        
        Args:
            channel: Slack channel ID
            limit: Maximum number of messages to retrieve (defaults to max_messages)
            
        Returns:
            List of context strings suitable for LLM consumption
        """
        try:
            limit = limit or self.max_messages
            logger.info("CONTEXT DEBUG: Extracting channel context for channel %s, limit %d", channel, limit)
            
            response = self.client.conversations_history(
                channel=channel,
                limit=limit
            )
            
            messages = response.get("messages", [])
            logger.info("CONTEXT DEBUG: Slack API returned %d raw messages for channel %s", len(messages), channel)
            
            # Log first message for debugging
            if messages:
                first_msg = messages[0]
                logger.info("CONTEXT DEBUG: First message - Text: %s, User: %s, Channel: %s", 
                           first_msg.get("text", "")[:50] + "..." if len(first_msg.get("text", "")) > 50 else first_msg.get("text", ""),
                           first_msg.get("user", "unknown"),
                           channel)
            
            # Reverse to get chronological order (Slack returns newest first)
            messages.reverse()
            
            context = self._messages_to_context(messages)
            logger.info("CONTEXT DEBUG: Converted to %d context strings", len(context))
            
            return context
            
        except SlackApiError as e:
            logger.error("Failed to extract channel context for channel %s: %s", channel, e)
            return []
    
    def _messages_to_context(self, messages: List[dict]) -> List[str]:
        """Convert Slack messages to context strings.
        
        Filters out bot messages and system messages, keeping only
        relevant human conversation.
        """
        context_strings = []
        
        for message in messages:
            # Skip bot messages and system messages
            if message.get("bot_id") or message.get("subtype"):
                continue
                
            # Skip messages without text
            text = message.get("text", "").strip()
            if not text:
                continue
            
            user_id = message.get("user", "unknown")
            user_name = self._get_user_name(user_id)
            
            slack_message = SlackMessage(
                text=text,
                user_id=user_id,
                timestamp=message.get("ts", ""),
                user_name=user_name,
                thread_ts=message.get("thread_ts")
            )
            
            context_strings.append(slack_message.to_context_string())
        
        logger.debug("Converted %d messages to %d context strings", len(messages), len(context_strings))
        return context_strings
    
    def _get_user_name(self, user_id: str) -> Optional[str]:
        """Get user display name from Slack API with caching."""
        if not user_id or user_id == "unknown":
            return None
            
        # Check cache first
        if user_id in self._user_name_cache:
            return self._user_name_cache[user_id]
        
        try:
            response = self.client.users_info(user=user_id)
            user_info = response.get("user", {})
            
            # Try to get real name first, then display name, then fall back to user ID
            real_name = user_info.get("real_name", "").strip()
            display_name = user_info.get("profile", {}).get("display_name", "").strip()
            username = user_info.get("name", "").strip()
            
            # Prefer real name, then display name, then username
            user_name = real_name or display_name or username or user_id
            
            # Cache the result
            self._user_name_cache[user_id] = user_name
            return user_name
            
        except SlackApiError as e:
            logger.warning("Failed to get user info for %s: %s", user_id, e)
            # Cache the failure to avoid repeated API calls
            self._user_name_cache[user_id] = None
            return None