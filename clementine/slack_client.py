"""Slack client and event handling."""

import logging
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
        
        return cls(
            text=text,
            user_id=event["user"], 
            channel=event["channel"],
            thread_ts=event.get("thread_ts", event["ts"])
        )


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