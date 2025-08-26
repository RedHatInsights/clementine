"""Tests for room configuration service."""

import pytest
from unittest.mock import Mock, patch
import json

from clementine.room_config_service import RoomConfigService, ProcessedRoomConfig
from clementine.room_config_repository import RoomConfig


class TestRoomConfigService:
    """Test RoomConfigService business logic."""
    
    def test_get_room_config_with_custom_config(self):
        """Test getting room config when custom config exists."""
        mock_repo = Mock()
        mock_repo.get_room_config.return_value = RoomConfig(
            room_id="test_room",
            assistant_list='["custom_assistant"]',
            system_prompt="Custom prompt"
        )
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default_assistant"],
            default_prompt="Default prompt",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        config = service.get_room_config("test_room")
        
        assert isinstance(config, ProcessedRoomConfig)
        assert config.room_id == "test_room"
        assert config.assistant_list == ["custom_assistant"]
        assert config.system_prompt == "Custom prompt"
        mock_repo.get_room_config.assert_called_once_with("test_room")
    
    def test_get_room_config_with_no_custom_config(self):
        """Test getting room config when no custom config exists."""
        mock_repo = Mock()
        mock_repo.get_room_config.return_value = None
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default_assistant"],
            default_prompt="Default prompt",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        config = service.get_room_config("test_room")
        
        assert isinstance(config, ProcessedRoomConfig)
        assert config.room_id == "test_room"
        assert config.assistant_list == ["default_assistant"]
        assert config.system_prompt == "Default prompt"
    
    def test_get_room_config_with_invalid_assistant_list(self):
        """Test getting room config with invalid JSON assistant list."""
        mock_repo = Mock()
        mock_repo.get_room_config.return_value = RoomConfig(
            room_id="test_room",
            assistant_list='invalid json',
            system_prompt="Custom prompt"
        )
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default_assistant"],
            default_prompt="Default prompt",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        config = service.get_room_config("test_room")
        
        # Should fallback to defaults for invalid JSON
        assert config.assistant_list == ["default_assistant"]
        assert config.system_prompt == "Custom prompt"  # Valid prompt should be used
    
    def test_get_room_config_with_empty_assistant_list(self):
        """Test getting room config with empty assistant list."""
        mock_repo = Mock()
        mock_repo.get_room_config.return_value = RoomConfig(
            room_id="test_room",
            assistant_list='[]',
            system_prompt="Custom prompt"
        )
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default_assistant"],
            default_prompt="Default prompt",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        config = service.get_room_config("test_room")
        
        # Should fallback to defaults for empty list
        assert config.assistant_list == ["default_assistant"]
        assert config.system_prompt == "Custom prompt"
    
    def test_get_room_config_with_empty_prompt(self):
        """Test getting room config with empty system prompt."""
        mock_repo = Mock()
        mock_repo.get_room_config.return_value = RoomConfig(
            room_id="test_room",
            assistant_list='["custom_assistant"]',
            system_prompt=""
        )
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default_assistant"],
            default_prompt="Default prompt",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        config = service.get_room_config("test_room")
        
        assert config.assistant_list == ["custom_assistant"]
        # Should fallback to default for empty prompt
        assert config.system_prompt == "Default prompt"
    
    def test_save_room_config_success(self):
        """Test successful room config save."""
        mock_repo = Mock()
        mock_repo.save_room_config.return_value = True
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default"],
            default_prompt="Default",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        result = service.save_room_config(
            room_id="test_room",
            assistant_list=["assistant1", "assistant2"],
            system_prompt="Custom prompt"
        )
        
        assert result is True
        mock_repo.save_room_config.assert_called_once()
        
        # Check the saved config
        saved_config = mock_repo.save_room_config.call_args[0][0]
        assert saved_config.room_id == "test_room"
        assert saved_config.assistant_list == '["assistant1", "assistant2"]'
        assert saved_config.system_prompt == "Custom prompt"
    
    def test_save_room_config_with_invalid_assistant_list(self):
        """Test saving room config with invalid assistant list but valid prompt."""
        mock_repo = Mock()
        mock_repo.save_room_config.return_value = True
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default"],
            default_prompt="Default",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        # Test with invalid assistant list but valid prompt
        # Should ignore invalid assistant list and save valid prompt
        result = service.save_room_config(
            room_id="test_room",
            assistant_list="not a list",
            system_prompt="Valid prompt"
        )
        
        assert result is True
        mock_repo.save_room_config.assert_called_once()
        
        # Verify saved config has None for assistant_list but valid prompt
        saved_config = mock_repo.save_room_config.call_args[0][0]
        assert saved_config.room_id == "test_room"
        assert saved_config.assistant_list is None  # Invalid list ignored
        assert saved_config.system_prompt == "Valid prompt"  # Valid prompt saved
    
    def test_save_room_config_with_empty_values(self):
        """Test saving room config with empty/None values."""
        mock_repo = Mock()
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default"],
            default_prompt="Default",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        result = service.save_room_config(
            room_id="test_room",
            assistant_list=None,
            system_prompt=None
        )
        
        assert result is False
        mock_repo.save_room_config.assert_not_called()
    
    def test_save_room_config_with_only_invalid_data(self):
        """Test saving room config with only invalid data."""
        mock_repo = Mock()
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default"],
            default_prompt="Default",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        # Test with invalid assistant list AND invalid prompt
        result = service.save_room_config(
            room_id="test_room",
            assistant_list="not a list",
            system_prompt=""  # Empty prompt is invalid
        )
        
        assert result is False
        mock_repo.save_room_config.assert_not_called()
    
    def test_save_room_config_partial_update(self):
        """Test saving room config with only some fields."""
        mock_repo = Mock()
        mock_repo.save_room_config.return_value = True
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default"],
            default_prompt="Default",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        # Save only assistant list
        result = service.save_room_config(
            room_id="test_room",
            assistant_list=["new_assistant"],
            system_prompt=None
        )
        
        assert result is True
        saved_config = mock_repo.save_room_config.call_args[0][0]
        assert saved_config.assistant_list == '["new_assistant"]'
        assert saved_config.system_prompt is None
    
    def test_delete_room_config(self):
        """Test deleting room configuration."""
        mock_repo = Mock()
        mock_repo.delete_room_config.return_value = True
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default"],
            default_prompt="Default",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        result = service.delete_room_config("test_room")
        
        assert result is True
        mock_repo.delete_room_config.assert_called_once_with("test_room")
    
    def test_get_current_config_for_display(self):
        """Test getting configuration formatted for display."""
        mock_repo = Mock()
        mock_repo.get_room_config.return_value = RoomConfig(
            room_id="test_room",
            assistant_list='["assistant1", "assistant2"]',
            system_prompt="Custom prompt"
        )
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default"],
            default_prompt="Default",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        display_config = service.get_current_config_for_display("test_room")
        
        expected = {
            "room_id": "test_room",
            "assistant_list": ["assistant1", "assistant2"],
            "system_prompt": "Custom prompt",
            "has_custom_config": True,
            "assistant_list_json": '["assistant1", "assistant2"]'
        }
        assert display_config == expected
    
    def test_get_current_config_for_display_defaults(self):
        """Test getting display config when using defaults."""
        mock_repo = Mock()
        mock_repo.get_room_config.return_value = None
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default_assistant"],
            default_prompt="Default prompt",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        display_config = service.get_current_config_for_display("test_room")
        
        expected = {
            "room_id": "test_room",
            "assistant_list": ["default_assistant"],
            "system_prompt": "Default prompt",
            "has_custom_config": False,
            "assistant_list_json": '["default_assistant"]'
        }
        assert display_config == expected
    
    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        mock_repo = Mock()
        mock_repo.delete_room_config.return_value = True
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default"],
            default_prompt="Default",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        result = service.reset_to_defaults("test_room")
        
        assert result is True
        mock_repo.delete_room_config.assert_called_once_with("test_room")
    

    
    @patch('clementine.room_config_service.logger')
    def test_error_handling_in_get_room_config(self, mock_logger):
        """Test error handling in get_room_config."""
        mock_repo = Mock()
        mock_repo.get_room_config.side_effect = Exception("Database error")
        
        service = RoomConfigService(
            repository=mock_repo,
            default_assistants=["default"],
            default_prompt="Default",
            default_slack_context=50,
            slack_min_context=50,
            slack_max_context=250
        )
        
        # Should not raise exception, should return defaults
        config = service.get_room_config("test_room")
        
        assert config.assistant_list == ["default"]
        assert config.system_prompt == "Default"
        mock_logger.error.assert_called_once()