"""Message formatting utilities."""

import logging
from typing import Dict, List
from .tangerine import TangerineResponse

logger = logging.getLogger(__name__)


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