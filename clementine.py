import requests
import uuid
from typing import Dict, List, Optional, Any
from slack_sdk.errors import SlackApiError


class TangerineClient:
    """Handles communication with the Tangerine API."""
    
    def __init__(self, api_url: str, api_token: str, timeout: int = 500):
        self.api_url = api_url
        self.api_token = api_token
        self.timeout = timeout
        self.chat_endpoint = f"{api_url}/api/assistants/chat"
    
    def chat(self, assistants: List[str], query: str, session_id: str, 
             client_name: str, prompt: str) -> Dict[str, Any]:
        """Send a chat request to Tangerine API."""
        payload = {
            "assistants": assistants,
            "query": query,
            "sessionId": session_id,
            "interactionId": str(uuid.uuid4()),
            "client": client_name,
            "stream": False,
            "prompt": prompt
        }
        
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


class SlackMessageHandler:
    """Handles Slack message operations."""
    
    def __init__(self, client):
        self.client = client
    
    def post_loading_message(self, channel: str, thread_ts: str) -> Optional[str]:
        """Post a loading message and return its timestamp."""
        try:
            loading = self.client.chat_postMessage(
                channel=channel,
                text=":hourglass_flowing_sand: Thinking...",
                thread_ts=thread_ts
            )
            return loading["ts"]
        except SlackApiError as e:
            print(f"⚠️ Failed to post loading message: {e}")
            return None
    
    def format_response_with_sources(self, text: str, metadata: List[Dict]) -> str:
        """Format the response text with source citations."""
        if not metadata:
            return text
            
        sources = metadata[:3]
        links = "\n".join(
            f"<{m['metadata']['citation_url']}|{m['metadata']['title']}>"
            for m in sources
            if m.get("metadata", {}).get("citation_url")
        )
        
        if links:
            text += "\n\n*Sources:*\n" + links
        
        return text
    
    def update_message(self, channel: str, ts: str, text: str) -> None:
        """Update an existing message."""
        try:
            self.client.chat_update(
                channel=channel,
                ts=ts,
                text=text
            )
        except SlackApiError as e:
            print(f"⚠️ Failed to update message: {e}")


class ClementineBot:
    """Main bot orchestrator that coordinates Slack events and Tangerine API calls."""
    
    def __init__(self, tangerine_client: TangerineClient, bot_name: str, 
                 assistant_list: List[str], default_prompt: str):
        self.tangerine_client = tangerine_client
        self.bot_name = bot_name
        self.assistant_list = assistant_list
        self.default_prompt = default_prompt
    
    def handle_mention(self, event: Dict, slack_client) -> None:
        """Handle a mention event from Slack."""
        message_handler = SlackMessageHandler(slack_client)
        
        user_msg = event["text"]
        session_id = event["user"]
        thread_ts = event.get("thread_ts", event["ts"])
        channel = event["channel"]
        
        # Post loading message
        loading_ts = message_handler.post_loading_message(channel, thread_ts)
        if not loading_ts:
            return
        
        try:
            # Get response from Tangerine
            response_data = self.tangerine_client.chat(
                assistants=self.assistant_list,
                query=user_msg,
                session_id=session_id,
                client_name=self.bot_name,
                prompt=self.default_prompt
            )
            
            # Format response
            text = response_data.get("text_content", "(No response from assistant)").strip()
            metadata = response_data.get("search_metadata", [])
            formatted_text = message_handler.format_response_with_sources(text, metadata)
            
            # Update message with response
            message_handler.update_message(channel, loading_ts, formatted_text)
            
        except Exception as e:
            error_msg = f"Oops, {self.bot_name} hit a snag: `{e}`"
            print(error_msg)
            message_handler.update_message(channel, loading_ts, error_msg) 