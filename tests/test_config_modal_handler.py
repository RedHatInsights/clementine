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
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
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
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        result = handler.create_config_modal("test_room", "trigger123")
        
        assert result is False
    
    def test_create_config_modal_exception(self):
        """Test modal creation with exception."""
        mock_service = Mock()
        mock_service.get_current_config_for_display.side_effect = Exception("Service error")
        
        mock_slack_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        result = handler.create_config_modal("test_room", "trigger123")
        
        assert result is False
    
    def test_build_modal_blocks_with_custom_config(self):
        """Test modal block construction with custom configuration."""
        mock_service = Mock()
        mock_slack_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        config = {
            "room_id": "test_room",
            "assistant_list": ["assistant1", "assistant2"],
            "system_prompt": "Custom prompt",
            "has_custom_config": True,
            "assistant_list_json": '["assistant1", "assistant2"]'
        }
        
        blocks = handler._build_modal_blocks(config)
        
        # Should have info, divider, assistant section, assistant input, prompt section, prompt input, divider, reset
        assert len(blocks) >= 7
        
        # Check for reset option (should be present for custom config)
        reset_blocks = [b for b in blocks if b.get("type") == "section" and 
                       b.get("accessory", {}).get("action_id") == "reset_to_defaults"]
        assert len(reset_blocks) == 1
        
        # Check assistant list input has correct initial value
        assistant_input_blocks = [b for b in blocks if b.get("block_id") == "assistant_list_block"]
        assert len(assistant_input_blocks) == 1
        assert assistant_input_blocks[0]["element"]["initial_value"] == "assistant1, assistant2"
    
    def test_build_modal_blocks_with_default_config(self):
        """Test modal block construction with default configuration."""
        mock_service = Mock()
        mock_slack_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        config = {
            "room_id": "test_room",
            "assistant_list": ["default_assistant"],
            "system_prompt": "Default prompt",
            "has_custom_config": False,
            "assistant_list_json": '["default_assistant"]'
        }
        
        blocks = handler._build_modal_blocks(config)
        
        # Should NOT have reset option for default config
        reset_blocks = [b for b in blocks if b.get("type") == "section" and 
                       b.get("accessory", {}).get("action_id") == "reset_to_defaults"]
        assert len(reset_blocks) == 0
    
    def test_extract_form_values(self):
        """Test extracting form values from modal state."""
        mock_service = Mock()
        mock_slack_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        state_values = {
            "assistant_list_block": {
                "assistant_list_input": {
                    "value": "assistant1, assistant2,  assistant3 "
                }
            },
            "system_prompt_block": {
                "system_prompt_input": {
                    "value": "Custom system prompt"
                }
            },
            "reset_to_defaults": {
                "reset_to_defaults": {
                    "selected_options": [{"value": "reset"}]
                }
            }
        }
        
        form_values = handler._extract_form_values(state_values)
        
        expected = {
            "assistant_list": ["assistant1", "assistant2", "assistant3"],
            "system_prompt": "Custom system prompt",
            "reset_to_defaults": True
        }
        assert form_values == expected
    
    def test_extract_form_values_empty(self):
        """Test extracting empty form values."""
        mock_service = Mock()
        mock_slack_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        state_values = {
            "assistant_list_block": {
                "assistant_list_input": {
                    "value": ""
                }
            },
            "system_prompt_block": {
                "system_prompt_input": {
                    "value": "  "
                }
            }
        }
        
        form_values = handler._extract_form_values(state_values)
        
        expected = {
            "reset_to_defaults": False
        }
        assert form_values == expected
    
    def test_validate_and_save_config_success(self):
        """Test successful config validation and save."""
        mock_service = Mock()
        mock_service.save_room_config.return_value = True
        mock_slack_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        form_values = {
            "assistant_list": ["assistant1", "assistant2"],
            "system_prompt": "Custom prompt",
            "reset_to_defaults": False
        }
        
        result = handler._validate_and_save_config("test_room", form_values)
        
        assert result["success"] is True
        assert result["errors"] == {}
        mock_service.save_room_config.assert_called_once_with(
            room_id="test_room",
            assistant_list=["assistant1", "assistant2"],
            system_prompt="Custom prompt"
        )
    
    def test_validate_and_save_config_reset(self):
        """Test config reset to defaults."""
        mock_service = Mock()
        mock_service.reset_to_defaults.return_value = True
        mock_slack_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        form_values = {
            "assistant_list": ["assistant1"],
            "system_prompt": "Custom prompt",
            "reset_to_defaults": True
        }
        
        result = handler._validate_and_save_config("test_room", form_values)
        
        assert result["success"] is True
        assert result["errors"] == {}
        mock_service.reset_to_defaults.assert_called_once_with("test_room")
        mock_service.save_room_config.assert_not_called()
    
    def test_validate_and_save_config_validation_errors(self):
        """Test config validation with errors."""
        mock_service = Mock()
        mock_slack_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        form_values = {
            "assistant_list": [],  # Empty list should cause error
            "system_prompt": "a" * 5001,  # Too long should cause error
            "reset_to_defaults": False
        }
        
        result = handler._validate_and_save_config("test_room", form_values)
        
        assert result["success"] is False
        assert "assistant_list_block" in result["errors"]
        assert "system_prompt_block" in result["errors"]
        mock_service.save_room_config.assert_not_called()
    
    def test_validate_and_save_config_too_many_assistants(self):
        """Test validation with too many assistants."""
        mock_service = Mock()
        mock_slack_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        form_values = {
            "assistant_list": [f"assistant{i}" for i in range(15)],  # Too many
            "system_prompt": "Valid prompt",
            "reset_to_defaults": False
        }
        
        result = handler._validate_and_save_config("test_room", form_values)
        
        assert result["success"] is False
        assert "assistant_list_block" in result["errors"]
        assert "Too many assistants" in result["errors"]["assistant_list_block"]
    
    def test_validate_and_save_config_no_values(self):
        """Test validation with no values provided."""
        mock_service = Mock()
        mock_slack_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        form_values = {
            "reset_to_defaults": False
        }
        
        result = handler._validate_and_save_config("test_room", form_values)
        
        assert result["success"] is False
        assert "general" in result["errors"]
        assert "at least one configuration value" in result["errors"]["general"]
    
    def test_handle_modal_submission_success(self):
        """Test successful modal submission handling."""
        mock_service = Mock()
        mock_service.save_room_config.return_value = True
        mock_slack_client = Mock()
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        payload = {
            "view": {
                "private_metadata": json.dumps({"room_id": "test_room"}),
                "state": {
                    "values": {
                        "assistant_list_block": {
                            "assistant_list_input": {
                                "value": "assistant1, assistant2"
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
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        payload = {
            "view": {
                "private_metadata": json.dumps({"room_id": "test_room"}),
                "state": {
                    "values": {
                        "assistant_list_block": {
                            "assistant_list_input": {
                                "value": ""  # Empty value should cause error
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
        
        handler = ConfigModalHandler(mock_service, mock_slack_client)
        
        # Invalid payload (missing required fields)
        payload = {
            "view": {
                "private_metadata": "invalid json"
            }
        }
        
        result = handler.handle_modal_submission(payload)
        
        assert result["response_action"] == "errors"
        assert "general" in result["errors"]