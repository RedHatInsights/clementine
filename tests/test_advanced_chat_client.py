"""Tests for AdvancedChatClient."""

import pytest
import requests
import json
from unittest.mock import Mock, patch
from uuid import UUID

from clementine.advanced_chat_client import AdvancedChatClient, ChunksRequest
from clementine.tangerine import TangerineResponse


class TestChunksRequest:
    """Test ChunksRequest value object."""
    
    def test_to_payload(self):
        """Test converting request to API payload."""
        chunks_request = ChunksRequest(
            query="What are they talking about?",
            chunks=["User A: Hello", "User B: Hi there"],
            session_id="session-123",
            client_name="test-client",
            prompt="You are a helpful assistant.",
            user_prompt="Please analyze the context to answer the user's question."
        )
        
        payload = chunks_request.to_payload()
        
        assert payload["query"] == "What are they talking about?"
        assert payload["chunks"] == ["User A: Hello", "User B: Hi there"]
        assert payload["sessionId"] == "session-123"
        assert payload["client"] == "test-client"
        assert payload["prompt"] == "You are a helpful assistant."
        assert payload["userPrompt"] == "Please analyze the context to answer the user's question."
        assert payload["stream"] is False
        assert payload["disable_agentic"] is True
        assert payload["assistants"] == ["clowder"]  # Default assistant
        
        # Check that interactionId is a valid UUID
        assert UUID(payload["interactionId"])
    
    def test_to_payload_with_assistants(self):
        """Test converting request to API payload with custom assistants."""
        chunks_request = ChunksRequest(
            query="Test question",
            chunks=["chunk1"],
            session_id="session-123",
            client_name="test-client",
            prompt="You are a helpful assistant.",
            user_prompt="Please analyze the context to answer the user's question.",
            assistants=["custom_assistant"]
        )
        
        payload = chunks_request.to_payload()
        
        assert payload["assistants"] == ["custom_assistant"]
        assert payload["prompt"] == "You are a helpful assistant."
        assert payload["userPrompt"] == "Please analyze the context to answer the user's question."
        assert payload["disable_agentic"] is True
        # Verify model is not included when not set
        assert "model" not in payload
    
    def test_to_payload_with_model(self):
        """Test converting request to API payload with model override."""
        chunks_request = ChunksRequest(
            query="Test question",
            chunks=["chunk1"],
            session_id="session-123",
            client_name="test-client",
            prompt="You are a helpful assistant.",
            user_prompt="Please analyze the context to answer the user's question.",
            model="chatgpt-4o"
        )
        
        payload = chunks_request.to_payload()
        
        assert payload["model"] == "chatgpt-4o"
        assert payload["assistants"] == ["clowder"]  # Default assistant
        assert payload["prompt"] == "You are a helpful assistant."
        assert payload["userPrompt"] == "Please analyze the context to answer the user's question."
        assert payload["disable_agentic"] is True


class TestAdvancedChatClient:
    """Test AdvancedChatClient functionality."""
    
    @pytest.fixture
    def client(self):
        """Create AdvancedChatClient for testing."""
        return AdvancedChatClient(
            api_url="https://api.example.com",
            api_token="test-token",
            timeout=30
        )
    
    def test_init_validates_parameters(self):
        """Test initialization parameter validation."""
        # Valid initialization
        client = AdvancedChatClient("https://api.example.com", "token")
        assert client.api_url == "https://api.example.com"
        assert client.api_token == "token"
        assert client.timeout == 500  # default
        assert client.model_override is None  # default
        
        # Valid initialization with model override
        client_with_model = AdvancedChatClient("https://api.example.com", "token", model_override="chatgpt-4o")
        assert client_with_model.model_override == "chatgpt-4o"
        
        # Invalid parameters
        with pytest.raises(ValueError, match="Both api_url and api_token are required"):
            AdvancedChatClient("", "token")
        
        with pytest.raises(ValueError, match="Both api_url and api_token are required"):
            AdvancedChatClient("https://api.example.com", "")
    
    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is removed from API URL."""
        client = AdvancedChatClient("https://api.example.com/", "token")
        assert client.api_url == "https://api.example.com"
        assert client.chat_endpoint == "https://api.example.com/api/assistants/chat"
    
    @patch('clementine.advanced_chat_client.requests.post')
    def test_chat_with_chunks_success(self, mock_post, client):
        """Test successful chat request with chunks."""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "text_content": "Based on the conversation, they are discussing project updates.",
            "search_metadata": []
        }
        mock_post.return_value = mock_response
        
        chunks_request = ChunksRequest(
            query="What are they talking about?",
            chunks=["User A: Working on the new feature", "User B: Looks good"],
            session_id="session-123",
            client_name="test-client",
            prompt="You are a helpful assistant.",
            user_prompt="Please analyze the context to answer the user's question."
        )
        
        result = client.chat_with_chunks(chunks_request)
        
        # Verify result
        assert isinstance(result, TangerineResponse)
        assert result.text == "Based on the conversation, they are discussing project updates."
        assert result.metadata == []
        assert UUID(result.interaction_id)  # Should be valid UUID
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        assert call_args[0][0] == "https://api.example.com/api/assistants/chat"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-token"
        assert call_args[1]["headers"]["Content-Type"] == "application/json"
        assert call_args[1]["timeout"] == 30
        
        # Verify payload
        payload = call_args[1]["json"]
        assert payload["query"] == "What are they talking about?"
        assert payload["chunks"] == ["User A: Working on the new feature", "User B: Looks good"]
        assert payload["prompt"] == "You are a helpful assistant."
        assert payload["userPrompt"] == "Please analyze the context to answer the user's question."
        assert payload["sessionId"] == "session-123"
        assert payload["client"] == "test-client"
        assert payload["assistants"] == ["clowder"]  # Default assistant
        assert payload["stream"] is False
        assert UUID(payload["interactionId"])
    
    @patch('clementine.advanced_chat_client.requests.post')
    def test_chat_with_chunks_timeout_error(self, mock_post, client):
        """Test timeout error handling."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        chunks_request = ChunksRequest(
            query="Test question",
            chunks=["chunk1"],
            session_id="session-123",
            client_name="test-client",
            prompt="You are a helpful assistant.",
            user_prompt="Please analyze the context to answer the user's question."
        )
        
        with pytest.raises(requests.exceptions.Timeout):
            client.chat_with_chunks(chunks_request)
    
    @patch('clementine.advanced_chat_client.requests.post')
    def test_chat_with_chunks_connection_error(self, mock_post, client):
        """Test connection error handling."""
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        chunks_request = ChunksRequest(
            query="Test question",
            chunks=["chunk1"],
            session_id="session-123",
            client_name="test-client",
            prompt="You are a helpful assistant.",
            user_prompt="Please analyze the context to answer the user's question."
        )
        
        with pytest.raises(requests.exceptions.ConnectionError):
            client.chat_with_chunks(chunks_request)
    
    @patch('clementine.advanced_chat_client.requests.post')
    def test_chat_with_chunks_http_error(self, mock_post, client):
        """Test HTTP error handling."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        chunks_request = ChunksRequest(
            query="Test question",
            chunks=["chunk1"],
            session_id="session-123",
            client_name="test-client",
            prompt="You are a helpful assistant.",
            user_prompt="Please analyze the context to answer the user's question."
        )
        
        with pytest.raises(requests.exceptions.HTTPError):
            client.chat_with_chunks(chunks_request)
    
    @patch('clementine.advanced_chat_client.requests.post')
    def test_chat_with_chunks_json_decode_error(self, mock_post, client):
        """Test JSON decode error handling."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response
        
        chunks_request = ChunksRequest(
            query="Test question",
            chunks=["chunk1"],
            session_id="session-123",
            client_name="test-client",
            prompt="You are a helpful assistant.",
            user_prompt="Please analyze the context to answer the user's question."
        )
        
        with pytest.raises(json.JSONDecodeError):
            client.chat_with_chunks(chunks_request)