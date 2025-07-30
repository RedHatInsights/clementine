import pytest
from clementine.formatters import MessageFormatter, BlockKitFormatter
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
        
        # Should only include first 3 sources
        expected = "Hello\n\n*Sources:*\n<http://example0.com|Example 0>\n<http://example1.com|Example 1>\n<http://example2.com|Example 2>"
        assert result == expected


class TestBlockKitFormatter:
    """Test BlockKitFormatter functionality."""
    
    def test_format_with_ai_disclosure_enabled(self):
        """Test Block Kit formatting with AI disclosure enabled."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=True)
        response = TangerineResponse(text="Hello world", metadata=[])
        
        result = formatter.format_with_sources(response)
        
        assert isinstance(result, dict)
        assert "blocks" in result
        assert "text" in result
        assert len(result["blocks"]) == 2  # Content + AI disclosure
        
        # Check main content block
        content_block = result["blocks"][0]
        assert content_block["type"] == "section"
        assert content_block["text"]["text"] == "Hello world"
        
        # Check AI disclosure block
        ai_block = result["blocks"][1]
        assert ai_block["type"] == "context"
        assert "🤖" in ai_block["elements"][0]["text"]
        
        # Check fallback text
        assert result["text"] == "Hello world"
    
    def test_format_with_ai_disclosure_disabled(self):
        """Test Block Kit formatting with AI disclosure disabled."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=False)
        response = TangerineResponse(text="Hello world", metadata=[])
        
        result = formatter.format_with_sources(response)
        
        assert isinstance(result, dict)
        assert len(result["blocks"]) == 1  # Only content block
        
        content_block = result["blocks"][0]
        assert content_block["type"] == "section"
        assert content_block["text"]["text"] == "Hello world"
    
    def test_format_with_sources_and_ai_disclosure(self):
        """Test Block Kit formatting with sources and AI disclosure."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=True)
        metadata = [
            {"metadata": {"citation_url": "http://example.com", "title": "Example"}},
            {"metadata": {"citation_url": "http://test.com", "title": "Test"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata)
        
        result = formatter.format_with_sources(response)
        
        assert len(result["blocks"]) == 3  # Content + Sources + AI disclosure
        
        # Check content block
        assert result["blocks"][0]["type"] == "section"
        assert result["blocks"][0]["text"]["text"] == "Hello"
        
        # Check sources block
        sources_block = result["blocks"][1]
        assert sources_block["type"] == "context"
        sources_text = sources_block["elements"][0]["text"]
        assert "*Sources:*" in sources_text
        assert "<http://example.com|Example>" in sources_text
        assert "<http://test.com|Test>" in sources_text
        
        # Check AI disclosure block
        ai_block = result["blocks"][2]
        assert ai_block["type"] == "context"
        assert "🤖" in ai_block["elements"][0]["text"]
    
    def test_format_with_malformed_sources(self):
        """Test Block Kit formatting with malformed source metadata."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=True)
        metadata = [
            {"metadata": {"citation_url": "http://example.com", "title": "Example"}},
            {"invalid": "structure"},  # Malformed - should be skipped
            {"metadata": {"citation_url": "http://test.com"}}  # Missing title - gets default "Source"
        ]
        response = TangerineResponse(text="Hello", metadata=metadata)
        
        result = formatter.format_with_sources(response)
        
        # Should have content + sources + AI disclosure blocks
        assert len(result["blocks"]) == 3
        
        # Check that sources block has correct links
        sources_block = result["blocks"][1]
        sources_text = sources_block["elements"][0]["text"]
        assert "<http://example.com|Example>" in sources_text
        assert "<http://test.com|Source>" in sources_text
    
    def test_format_with_no_valid_sources(self):
        """Test Block Kit formatting when no sources are valid."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=True)
        metadata = [
            {"invalid": "structure"},
            {"metadata": {}}  # No URL or title
        ]
        response = TangerineResponse(text="Hello", metadata=metadata)
        
        result = formatter.format_with_sources(response)
        
        # Should only have content + AI disclosure (no sources block)
        assert len(result["blocks"]) == 2
        assert result["blocks"][0]["type"] == "section"
        assert result["blocks"][1]["type"] == "context"
    
    def test_custom_ai_disclosure_text(self):
        """Test Block Kit formatting with custom AI disclosure text."""
        custom_text = "Custom AI warning message"
        formatter = BlockKitFormatter(
            ai_disclosure_enabled=True,
            ai_disclosure_text=custom_text
        )
        response = TangerineResponse(text="Hello", metadata=[])
        
        result = formatter.format_with_sources(response)
        
        ai_block = result["blocks"][1]
        assert custom_text in ai_block["elements"][0]["text"]
    
    def test_fallback_text_includes_source_titles(self):
        """Test that fallback text includes source information for accessibility."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=True)
        metadata = [
            {"metadata": {"citation_url": "http://example.com", "title": "Example Doc"}},
            {"metadata": {"citation_url": "http://test.com", "title": "Test Page"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata)
        
        result = formatter.format_with_sources(response)
        
        fallback_text = result["text"]
        assert fallback_text == "Hello (Sources: Example Doc, Test Page)"
    
    def test_sources_limited_to_three(self):
        """Test that sources are limited to three in Block Kit format."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=True)
        metadata = [
            {"metadata": {"citation_url": f"http://example{i}.com", "title": f"Example {i}"}}
            for i in range(5)
        ]
        response = TangerineResponse(text="Hello", metadata=metadata)
        
        result = formatter.format_with_sources(response)
        
        sources_block = result["blocks"][1]
        sources_text = sources_block["elements"][0]["text"]
        
        # Should contain first 3 sources
        assert "Example 0" in sources_text
        assert "Example 1" in sources_text
        assert "Example 2" in sources_text
        # Should not contain 4th and 5th sources
        assert "Example 3" not in sources_text
        assert "Example 4" not in sources_text 