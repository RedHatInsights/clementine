import pytest
from clementine.formatters import MessageFormatter
from clementine.tangerine import TangerineResponse


class TestMessageFormatter:
    """Test MessageFormatter functionality."""
    
    def test_format_with_sources_no_metadata(self):
        """Test formatting when no metadata is provided."""
        formatter = MessageFormatter()
        response = TangerineResponse(text="Hello", metadata=[])
        
        result = formatter.format_with_sources(response)
        
        assert result == "Hello"
    
    def test_format_with_sources_valid_metadata(self):
        """Test formatting with valid source metadata."""
        formatter = MessageFormatter()
        metadata = [
            {"metadata": {"citation_url": "http://example.com", "title": "Example"}},
            {"metadata": {"citation_url": "http://test.com", "title": "Test"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata)
        
        result = formatter.format_with_sources(response)
        
        expected = "Hello\n\n*Sources:*\n<http://example.com|Example>\n<http://test.com|Test>"
        assert result == expected
    
    def test_format_with_sources_malformed_metadata(self):
        """Test handling of malformed metadata entries."""
        formatter = MessageFormatter()
        metadata = [
            {"metadata": {"citation_url": "http://example.com", "title": "Example"}},
            {"invalid": "structure"},  # Malformed - should be skipped
            {"metadata": {"citation_url": "http://test.com"}}  # Missing title - gets default "Source"
        ]
        response = TangerineResponse(text="Hello", metadata=metadata)
        
        result = formatter.format_with_sources(response)
        
        expected = "Hello\n\n*Sources:*\n<http://example.com|Example>\n<http://test.com|Source>"
        assert result == expected
    
    def test_format_with_sources_limits_to_three(self):
        """Test that only first 3 sources are included."""
        formatter = MessageFormatter()
        metadata = [
            {"metadata": {"citation_url": f"http://example{i}.com", "title": f"Example {i}"}}
            for i in range(5)
        ]
        response = TangerineResponse(text="Hello", metadata=metadata)
        
        result = formatter.format_with_sources(response)
        
        # Should only have 3 sources
        assert result.count("<http://") == 3
        assert "Example 0" in result
        assert "Example 1" in result
        assert "Example 2" in result
        assert "Example 3" not in result 