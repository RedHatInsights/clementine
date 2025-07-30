import pytest
from unittest.mock import Mock
import requests

from clementine.tangerine import TangerineResponse, TangerineClient


class TestTangerineResponse:
    """Test TangerineResponse value object."""
    
    def test_from_dict_with_content_and_metadata(self):
        """Test creating response with content and metadata."""
        data = {
            "text_content": "Here's your answer",
            "search_metadata": [
                {"metadata": {"citation_url": "http://example.com", "title": "Example"}},
                {"metadata": {"citation_url": "http://test.com", "title": "Test"}}
            ]
        }
        
        response = TangerineResponse.from_dict(data)
        
        assert response.text == "Here's your answer"
        assert len(response.metadata) == 2
        assert response.metadata[0]["metadata"]["title"] == "Example"
    
    def test_from_dict_missing_content(self):
        """Test default message when content is missing."""
        data = {"search_metadata": []}
        
        response = TangerineResponse.from_dict(data)
        
        assert response.text == "(No response from assistant)"
        assert response.metadata == []
    
    def test_from_dict_strips_whitespace(self):
        """Test that text content is stripped."""
        data = {"text_content": "  Answer  "}
        
        response = TangerineResponse.from_dict(data)
        
        assert response.text == "Answer"


class MockHTTPAdapter:
    """Mock HTTP adapter for testing TangerineClient."""
    
    def __init__(self):
        self.post_responses = []
        self.call_count = 0
    
    def add_response(self, status_code, json_data):
        """Add a mock response."""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data
        mock_response.raise_for_status = Mock()
        if status_code >= 400:
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        self.post_responses.append(mock_response)
    
    def post(self, url, **kwargs):
        """Mock post method."""
        if self.call_count >= len(self.post_responses):
            raise Exception("No more mock responses available")
        response = self.post_responses[self.call_count]
        self.call_count += 1
        return response


class TestTangerineClient:
    """Test TangerineClient with dependency injection."""
    
    def test_chat_success(self):
        """Test successful chat request."""
        mock_adapter = MockHTTPAdapter()
        mock_adapter.add_response(200, {
            "text_content": "Hello response",
            "search_metadata": [{"metadata": {"citation_url": "http://example.com", "title": "Example"}}]
        })
        
        # Use dependency injection to replace requests
        client = TangerineClient("http://api.example.com", "token123")
        client._http_adapter = mock_adapter
        
        # Inject the adapter into the _make_request method
        original_make_request = client._make_request
        def mock_make_request(payload):
            return mock_adapter.post("fake_url", json=payload).json()
        client._make_request = mock_make_request
        
        result = client.chat(
            assistants=["assistant1"],
            query="Hello",
            session_id="session123",
            client_name="TestBot",
            prompt="You are helpful"
        )
        
        assert isinstance(result, TangerineResponse)
        assert result.text == "Hello response"
        assert len(result.metadata) == 1
    
    def test_initialization_validation(self):
        """Test client initialization validation."""
        with pytest.raises(ValueError, match="Both api_url and api_token are required"):
            TangerineClient("", "token")
        
        with pytest.raises(ValueError, match="Both api_url and api_token are required"):
            TangerineClient("http://example.com", "")
    
    def test_url_normalization(self):
        """Test that trailing slashes are removed from URLs."""
        client = TangerineClient("http://example.com/", "token")
        
        assert client.api_url == "http://example.com"
        assert client.chat_endpoint == "http://example.com/api/assistants/chat" 