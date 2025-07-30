"""Feedback client for sending user feedback to Tangerine API."""

import requests
import logging
from typing import Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FeedbackRequest:
    """Value object representing a feedback request."""
    like: bool
    dislike: bool
    feedback: str
    interaction_id: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API request."""
        return {
            "like": self.like,
            "dislike": self.dislike, 
            "feedback": self.feedback,
            "interactionId": self.interaction_id
        }


class FeedbackClient:
    """Handles sending user feedback to the Tangerine API."""
    
    def __init__(self, api_url: str, api_token: str, timeout: int = 30):
        if not api_url or not api_token:
            raise ValueError("Both api_url and api_token are required")
        
        self.api_url = api_url.rstrip('/')  # Remove trailing slash
        self.api_token = api_token
        self.timeout = timeout
        self.feedback_endpoint = f"{self.api_url}/api/feedback"
    
    def send_feedback(self, feedback_request: FeedbackRequest) -> bool:
        """Send feedback to Tangerine API and return success status."""
        logger.debug("Sending feedback for interaction %s", feedback_request.interaction_id)
        
        try:
            response = requests.post(
                self.feedback_endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                },
                json=feedback_request.to_dict(),
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info("Successfully sent feedback for interaction %s", feedback_request.interaction_id)
            return True
            
        except requests.exceptions.Timeout:
            logger.error("Feedback API request timed out after %d seconds", self.timeout)
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Feedback API at %s", self.feedback_endpoint)
            return False
        except requests.exceptions.HTTPError as e:
            status_code = getattr(e.response, 'status_code', 'unknown') if e.response else 'unknown'
            logger.error("Feedback API returned HTTP error %s: %s", status_code, e)
            return False
        except Exception as e:
            logger.error("Unexpected error calling Feedback API: %s", e)
            return False 