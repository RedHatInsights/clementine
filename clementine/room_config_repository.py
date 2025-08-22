"""Room configuration database layer with SQLite persistence."""

import logging
import sqlite3
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class RoomConfig:
    """Value object representing room-specific configuration."""
    room_id: str
    assistant_list: Optional[str] = None  # JSON string of assistants
    system_prompt: Optional[str] = None
    slack_context_size: Optional[int] = None  # Number of messages to include in slack context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoomConfig':
        """Create RoomConfig from dictionary."""
        return cls(
            room_id=data["room_id"],
            assistant_list=data.get("assistant_list"),
            system_prompt=data.get("system_prompt"),
            slack_context_size=data.get("slack_context_size")
        )


class RoomConfigRepository:
    """Repository for room configuration persistence using SQLite."""
    
    def __init__(self, db_path: str = "room_configs.db"):
        self.db_path = db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self) -> None:
        """Ensure database file and table exist."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS room_configs (
                        room_id TEXT PRIMARY KEY,
                        assistant_list TEXT,
                        system_prompt TEXT,
                        slack_context_size INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Add slack_context_size column if it doesn't exist (for existing databases)
                try:
                    conn.execute("ALTER TABLE room_configs ADD COLUMN slack_context_size INTEGER")
                    logger.info("Added slack_context_size column to existing room_configs table")
                except sqlite3.OperationalError:
                    # Column already exists, which is fine
                    pass
                
                conn.commit()
                logger.info("Room configuration database initialized at %s", self.db_path)
        except sqlite3.Error as e:
            logger.error("Failed to initialize room configuration database: %s", e)
            raise
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error("Database error: %s", e)
            raise
        finally:
            if conn:
                conn.close()
    
    def get_room_config(self, room_id: str) -> Optional[RoomConfig]:
        """Get room configuration by room ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT room_id, assistant_list, system_prompt, slack_context_size FROM room_configs WHERE room_id = ?",
                    (room_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    logger.debug("Found room config for room %s", room_id)
                    return RoomConfig(
                        room_id=row["room_id"],
                        assistant_list=row["assistant_list"],
                        system_prompt=row["system_prompt"],
                        slack_context_size=row["slack_context_size"]
                    )
                else:
                    logger.debug("No room config found for room %s", room_id)
                    return None
                    
        except sqlite3.Error as e:
            logger.error("Failed to get room config for room %s: %s", room_id, e)
            raise
    
    def save_room_config(self, config: RoomConfig) -> bool:
        """Save or update room configuration."""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO room_configs 
                    (room_id, assistant_list, system_prompt, slack_context_size, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (config.room_id, config.assistant_list, config.system_prompt, config.slack_context_size))
                conn.commit()
                
                logger.info("Saved room config for room %s", config.room_id)
                return True
                
        except sqlite3.Error as e:
            logger.error("Failed to save room config for room %s: %s", config.room_id, e)
            return False
    
    def delete_room_config(self, room_id: str) -> bool:
        """Delete room configuration."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM room_configs WHERE room_id = ?", 
                    (room_id,)
                )
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info("Deleted room config for room %s", room_id)
                    return True
                else:
                    logger.debug("No room config found to delete for room %s", room_id)
                    return False
                    
        except sqlite3.Error as e:
            logger.error("Failed to delete room config for room %s: %s", room_id, e)
            return False
    
    def list_all_room_configs(self) -> Dict[str, RoomConfig]:
        """Get all room configurations (for debugging/admin purposes)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT room_id, assistant_list, system_prompt, slack_context_size FROM room_configs"
                )
                
                configs = {}
                for row in cursor.fetchall():
                    config = RoomConfig(
                        room_id=row["room_id"],
                        assistant_list=row["assistant_list"],
                        system_prompt=row["system_prompt"],
                        slack_context_size=row["slack_context_size"]
                    )
                    configs[config.room_id] = config
                
                logger.debug("Retrieved %d room configurations", len(configs))
                return configs
                
        except sqlite3.Error as e:
            logger.error("Failed to list room configurations: %s", e)
            raise