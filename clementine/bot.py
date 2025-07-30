"""Main bot orchestration logic."""

import logging
from typing import Dict
from slack_sdk.web.client import WebClient

from .slack_client import SlackClient, SlackEvent
from .tangerine import TangerineClient
from .formatters import MessageFormatter
from .error_handling import ErrorHandler

logger = logging.getLogger(__name__)


class ClementineBot:
    """Main bot orchestrator following single responsibility principle."""
    
    def __init__(self, tangerine_client: TangerineClient, slack_client: SlackClient,
                 bot_name: str, assistant_list: list[str], default_prompt: str):
        self.tangerine_client = tangerine_client
        self.slack_client = slack_client
        self.bot_name = bot_name
        self.assistant_list = assistant_list
        self.default_prompt = default_prompt
        self.formatter = MessageFormatter()
        self.error_handler = ErrorHandler(bot_name)
    
    def handle_mention(self, event_dict: Dict, slack_web_client: WebClient) -> None:
        """Handle mention by orchestrating the response flow."""
        try:
            event = SlackEvent.from_dict(event_dict)
        except ValueError as e:
            logger.error("Invalid Slack event format: %s", e)
            return
            
        logger.info("Processing mention from user %s in channel %s", event.user_id, event.channel)
        
        loading_ts = self._post_loading_message(event)
        if not loading_ts:
            logger.warning("Failed to post loading message, aborting mention handling")
            return
            
        try:
            # Truncate very long queries for logging
            query_preview = event.text[:100] + "..." if len(event.text) > 100 else event.text
            logger.debug("Requesting response from Tangerine for query: %s", query_preview)
            response = self._get_tangerine_response(event)
            logger.debug("Received response with %d metadata sources", len(response.metadata))
            
            formatted_text = self.formatter.format_with_sources(response)
            self._update_message(event, loading_ts, formatted_text)
            logger.info("Successfully handled mention for user %s", event.user_id)
        except Exception as error:
            self._handle_error(event, loading_ts, error)
    
    def _post_loading_message(self, event: SlackEvent) -> str | None:
        """Post loading message."""
        return self.slack_client.post_loading_message(event.channel, event.thread_ts)
    
    def _get_tangerine_response(self, event: SlackEvent):
        """Get response from Tangerine API."""
        return self.tangerine_client.chat(
            assistants=self.assistant_list,
            query=event.text,
            session_id=event.user_id,
            client_name=self.bot_name,
            prompt=self.default_prompt
        )
    
    def _update_message(self, event: SlackEvent, loading_ts: str, text: str) -> None:
        """Update Slack message with response."""
        success = self.slack_client.update_message(event.channel, loading_ts, text)
        if not success:
            logger.warning("Failed to update message %s in channel %s", loading_ts, event.channel)
    
    def _handle_error(self, event: SlackEvent, loading_ts: str, error: Exception) -> None:
        """Handle and display error."""
        error_message = self.error_handler.format_error_message(error)
        logger.info("Displaying error message to user in channel %s", event.channel)
        success = self.slack_client.update_message(event.channel, loading_ts, error_message)
        if not success:
            logger.error("Failed to display error message to user - they won't see any response") 