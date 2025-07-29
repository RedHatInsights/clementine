import requests
import uuid
import logging
from typing import Dict, List, Optional, Any
from slack_sdk.errors import SlackApiError
from slack_sdk.web.client import WebClient
from dataclasses import dataclass

# Set up logger
logger = logging.getLogger(__name__)


@dataclass
class SlackEvent:
    """Value object representing a Slack mention event."""
    text: str
    user_id: str
    channel: str
    thread_ts: str
    
    @classmethod
    def from_dict(cls, event: Dict) -> 'SlackEvent':
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


@dataclass
class TangerineResponse:
    """Value object representing a Tangerine API response."""
    text: str
    metadata: List[Dict]
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TangerineResponse':
        return cls(
            text=data.get("text_content", "(No response from assistant)").strip(),
            metadata=data.get("search_metadata", [])
        )


class MessageFormatter:
    """Handles formatting of responses."""
    
    def format_with_sources(self, response: TangerineResponse) -> str:
        """Format response text with source citations."""
        if not response.metadata:
            return response.text
            
        sources = response.metadata[:3]
        links = self._build_source_links(sources)
        
        return response.text + f"\n\n*Sources:*\n{links}" if links else response.text
    
    def _build_source_links(self, sources: List[Dict]) -> str:
        """Build formatted source links with safe metadata access."""
        links = []
        for source in sources:
            try:
                metadata = source.get("metadata", {})
                url = metadata.get("citation_url")
                title = metadata.get("title", "Source")
                if url and title:
                    links.append(f"<{url}|{title}>")
            except (TypeError, AttributeError):
                # Skip malformed source entries
                logger.debug("Skipping malformed source metadata: %s", source)
                continue
        return "\n".join(links)


class SlackClient:
    """Wrapper for Slack operations with better error handling."""
    
    def __init__(self, client: WebClient, loading_text: str = ":hourglass_flowing_sand: Thinking..."):
        self.client = client
        self.loading_text = loading_text
    
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
            error_code = getattr(e.response, 'get', lambda x, default: 'unknown')('error', 'unknown')
            logger.error("Failed to post loading message: %s - %s", error_code, e)
            return None
    
    def update_message(self, channel: str, ts: str, text: str) -> bool:
        """Update message and return success status."""
        try:
            self.client.chat_update(channel=channel, ts=ts, text=text)
            return True
        except SlackApiError as e:
            error_code = getattr(e.response, 'get', lambda x, default: 'unknown')('error', 'unknown')
            logger.error("Failed to update message: %s - %s", error_code, e)
            return False


class TangerineClient:
    """Handles communication with the Tangerine API."""
    
    def __init__(self, api_url: str, api_token: str, timeout: int = 500):
        if not api_url or not api_token:
            raise ValueError("Both api_url and api_token are required")
        
        self.api_url = api_url.rstrip('/')  # Remove trailing slash
        self.api_token = api_token
        self.timeout = timeout
        self.chat_endpoint = f"{self.api_url}/api/assistants/chat"
    
    def chat(self, assistants: List[str], query: str, session_id: str, 
             client_name: str, prompt: str) -> TangerineResponse:
        """Send chat request and return structured response."""
        logger.debug("Sending chat request to Tangerine API for session %s", session_id)
        payload = self._build_payload(assistants, query, session_id, client_name, prompt)
        response_data = self._make_request(payload)
        logger.debug("Received response from Tangerine API")
        return TangerineResponse.from_dict(response_data)
    
    def _build_payload(self, assistants: List[str], query: str, session_id: str, 
                      client_name: str, prompt: str) -> Dict:
        """Build API request payload."""
        return {
            "assistants": assistants,
            "query": query,
            "sessionId": session_id,
            "interactionId": str(uuid.uuid4()),
            "client": client_name,
            "stream": False,
            "prompt": prompt
        }
    
    def _make_request(self, payload: Dict) -> Dict:
        """Make HTTP request to Tangerine API with comprehensive error handling."""
        try:
            response = requests.post(
                self.chat_endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Tangerine API request timed out after %d seconds", self.timeout)
            raise
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Tangerine API at %s", self.chat_endpoint)
            raise
        except requests.exceptions.HTTPError as e:
            logger.error("Tangerine API returned HTTP error %d: %s", e.response.status_code, e)
            raise
        except requests.exceptions.JSONDecodeError:
            logger.error("Tangerine API returned invalid JSON response")
            raise
        except Exception as e:
            logger.error("Unexpected error calling Tangerine API: %s", e)
            raise


class ErrorHandler:
    """Handles error scenarios."""
    
    def __init__(self, bot_name: str):
        self.bot_name = bot_name
    
    def format_error_message(self, error: Exception) -> str:
        """Format safe error message for user display and log full details."""
        # Log full exception details for debugging (not shown to user)
        logger.exception("Unhandled error in bot operation: %s", type(error).__name__)
        
        # Return generic, safe message for users
        return f"Oops, {self.bot_name} hit a snag. Please try again in a moment."


class ClementineBot:
    """Main bot orchestrator following single responsibility principle."""
    
    def __init__(self, tangerine_client: TangerineClient, slack_client: SlackClient,
                 bot_name: str, assistant_list: List[str], default_prompt: str):
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
    
    def _post_loading_message(self, event: SlackEvent) -> Optional[str]:
        """Post loading message."""
        return self.slack_client.post_loading_message(event.channel, event.thread_ts)
    
    def _get_tangerine_response(self, event: SlackEvent) -> TangerineResponse:
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