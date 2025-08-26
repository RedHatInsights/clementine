"""Tests for room configuration repository."""

import pytest
import tempfile
import os
from unittest.mock import patch

from clementine.room_config_repository import RoomConfigRepository, RoomConfig


class TestRoomConfigRepository:
    """Test RoomConfigRepository database operations."""
    
    def test_init_creates_database_and_table(self):
        """Test that repository initialization creates database and table."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_db_path = temp_file.name
        
        try:
            # Remove the temp file so we can test database creation
            os.unlink(temp_db_path)
            
            repo = RoomConfigRepository(temp_db_path)
            
            # Verify database file was created
            assert os.path.exists(temp_db_path)
            
            # Verify we can perform basic operations (table exists)
            config = RoomConfig(room_id="test", assistant_list="test", system_prompt="test")
            assert repo.save_room_config(config) is True
            
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    def test_save_and_get_room_config(self):
        """Test saving and retrieving room configuration."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_db_path = temp_file.name
        
        try:
            repo = RoomConfigRepository(temp_db_path)
            
            # Save config
            config = RoomConfig(
                room_id="test_room",
                assistant_list='["assistant1", "assistant2"]',
                system_prompt="You are a helpful assistant"
            )
            
            result = repo.save_room_config(config)
            assert result is True
            
            # Retrieve config
            retrieved = repo.get_room_config("test_room")
            assert retrieved is not None
            assert retrieved.room_id == "test_room"
            assert retrieved.assistant_list == '["assistant1", "assistant2"]'
            assert retrieved.system_prompt == "You are a helpful assistant"
            
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    def test_get_nonexistent_room_config(self):
        """Test getting configuration for room that doesn't exist."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_db_path = temp_file.name
        
        try:
            repo = RoomConfigRepository(temp_db_path)
            
            result = repo.get_room_config("nonexistent_room")
            assert result is None
            
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    def test_update_room_config(self):
        """Test updating existing room configuration."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_db_path = temp_file.name
        
        try:
            repo = RoomConfigRepository(temp_db_path)
            
            # Save initial config
            config1 = RoomConfig(
                room_id="test_room",
                assistant_list='["assistant1"]',
                system_prompt="First prompt"
            )
            repo.save_room_config(config1)
            
            # Update config
            config2 = RoomConfig(
                room_id="test_room",
                assistant_list='["assistant2", "assistant3"]',
                system_prompt="Updated prompt"
            )
            result = repo.save_room_config(config2)
            assert result is True
            
            # Verify update
            retrieved = repo.get_room_config("test_room")
            assert retrieved.assistant_list == '["assistant2", "assistant3"]'
            assert retrieved.system_prompt == "Updated prompt"
            
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    def test_delete_room_config(self):
        """Test deleting room configuration."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_db_path = temp_file.name
        
        try:
            repo = RoomConfigRepository(temp_db_path)
            
            # Save config
            config = RoomConfig(
                room_id="test_room",
                assistant_list='["assistant1"]',
                system_prompt="Test prompt"
            )
            repo.save_room_config(config)
            
            # Verify it exists
            assert repo.get_room_config("test_room") is not None
            
            # Delete it
            result = repo.delete_room_config("test_room")
            assert result is True
            
            # Verify it's gone
            assert repo.get_room_config("test_room") is None
            
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    def test_delete_nonexistent_room_config(self):
        """Test deleting configuration that doesn't exist."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_db_path = temp_file.name
        
        try:
            repo = RoomConfigRepository(temp_db_path)
            
            result = repo.delete_room_config("nonexistent_room")
            assert result is False
            
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    def test_list_all_room_configs(self):
        """Test listing all room configurations."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_db_path = temp_file.name
        
        try:
            repo = RoomConfigRepository(temp_db_path)
            
            # Save multiple configs
            config1 = RoomConfig(room_id="room1", assistant_list='["a1"]', system_prompt="prompt1")
            config2 = RoomConfig(room_id="room2", assistant_list='["a2"]', system_prompt="prompt2")
            
            repo.save_room_config(config1)
            repo.save_room_config(config2)
            
            # List all configs
            configs = repo.list_all_room_configs()
            
            assert len(configs) == 2
            assert "room1" in configs
            assert "room2" in configs
            assert configs["room1"].assistant_list == '["a1"]'
            assert configs["room2"].system_prompt == "prompt2"
            
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    def test_partial_config_save(self):
        """Test saving configuration with only some fields set."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_db_path = temp_file.name
        
        try:
            repo = RoomConfigRepository(temp_db_path)
            
            # Save config with only assistant list
            config1 = RoomConfig(room_id="test_room", assistant_list='["assistant1"]', system_prompt=None)
            result = repo.save_room_config(config1)
            assert result is True
            
            retrieved = repo.get_room_config("test_room")
            assert retrieved.assistant_list == '["assistant1"]'
            assert retrieved.system_prompt is None
            
            # Update with only system prompt
            config2 = RoomConfig(room_id="test_room", assistant_list=None, system_prompt="New prompt")
            result = repo.save_room_config(config2)
            assert result is True
            
            retrieved = repo.get_room_config("test_room")
            assert retrieved.assistant_list is None  # Should be overwritten
            assert retrieved.system_prompt == "New prompt"
            
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    @patch('clementine.room_config_repository.sqlite3.connect')
    def test_database_error_handling(self, mock_connect):
        """Test handling of database errors."""
        import sqlite3
        
        # Mock database error
        mock_connect.side_effect = sqlite3.Error("Database error")
        
        with pytest.raises(sqlite3.Error):
            RoomConfigRepository("test.db")
    
    def test_room_config_dataclass(self):
        """Test RoomConfig dataclass methods."""
        config = RoomConfig(
            room_id="test",
            assistant_list='["a1", "a2"]',
            system_prompt="Test prompt"
        )
        
        # Test to_dict
        data = config.to_dict()
        expected = {
            "room_id": "test",
            "assistant_list": '["a1", "a2"]',
            "system_prompt": "Test prompt",
            "slack_context_size": None
        }
        assert data == expected
        
        # Test from_dict
        recreated = RoomConfig.from_dict(data)
        assert recreated.room_id == config.room_id
        assert recreated.assistant_list == config.assistant_list
        assert recreated.system_prompt == config.system_prompt
        assert recreated.slack_context_size == config.slack_context_size