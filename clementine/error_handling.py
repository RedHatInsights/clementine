"""Error handling utilities."""

import logging

logger = logging.getLogger(__name__)


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