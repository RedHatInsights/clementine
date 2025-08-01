"""Message formatting utilities."""

import logging
from typing import Dict, List, Optional, Protocol, Union
from .tangerine import TangerineResponse

logger = logging.getLogger(__name__)


class ResponseFormatter(Protocol):
    """Protocol for response formatters."""
    
    def format_with_sources(self, response: TangerineResponse) -> Union[str, Dict]:
        """Format response with source citations."""
        ...


class MessageFormatter:
    """Handles formatting of responses as plain text."""
    
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


class BlockKitFormatter:
    """Handles formatting of responses using Slack Block Kit with AI disclosure."""
    
    def __init__(self, ai_disclosure_enabled: bool = True, 
                 ai_disclosure_text: str = "This response was generated by AI. Please verify important information.",
                 feedback_enabled: bool = True):
        self.ai_disclosure_enabled = ai_disclosure_enabled
        self.ai_disclosure_text = ai_disclosure_text
        self.feedback_enabled = feedback_enabled
    
    def format_with_sources(self, response: TangerineResponse) -> Dict:
        """Format response as Block Kit blocks with source citations and AI disclosure."""
        blocks = []
        
        # Main content block
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": response.text
            }
        })
        
        # Sources block if available
        if response.metadata:
            sources_block = self._build_sources_block(response.metadata[:3])
            if sources_block:
                blocks.append(sources_block)
        
        # AI disclosure context block
        if self.ai_disclosure_enabled:
            blocks.append(self._build_ai_disclosure_block())
        
        # Feedback buttons if enabled
        if self.feedback_enabled:
            feedback_block = self._build_feedback_block(response.interaction_id)
            blocks.append(feedback_block)
        
        return {
            "blocks": blocks,
            # Fallback text for notifications and accessibility
            "text": self._build_fallback_text(response)
        }
    
    def _build_sources_block(self, sources: List[Dict]) -> Optional[Dict]:
        """Build Block Kit context block for source citations."""
        links = []
        for source in sources:
            try:
                metadata = source.get("metadata", {})
                url = metadata.get("citation_url")
                title = metadata.get("title", "Source")
                if url and title:
                    links.append(f"<{url}|{title}>")
            except (TypeError, AttributeError):
                logger.debug("Skipping malformed source metadata: %s", source)
                continue
        
        if not links:
            return None
            
        return {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*Sources:* {' • '.join(links)}"
                }
            ]
        }
    
    def _build_ai_disclosure_block(self) -> Dict:
        """Build Block Kit context block for AI disclosure."""
        return {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🤖 {self.ai_disclosure_text}"
                }
            ]
        }
    
    def _build_feedback_block(self, interaction_id: str) -> Dict:
        """Build Block Kit actions block for feedback buttons."""
        return {
            "type": "actions",
            "block_id": "feedback_actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "👍"
                    },
                    "style": "primary",
                    "value": f"feedback_like_{interaction_id}",
                    "action_id": "feedback_like"
                },
                {
                    "type": "button", 
                    "text": {
                        "type": "plain_text",
                        "text": "👎"
                    },
                    "value": f"feedback_dislike_{interaction_id}",
                    "action_id": "feedback_dislike"
                }
            ]
        }
    
    def _build_fallback_text(self, response: TangerineResponse) -> str:
        """Build fallback text for notifications and accessibility."""
        text = response.text
        
        if response.metadata:
            sources = response.metadata[:3]
            links = []
            for source in sources:
                try:
                    metadata = source.get("metadata", {})
                    title = metadata.get("title", "Source")
                    if title:
                        links.append(title)
                except (TypeError, AttributeError):
                    continue
            
            if links:
                text += f" (Sources: {', '.join(links)})"
        
        return text 