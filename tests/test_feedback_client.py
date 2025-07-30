"""Tests for feedback client functionality."""

import pytest
import requests
from unittest.mock import Mock, patch

from clementine.feedback_client import FeedbackClient, FeedbackRequest


class TestFeedbackRequest:
    """Test cases for FeedbackRequest value object."""
    
    def test_to_dict_like_feedback(self):
        """Test to_dict method for like feedback."""
        request = FeedbackRequest(
            like=True,
            dislike=False,
            feedback="",
            interaction_id="test-interaction-123"
        )
        
        expected = {
            "like": True,
            "dislike": False,
            "feedback": "",
            "interactionId": "test-interaction-123"
        }
        
        assert request.to_dict() == expected
    
    def test_to_dict_dislike_feedback(self):
        """Test to_dict method for dislike feedback."""
        request = FeedbackRequest(
            like=False,
            dislike=True,
            feedback="Could be better",
            interaction_id="test-interaction-456"
        )
        
        expected = {
            "like": False,
            "dislike": True,
            "feedback": "Could be better",
            "interactionId": "test-interaction-456"
        }
        
        assert request.to_dict() == expected


class TestFeedbackClient:
    """Test cases for FeedbackClient."""
    
    def test_init_valid_params(self):
        """Test successful initialization with valid parameters."""
        client = FeedbackClient("https://api.example.com", "token123")
        
        assert client.api_url == "https://api.example.com"
        assert client.api_token == "token123"
        assert client.timeout == 30
        assert client.feedback_endpoint == "https://api.example.com/api/feedback"
    
    def test_init_removes_trailing_slash(self):
        """Test that trailing slash is removed from API URL."""
        client = FeedbackClient("https://api.example.com/", "token123")
        
        assert client.api_url == "https://api.example.com"
        assert client.feedback_endpoint == "https://api.example.com/api/feedback"
    
    def test_init_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = FeedbackClient("https://api.example.com", "token123", timeout=60)
        
        assert client.timeout == 60
    
    def test_init_missing_api_url(self):
        """Test initialization fails with missing API URL."""
        with pytest.raises(ValueError, match="Both api_url and api_token are required"):
            FeedbackClient("", "token123")
    
    def test_init_missing_api_token(self):
        """Test initialization fails with missing API token."""
        with pytest.raises(ValueError, match="Both api_url and api_token are required"):
            FeedbackClient("https://api.example.com", "")
    
    @patch('clementine.feedback_client.requests.post')
    def test_send_feedback_success(self, mock_post):
        """Test successful feedback submission."""
        # Setup
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = FeedbackClient("https://api.example.com", "token123")
        request = FeedbackRequest(True, False, "", "interaction-123")
        
        # Execute
        result = client.send_feedback(request)
        
        # Verify
        assert result is True
        mock_post.assert_called_once_with(
            "https://api.example.com/api/feedback",
            headers={
                "Authorization": "Bearer token123",
                "Content-Type": "application/json"
            },
            json={
                "like": True,
                "dislike": False,
                "feedback": "",
                "interactionId": "interaction-123"
            },
            timeout=30
        )
    
    @patch('clementine.feedback_client.requests.post')
    def test_send_feedback_timeout(self, mock_post):
        """Test feedback submission with timeout error."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        client = FeedbackClient("https://api.example.com", "token123")
        request = FeedbackRequest(True, False, "", "interaction-123")
        
        result = client.send_feedback(request)
        
        assert result is False
    
    @patch('clementine.feedback_client.requests.post')
    def test_send_feedback_connection_error(self, mock_post):
        """Test feedback submission with connection error."""
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        client = FeedbackClient("https://api.example.com", "token123")
        request = FeedbackRequest(True, False, "", "interaction-123")
        
        result = client.send_feedback(request)
        
        assert result is False
    
    @patch('clementine.feedback_client.requests.post')
    def test_send_feedback_http_error(self, mock_post):
        """Test feedback submission with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 400
        
        # Create HTTPError with response attached
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response
        
        client = FeedbackClient("https://api.example.com", "token123")
        request = FeedbackRequest(True, False, "", "interaction-123")
        
        result = client.send_feedback(request)
        
        assert result is False
    

    
    @patch('clementine.feedback_client.requests.post')
    def test_send_feedback_unexpected_error(self, mock_post):
        """Test feedback submission with unexpected error."""
        mock_post.side_effect = Exception("Unexpected error")
        
        client = FeedbackClient("https://api.example.com", "token123")
        request = FeedbackRequest(True, False, "", "interaction-123")
        
        result = client.send_feedback(request)
        
        assert result is False 