"""Slack client and event handling."""

import logging
import re
from typing import Optional
from dataclasses import dataclass
from slack_sdk.errors import SlackApiError
from slack_sdk.web.client import WebClient

logger = logging.getLogger(__name__)


@dataclass
class SlackEvent:
    """Value object representing a Slack mention event."""
    text: str
    user_id: str
    channel: str
    thread_ts: str
    
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
            thread_ts=event.get("thread_ts", event["ts"])
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
        # <@U followed by alphanumeric characters, then >
        mention_pattern = r'^<@U[A-Za-z0-9]+>\s*'
        return re.sub(mention_pattern, '', text).strip()


class SlackClient:
    """Wrapper for Slack operations with better error handling."""
    
    def __init__(self, client: WebClient, loading_text: str = ":hourglass_flowing_sand: Thinking..."):
        self.client = client
        self.loading_text = loading_text
    
    def _extract_error_code(self, slack_error: SlackApiError) -> str:
        """Extract error code from SlackApiError safely."""
        return slack_error.response.get('error', 'unknown') if hasattr(slack_error.response, 'get') else 'unknown'
    
    def post_loading_message(self, channel: str, thread_ts: str) -> Optional[str]:
        """Post loading message and return timestamp."""
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=self.loading_text,
                thread_ts=thread_ts
            )
            return response["ts"]
        except SlackApiError as e:
            error_code = self._extract_error_code(e)
            logger.error("Failed to post loading message: %s - %s", error_code, e)
            return None
    
    def update_message(self, channel: str, ts: str, text: str) -> bool:
        """Update message and return success status."""
        try:
            self.client.chat_update(channel=channel, ts=ts, text=text)
            return True
        except SlackApiError as e:
            error_code = self._extract_error_code(e)
            logger.error("Failed to update message: %s - %s", error_code, e)
            return False 