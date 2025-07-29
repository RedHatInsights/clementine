import requests
import uuid
from typing import Dict, List, Optional, Any
from slack_sdk.errors import SlackApiError
from slack_sdk.web.client import WebClient
from dataclasses import dataclass


@dataclass
class SlackEvent:
    """Value object representing a Slack mention event."""
    text: str
    user_id: str
    channel: str
    thread_ts: str
    
    @classmethod
    def from_dict(cls, event: Dict) -> 'SlackEvent':
        return cls(
            text=event["text"],
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
        """Build formatted source links."""
        return "\n".join(
            f"<{source['metadata']['citation_url']}|{source['metadata']['title']}>"
            for source in sources
            if source.get("metadata", {}).get("citation_url")
        )


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
        except SlackApiError:
            return None
    
    def update_message(self, channel: str, ts: str, text: str) -> bool:
        """Update message and return success status."""
        try:
            self.client.chat_update(channel=channel, ts=ts, text=text)
            return True
        except SlackApiError:
            return False


class TangerineClient:
    """Handles communication with the Tangerine API."""
    
    def __init__(self, api_url: str, api_token: str, timeout: int = 500):
        self.api_url = api_url
        self.api_token = api_token
        self.timeout = timeout
        self.chat_endpoint = f"{api_url}/api/assistants/chat"
    
    def chat(self, assistants: List[str], query: str, session_id: str, 
             client_name: str, prompt: str) -> TangerineResponse:
        """Send chat request and return structured response."""
        payload = self._build_payload(assistants, query, session_id, client_name, prompt)
        response_data = self._make_request(payload)
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
        """Make HTTP request to Tangerine API."""
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


class ErrorHandler:
    """Handles error scenarios."""
    
    def __init__(self, bot_name: str):
        self.bot_name = bot_name
    
    def format_error_message(self, error: Exception) -> str:
        """Format error for user display."""
        return f"Oops, {self.bot_name} hit a snag: `{error}`"


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
        event = SlackEvent.from_dict(event_dict)
        loading_ts = self._post_loading_message(event)
        
        if not loading_ts:
            return
            
        try:
            response = self._get_tangerine_response(event)
            formatted_text = self.formatter.format_with_sources(response)
            self._update_message(event, loading_ts, formatted_text)
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
        self.slack_client.update_message(event.channel, loading_ts, text)
    
    def _handle_error(self, event: SlackEvent, loading_ts: str, error: Exception) -> None:
        """Handle and display error."""
        error_message = self.error_handler.format_error_message(error)
        print(error_message)
        self.slack_client.update_message(event.channel, loading_ts, error_message) 