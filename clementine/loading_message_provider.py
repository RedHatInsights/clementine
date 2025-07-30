"""Loading message provider for personality-rich bot responses."""

import random
from typing import List

from .loading_messages import LOADING_MESSAGES


class LoadingMessageProvider:
    """Provides random loading messages with personality.
    
    Follows single responsibility principle - only responsible for providing
    loading messages. Uses dependency injection for extensibility.
    """
    
    def __init__(self, messages: List[str] = None):
        """Initialize with message collection.
        
        Args:
            messages: List of loading messages. Defaults to standard collection.
        """
        if messages is None:
            self._messages = LOADING_MESSAGES.copy()
        else:
            self._messages = messages.copy()
        
        if not self._messages:
            raise ValueError("Loading messages cannot be empty")
    
    def get_random_message(self) -> str:
        """Get a random loading message.
        
        Returns:
            A randomly selected loading message string.
        """
        return random.choice(self._messages)
    
    def get_message_count(self) -> int:
        """Get the total number of available messages.
        
        Returns:
            Number of loading messages available.
        """
        return len(self._messages) 