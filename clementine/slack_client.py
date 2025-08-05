"""Slack client and event handling."""

import logging
import re
from typing import Optional
from dataclasses import dataclass
from slack_sdk.errors import SlackApiError
from slack_sdk.web.client import WebClient

from .loading_message_provider import LoadingMessageProvider

logger = logging.getLogger(__name__)


@dataclass
class SlackEvent:
    """Value object representing a Slack mention event."""
    text: str
    user_id: str
    channel: str
    thread_ts: str
    room_id: str  # For room-specific configuration
    
    @classmethod
    def from_dict(cls, event: dict) -> 'SlackEvent':
        """Create SlackEvent from Slack event dictionary with validation."""
        required_fields = ["text", "user", "channel", "ts"]
        missing_fields = [field for field in required_fields if field not in event]
        
        if missing_fields:
            raise ValueError(f"Missing required event fields: {missing_fields}")
        
        # Additional validation
        text = event["text"].strip()
        if not text:
            raise ValueError("Event text cannot be empty")
        
        # Remove bot mention from the beginning of the text
        text = cls._strip_bot_mention(text)
        if not text:
            raise ValueError("Event text cannot be empty after removing bot mention")
        
        return cls(
            text=text,
            user_id=event["user"], 
            channel=event["channel"],
            thread_ts=event.get("thread_ts", event["ts"]),
            room_id=event["channel"]  # Use channel as room_id for per-room configuration
        )
    
    @staticmethod
    def _strip_bot_mention(text: str) -> str:
        """Remove bot mention from the beginning of text.
        
        Slack mentions have format <@U1234567890> where U1234567890 is the user ID.
        This method removes such mentions from the start of the text.
        
        Args:
            text: The original text that may contain a bot mention
            
        Returns:
            Text with bot mention removed and whitespace stripped
            
        Examples:
            "<@U098PF40S1E> what is tekton?" -> "what is tekton?"
            "what is tekton?" -> "what is tekton?"
        """
        # Pattern to match Slack user mentions at the start of text
        # <@U or <@W followed by alphanumeric characters, underscores, or hyphens, then >
        # Slack user IDs can start with U (regular users) or W (Enterprise users)
        mention_pattern = r'^<@[UW][A-Za-z0-9_-]+>\s*'
        return re.sub(mention_pattern, '', text).strip()


class SlackClient:
    """Wrapper for Slack operations with better error handling."""
    
    def __init__(self, client: WebClient, loading_message_provider: LoadingMessageProvider = None):
        self.client = client
        self.loading_message_provider = loading_message_provider or LoadingMessageProvider()
    
    def _extract_error_code(self, slack_error: SlackApiError) -> str:
        """Extract error code from SlackApiError safely."""
        return slack_error.response.get('error', 'unknown') if hasattr(slack_error.response, 'get') else 'unknown'
    
    def post_loading_message(self, channel: str, thread_ts: str) -> Optional[str]:
        """Post loading message and return timestamp."""
        try:
            loading_message = self.loading_message_provider.get_random_message()
            response = self.client.chat_postMessage(
                channel=channel,
                text=loading_message,
                thread_ts=thread_ts
            )
            return response["ts"]
        except SlackApiError as e:
            error_code = self._extract_error_code(e)
            logger.error("Failed to post loading message: %s - %s", error_code, e)
            return None
    
    def update_message(self, channel: str, ts: str, text: str) -> bool:
        """Update message with plain text and return success status."""
        try:
            self.client.chat_update(channel=channel, ts=ts, text=text)
            return True
        except SlackApiError as e:
            error_code = self._extract_error_code(e)
            logger.error("Failed to update message: %s - %s", error_code, e)
            return False
    
    def update_message_with_blocks(self, channel: str, ts: str, blocks_message: dict) -> bool:
        """Update message with Block Kit blocks and return success status."""
        try:
            self.client.chat_update(
                channel=channel, 
                ts=ts, 
                blocks=blocks_message["blocks"],
                text=blocks_message["text"]  # Fallback text for notifications
            )
            return True
        except SlackApiError as e:
            error_code = self._extract_error_code(e)
            logger.error("Failed to update message with blocks: %s - %s", error_code, e)
            return False
    
    def get_message(self, channel: str, ts: str) -> Optional[dict]:
        """Get message content by channel and timestamp."""
        try:
            # Convert timestamp to float for calculations
            target_ts = float(ts)
            
            # Get a small window around the target timestamp (±10 seconds)
            oldest = str(target_ts - 10)
            latest = str(target_ts + 10)
            
            response = self.client.conversations_history(
                channel=channel,
                oldest=oldest,
                latest=latest,
                inclusive=True,
                limit=100  # Get more messages to search through
            )
            
            messages = response.get("messages", [])
            
            # Find the exact message by timestamp
            for message in messages:
                if message.get("ts") == ts:
                    logger.debug("Found message with ts %s in channel %s", ts, channel)
                    return message
            
            # If exact match not found, try finding the closest one
            closest_message = None
            min_diff = float('inf')
            
            for message in messages:
                msg_ts = float(message.get("ts", 0))
                diff = abs(msg_ts - target_ts)
                if diff < min_diff:
                    min_diff = diff
                    closest_message = message
            
            if closest_message and min_diff < 1.0:  # Within 1 second
                logger.debug("Found closest message (diff: %.3fs) for ts %s in channel %s", 
                           min_diff, ts, channel)
                return closest_message
            
            logger.warning("No message found for ts %s in channel %s (searched %d messages)", 
                          ts, channel, len(messages))
            return None
                
        except SlackApiError as e:
            error_code = self._extract_error_code(e)
            logger.error("Failed to get message: %s - %s", error_code, e)
            return None
        except ValueError as e:
            logger.error("Invalid timestamp format %s: %s", ts, e)
            return None 