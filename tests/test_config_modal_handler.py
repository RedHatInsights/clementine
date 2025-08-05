"""Tests for configuration modal handler."""

import pytest
import json
from unittest.mock import Mock, patch

from clementine.config_modal_handler import ConfigModalHandler


class TestConfigModalHandler:
    """Test ConfigModalHandler Slack modal interactions."""
    
    def test_create_config_modal_success(self):
        """Test successful modal creation."""
        mock_service = Mock()
        mock_service.get_current_config_for_display.return_value = {
            "room_id": "test_room",
            "assistant_list": ["assistant1"],
            "system_prompt": "Test prompt",
            "has_custom_config": True,
            "assistant_list_json": '["assistant1"]'
        }
        
        mock_slack_client = Mock()
        mock_slack_client.client.views_open.return_value = {"ok": True}
        
        mock_tangerine_client = Mock()
        mock_tangerine_client.fetch_assistants.return_value = [
            {"id": 1, "name": "assistant1", "description": "Test Assistant 1"},
            {"id": 2, "name": "assistant2", "description": "Test Assistant 2"}
        ]
        
        handler = ConfigModalHandler(mock_service, mock_slack_client, mock_tangerine_client)
        
        result = handler.create_config_modal("test_room", "trigger123")
        
        assert result is True
        mock_service.get_current_config_for_display.assert_called_once_with("test_room")
        mock_slack_client.client.views_open.assert_called_once()
        
        # Verify modal structure
        call_args = mock_slack_client.client.views_open.call_args
        view = call_args[1]["view"]
        assert view["type"] == "modal"
        assert view["callback_id"] == "room_config_modal"
        assert "room_id" in json.loads(view["private_metadata"])
    
    def test_create_config_modal_failure(self):
        """Test modal creation failure."""
        mock_service = Mock()
        mock_service.get_current_config_for_display.return_value = {
            "room_id": "test_room",
            "assistant_list": ["assistant1"],
            "system_prompt": "Test prompt",
            "has_custom_config": False,
            "assistant_list_json": '["assistant1"]'
        }
        
        mock_slack_client = Mock()
        mock_slack_client.client.views_open.return_value = {"ok": False, "error": "permission_denied"}
        
        mock_tangerine_client = Mock()
        mock_tangerine_client.fetch_assistants.return_value = []
        
        handler = ConfigModalHandler(mock_service, mock_slack_client, mock_tangerine_client)
        
        result = handler.create_config_modal("test_room", "trigger123")
        
        assert result is False
    
    def test_create_config_modal_exception(self):
        """Test modal creation with exception."""
        mock_service = Mock()
        mock_service.get_current_config_for_display.side_effect = Exception("Service error")
        
        mock_slack_client = Mock()
        
        mock_tangerine_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client, mock_tangerine_client)
        
        result = handler.create_config_modal("test_room", "trigger123")
        
        assert result is False
    

    
    def test_handle_modal_submission_success(self):
        """Test successful modal submission handling."""
        mock_service = Mock()
        mock_service.save_room_config.return_value = True
        mock_slack_client = Mock()
        mock_tangerine_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client, mock_tangerine_client)
        
        payload = {
            "view": {
                "private_metadata": json.dumps({"room_id": "test_room"}),
                "state": {
                    "values": {
                        "assistant_list_block": {
                            "assistant_list_select": {
                                "selected_options": [
                                    {"value": "assistant1", "text": {"type": "plain_text", "text": "assistant1"}},
                                    {"value": "assistant2", "text": {"type": "plain_text", "text": "assistant2"}}
                                ]
                            }
                        },
                        "system_prompt_block": {
                            "system_prompt_input": {
                                "value": "Custom prompt"
                            }
                        }
                    }
                }
            }
        }
        
        result = handler.handle_modal_submission(payload)
        
        assert result["response_action"] == "clear"
    
    def test_handle_modal_submission_with_errors(self):
        """Test modal submission handling with validation errors."""
        mock_service = Mock()
        mock_slack_client = Mock()
        mock_tangerine_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client, mock_tangerine_client)
        
        payload = {
            "view": {
                "private_metadata": json.dumps({"room_id": "test_room"}),
                "state": {
                    "values": {
                        "assistant_list_block": {
                            "assistant_list_select": {
                                "selected_options": []  # Empty selection should cause error
                            }
                        }
                    }
                }
            }
        }
        
        result = handler.handle_modal_submission(payload)
        
        assert result["response_action"] == "errors"
        assert "errors" in result
    
    def test_handle_modal_submission_exception(self):
        """Test modal submission handling with exception."""
        mock_service = Mock()
        mock_slack_client = Mock()
        mock_tangerine_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client, mock_tangerine_client)
        
        # Invalid payload (missing required fields)
        payload = {
            "view": {
                "private_metadata": "invalid json"
            }
        }
        
        result = handler.handle_modal_submission(payload)
        
        assert result["response_action"] == "errors"
        assert "general" in result["errors"]