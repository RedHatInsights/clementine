import pytest
from clementine.formatters import MessageFormatter, BlockKitFormatter
from clementine.tangerine import TangerineResponse


class TestMessageFormatter:
    """Test MessageFormatter functionality."""
    
    def test_format_with_sources_no_metadata(self):
        """Test formatting when no metadata is provided."""
        formatter = MessageFormatter()
        response = TangerineResponse(text="Hello", metadata=[], interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        assert result == "Hello"
    
    def test_format_with_sources_valid_metadata(self):
        """Test formatting with valid source metadata."""
        formatter = MessageFormatter()
        metadata = [
            {"metadata": {"citation_url": "http://example.com", "title": "Example"}},
            {"metadata": {"citation_url": "http://test.com", "title": "Test"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
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
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
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
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        # Should only include first 3 sources
        expected = "Hello\n\n*Sources:*\n<http://example0.com|Example 0>\n<http://example1.com|Example 1>\n<http://example2.com|Example 2>"
        assert result == expected
    
    def test_format_with_doc_base_url_and_relative_paths(self):
        """Test formatting with DOC_BASE_URL and relative citation paths."""
        formatter = MessageFormatter(doc_base_url="https://docs.example.com")
        metadata = [
            {"metadata": {"citation_url": "/docs/guide/getting-started", "title": "Getting Started"}},
            {"metadata": {"citation_url": "/docs/api/reference", "title": "API Reference"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        expected = "Hello\n\n*Sources:*\n<https://docs.example.com/docs/guide/getting-started|Getting Started>\n<https://docs.example.com/docs/api/reference|API Reference>"
        assert result == expected
    
    def test_format_with_doc_base_url_and_absolute_urls(self):
        """Test formatting with DOC_BASE_URL but absolute URLs in citation_url."""
        formatter = MessageFormatter(doc_base_url="https://docs.example.com")
        metadata = [
            {"metadata": {"citation_url": "https://external.com/guide", "title": "External Guide"}},
            {"metadata": {"citation_url": "http://another.com/api", "title": "Another API"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        # Should use original URLs since they're already absolute
        expected = "Hello\n\n*Sources:*\n<https://external.com/guide|External Guide>\n<http://another.com/api|Another API>"
        assert result == expected
    
    def test_format_with_doc_base_url_mixed_paths(self):
        """Test formatting with mix of relative and absolute paths."""
        formatter = MessageFormatter(doc_base_url="https://docs.example.com")
        metadata = [
            {"metadata": {"citation_url": "/docs/internal", "title": "Internal Doc"}},
            {"metadata": {"citation_url": "https://external.com/doc", "title": "External Doc"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        expected = "Hello\n\n*Sources:*\n<https://docs.example.com/docs/internal|Internal Doc>\n<https://external.com/doc|External Doc>"
        assert result == expected
    
    def test_format_with_doc_base_url_trailing_slash(self):
        """Test that trailing slashes in DOC_BASE_URL are handled correctly."""
        formatter = MessageFormatter(doc_base_url="https://docs.example.com/")
        metadata = [
            {"metadata": {"citation_url": "/docs/guide", "title": "Guide"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        # Should not double slash
        expected = "Hello\n\n*Sources:*\n<https://docs.example.com/docs/guide|Guide>"
        assert result == expected


class TestBlockKitFormatter:
    """Test BlockKitFormatter functionality."""
    
    def test_format_with_ai_disclosure_enabled(self):
        """Test Block Kit formatting with AI disclosure enabled."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=True, feedback_enabled=False)
        response = TangerineResponse(text="Hello world", metadata=[], interaction_id="test-123")
        
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
        formatter = BlockKitFormatter(ai_disclosure_enabled=False, feedback_enabled=False)
        response = TangerineResponse(text="Hello world", metadata=[], interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        assert isinstance(result, dict)
        assert len(result["blocks"]) == 1  # Only content block
        
        content_block = result["blocks"][0]
        assert content_block["type"] == "section"
        assert content_block["text"]["text"] == "Hello world"
    
    def test_format_with_sources_and_ai_disclosure(self):
        """Test Block Kit formatting with sources and AI disclosure."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=True, feedback_enabled=False)
        metadata = [
            {"metadata": {"citation_url": "http://example.com", "title": "Example"}},
            {"metadata": {"citation_url": "http://test.com", "title": "Test"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
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
        formatter = BlockKitFormatter(ai_disclosure_enabled=True, feedback_enabled=False)
        metadata = [
            {"metadata": {"citation_url": "http://example.com", "title": "Example"}},
            {"invalid": "structure"},  # Malformed - should be skipped
            {"metadata": {"citation_url": "http://test.com"}}  # Missing title - gets default "Source"
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
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
        formatter = BlockKitFormatter(ai_disclosure_enabled=True, feedback_enabled=False)
        metadata = [
            {"invalid": "structure"},
            {"metadata": {}}  # No URL or title
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
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
            ai_disclosure_text=custom_text,
            feedback_enabled=False
        )
        response = TangerineResponse(text="Hello", metadata=[], interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        ai_block = result["blocks"][1]
        assert custom_text in ai_block["elements"][0]["text"]
    
    def test_fallback_text_includes_source_titles(self):
        """Test that fallback text includes source information for accessibility."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=True, feedback_enabled=False)
        metadata = [
            {"metadata": {"citation_url": "http://example.com", "title": "Example Doc"}},
            {"metadata": {"citation_url": "http://test.com", "title": "Test Page"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        fallback_text = result["text"]
        assert fallback_text == "Hello (Sources: Example Doc, Test Page)"
    
    def test_sources_limited_to_three(self):
        """Test that sources are limited to three in Block Kit format."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=True, feedback_enabled=False)
        metadata = [
            {"metadata": {"citation_url": f"http://example{i}.com", "title": f"Example {i}"}}
            for i in range(5)
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
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
    
    def test_format_with_doc_base_url_and_relative_paths(self):
        """Test BlockKit formatting with DOC_BASE_URL and relative citation paths."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=False, feedback_enabled=False, 
                                     doc_base_url="https://docs.example.com")
        metadata = [
            {"metadata": {"citation_url": "/docs/guide/getting-started", "title": "Getting Started"}},
            {"metadata": {"citation_url": "/docs/api/reference", "title": "API Reference"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        # Check sources block
        sources_block = result["blocks"][1]
        sources_text = sources_block["elements"][0]["text"]
        assert "<https://docs.example.com/docs/guide/getting-started|Getting Started>" in sources_text
        assert "<https://docs.example.com/docs/api/reference|API Reference>" in sources_text
    
    def test_format_with_doc_base_url_and_absolute_urls(self):
        """Test BlockKit formatting with DOC_BASE_URL but absolute URLs in citation_url."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=False, feedback_enabled=False,
                                     doc_base_url="https://docs.example.com")
        metadata = [
            {"metadata": {"citation_url": "https://external.com/guide", "title": "External Guide"}},
            {"metadata": {"citation_url": "http://another.com/api", "title": "Another API"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        # Should use original URLs since they're already absolute
        sources_block = result["blocks"][1]
        sources_text = sources_block["elements"][0]["text"]
        assert "<https://external.com/guide|External Guide>" in sources_text
        assert "<http://another.com/api|Another API>" in sources_text
    
    def test_format_with_doc_base_url_mixed_paths(self):
        """Test BlockKit formatting with mix of relative and absolute paths."""
        formatter = BlockKitFormatter(ai_disclosure_enabled=False, feedback_enabled=False,
                                     doc_base_url="https://docs.example.com")
        metadata = [
            {"metadata": {"citation_url": "/docs/internal", "title": "Internal Doc"}},
            {"metadata": {"citation_url": "https://external.com/doc", "title": "External Doc"}}
        ]
        response = TangerineResponse(text="Hello", metadata=metadata, interaction_id="test-123")
        
        result = formatter.format_with_sources(response)
        
        sources_block = result["blocks"][1]
        sources_text = sources_block["elements"][0]["text"]
        assert "<https://docs.example.com/docs/internal|Internal Doc>" in sources_text
        assert "<https://external.com/doc|External Doc>" in sources_text