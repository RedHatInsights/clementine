"""Tangerine API client and response handling."""

import requests
import uuid
import logging
from typing import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Namespace UUID for generating deterministic session IDs
CLEMENTINE_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


def generate_session_id(channel: str, thread_ts: str) -> str:
    """Generate deterministic UUID session ID from channel and thread timestamp.
    
    Creates consistent session IDs for the same Slack thread across bot restarts.
    Uses UUID5 with a fixed namespace for deterministic generation.
    """
    session_key = f"{channel}_{thread_ts}"
    return str(uuid.uuid5(CLEMENTINE_NAMESPACE, session_key))


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