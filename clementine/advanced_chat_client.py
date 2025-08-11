"""Advanced chat client for 'bring your own chunks' API."""

import requests
import uuid
import logging
import json
from typing import Dict, List
from dataclasses import dataclass

from .tangerine import TangerineResponse

logger = logging.getLogger(__name__)


@dataclass
class ChunksRequest:
    """Value object for advanced chat requests with custom chunks."""
    query: str
    chunks: List[str]
    session_id: str
    client_name: str
    assistant_name: str = "clowder"
    system_prompt: str = None
    user_prompt: str = None
    
    def to_payload(self) -> Dict:
        """Convert to API payload format."""
        payload = {
            "assistants": [self.assistant_name],
            "query": self.query,
            "sessionId": self.session_id,
            "interactionId": str(uuid.uuid4()),
            "client": self.client_name,
            "stream": False,
            "chunks": self.chunks,
            "disable_agentic": True
        }
        
        # Add system prompt if provided
        if self.system_prompt:
            payload["system_prompt"] = self.system_prompt
            
        # Add user prompt if provided
        if self.user_prompt:
            payload["userPrompt"] = self.user_prompt
            
        return payload


class AdvancedChatClient:
    """Handles communication with the advanced chat API using custom chunks.
    
    This client is specifically designed for the 'bring your own chunks' workflow
    where we provide our own context instead of using traditional RAG retrieval.
    It follows the single responsibility principle by only handling API communication.
    """
    
    def __init__(self, api_url: str, api_token: str, timeout: int = 500):
        if not api_url or not api_token:
            raise ValueError("Both api_url and api_token are required")
        
        self.api_url = api_url.rstrip('/')  # Remove trailing slash
        self.api_token = api_token
        self.timeout = timeout
        self.chat_endpoint = f"{self.api_url}/api/assistants/chat"
    
    def chat_with_chunks(self, chunks_request: ChunksRequest) -> TangerineResponse:
        """Send chat request with custom chunks and return structured response."""
        logger.info("API DEBUG: Sending chunks-based chat request for session %s", chunks_request.session_id)
        logger.info("API DEBUG: Using %d chunks for context", len(chunks_request.chunks))
        
        payload = chunks_request.to_payload()
        
        # Log payload without chunks for debugging (chunks could be large)
        debug_payload = {k: v for k, v in payload.items() if k != "chunks"}
        debug_payload["chunks"] = f"[{len(payload['chunks'])} chunks]"
        logger.info("API DEBUG: Full payload (without chunks): %s", debug_payload)
        logger.info("API DEBUG: Using assistant: %s", chunks_request.assistant_name)
        
        response_data = self._make_request(payload)
        logger.info("API DEBUG: Received response from advanced chat API")
        
        # Log the response text to see if it matches what we expect
        response_text = response_data.get("text_content", "")
        logger.info("API DEBUG: Response text: %s", response_text[:300] + "..." if len(response_text) > 300 else response_text)
        
        # Extract interaction_id from the payload we sent
        interaction_id = payload["interactionId"]
        return TangerineResponse.from_dict(response_data, interaction_id)
    
    def _make_request(self, payload: Dict) -> Dict:
        """Make HTTP request to advanced chat API with comprehensive error handling."""
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
            logger.error("Advanced chat API request timed out after %d seconds", self.timeout)
            raise
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to advanced chat API at %s", self.chat_endpoint)
            raise
        except requests.exceptions.HTTPError as e:
            status_code = getattr(e.response, 'status_code', 'unknown') if e.response else 'unknown'
            logger.error("Advanced chat API returned HTTP error %s: %s", status_code, e)
            raise
        except json.JSONDecodeError:
            logger.error("Advanced chat API returned invalid JSON response")
            raise
        except Exception as e:
            logger.error("Unexpected error calling advanced chat API: %s", e)
            raise