import pytest
from clementine.error_handling import ErrorHandler


class TestErrorHandler:
    """Test ErrorHandler functionality."""
    
    def test_format_error_message(self):
        """Test error message formatting."""
        error_handler = ErrorHandler("TestBot")
        test_error = Exception("Test error")
        
        result = error_handler.format_error_message(test_error)
        
        assert result == "Oops, TestBot hit a snag. Please try again in a moment."
    
    def test_format_error_message_different_bot_name(self):
        """Test error message with different bot name."""
        error_handler = ErrorHandler("DifferentBot")
        test_error = ValueError("Test error")
        
        result = error_handler.format_error_message(test_error)
        
        assert result == "Oops, DifferentBot hit a snag. Please try again in a moment." 