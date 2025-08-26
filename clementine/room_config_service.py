"""Room configuration service for business logic and configuration management."""

import logging
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .room_config_repository import RoomConfigRepository, RoomConfig

logger = logging.getLogger(__name__)


@dataclass
class ProcessedRoomConfig:
    """Processed room configuration with parsed values."""
    room_id: str
    assistant_list: List[str]
    system_prompt: str
    slack_context_size: int
    
    @classmethod
    def from_room_config(cls, config: RoomConfig, default_assistants: List[str], default_prompt: str, 
                        default_slack_context: int, slack_min_context: int, slack_max_context: int) -> 'ProcessedRoomConfig':
        """Create ProcessedRoomConfig from RoomConfig with defaults."""
        # Parse assistant list from JSON string
        assistants = default_assistants
        if config.assistant_list:
            try:
                parsed_assistants = json.loads(config.assistant_list)
                if isinstance(parsed_assistants, list) and all(isinstance(a, str) for a in parsed_assistants):
                    assistants = [a.strip() for a in parsed_assistants if a.strip()]
                    if not assistants:  # If empty after filtering, use defaults
                        assistants = default_assistants
                        logger.warning("Empty assistant list for room %s, using defaults", config.room_id)
                else:
                    logger.warning("Invalid assistant list format for room %s, using defaults", config.room_id)
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse assistant list for room %s: %s, using defaults", config.room_id, e)
        
        # Use custom prompt or default
        prompt = default_prompt
        if config.system_prompt is not None and isinstance(config.system_prompt, str):
            stripped_prompt = config.system_prompt.strip()
            if stripped_prompt:
                prompt = stripped_prompt
        if not prompt:
            prompt = default_prompt
            logger.warning("Empty system prompt for room %s, using default", config.room_id)
        
        # Use custom slack context size or default, with bounds clamping
        slack_context = default_slack_context
        if config.slack_context_size is not None and isinstance(config.slack_context_size, int):
            if config.slack_context_size > 0:
                # Clamp stored value to global min/max bounds
                clamped_size = max(slack_min_context, min(config.slack_context_size, slack_max_context))
                if clamped_size != config.slack_context_size:
                    logger.warning("Slack context size %d for room %s is out of bounds [%d-%d], clamping to %d", 
                                 config.slack_context_size, config.room_id, slack_min_context, slack_max_context, clamped_size)
                slack_context = clamped_size
            else:
                logger.warning("Invalid slack context size for room %s, using default", config.room_id)
        
        return cls(
            room_id=config.room_id,
            assistant_list=assistants,
            system_prompt=prompt,
            slack_context_size=slack_context
        )


class RoomConfigService:
    """Service for managing room configurations with validation and business logic."""
    
    def __init__(self, repository: RoomConfigRepository, default_assistants: List[str], default_prompt: str, 
                 default_slack_context: int, slack_min_context: int, slack_max_context: int):
        self.repository = repository
        self.default_assistants = default_assistants
        self.default_prompt = default_prompt
        self.default_slack_context = default_slack_context
        self.slack_min_context = slack_min_context
        self.slack_max_context = slack_max_context
    
    def get_room_config(self, room_id: str) -> ProcessedRoomConfig:
        """Get processed room configuration with fallback to defaults."""
        try:
            config = self.repository.get_room_config(room_id)
            
            if config:
                logger.debug("Using custom configuration for room %s", room_id)
                return ProcessedRoomConfig.from_room_config(config, self.default_assistants, self.default_prompt, 
                                                          self.default_slack_context, self.slack_min_context, self.slack_max_context)
            else:
                logger.debug("Using default configuration for room %s", room_id)
                return ProcessedRoomConfig(
                    room_id=room_id,
                    assistant_list=self.default_assistants,
                    system_prompt=self.default_prompt,
                    slack_context_size=self.default_slack_context
                )
        except Exception as e:
            logger.error("Error getting room config for %s, using defaults: %s", room_id, e)
            return ProcessedRoomConfig(
                room_id=room_id,
                assistant_list=self.default_assistants,
                system_prompt=self.default_prompt,
                slack_context_size=self.default_slack_context
            )
    
    def save_room_config(self, room_id: str, assistant_list: Optional[List[str]] = None, 
                        system_prompt: Optional[str] = None, slack_context_size: Optional[int] = None) -> bool:
        """Save room configuration with validation."""
        try:
            # Validate and process assistant list
            assistants_json = None
            if assistant_list is not None:
                validated_assistants = self._validate_assistant_list(assistant_list)
                if validated_assistants:
                    assistants_json = json.dumps(validated_assistants)
                else:
                    logger.warning("Invalid assistant list provided for room %s, ignoring", room_id)
            
            # Validate system prompt
            validated_prompt = None
            if system_prompt is not None:
                validated_prompt = self._validate_system_prompt(system_prompt)
                if not validated_prompt:
                    logger.warning("Invalid system prompt provided for room %s, ignoring", room_id)
            
            # Validate slack context size
            validated_slack_context = None
            if slack_context_size is not None:
                validated_slack_context = self._validate_slack_context_size(slack_context_size)
                if validated_slack_context is None:
                    logger.warning("Invalid slack context size provided for room %s, ignoring", room_id)
            
            # Only save if we have something to save
            if assistants_json is None and validated_prompt is None and validated_slack_context is None:
                logger.warning("No valid configuration provided for room %s", room_id)
                return False
            
            config = RoomConfig(
                room_id=room_id,
                assistant_list=assistants_json,
                system_prompt=validated_prompt,
                slack_context_size=validated_slack_context
            )
            
            success = self.repository.save_room_config(config)
            if success:
                logger.info("Successfully saved configuration for room %s", room_id)
            return success
            
        except Exception as e:
            logger.error("Error saving room config for %s: %s", room_id, e)
            return False
    
    def delete_room_config(self, room_id: str) -> bool:
        """Delete room configuration."""
        try:
            return self.repository.delete_room_config(room_id)
        except Exception as e:
            logger.error("Error deleting room config for %s: %s", room_id, e)
            return False
    
    def _validate_assistant_list(self, assistant_list: List[str]) -> Optional[List[str]]:
        """Validate and clean assistant list."""
        if not isinstance(assistant_list, list):
            return None
        
        # Clean and validate each assistant name
        validated = []
        for assistant in assistant_list:
            if isinstance(assistant, str):
                clean_name = assistant.strip()
                if clean_name and len(clean_name) <= 100:  # Reasonable limit
                    validated.append(clean_name)
        
        return validated if validated else None
    
    def _validate_system_prompt(self, system_prompt: str) -> Optional[str]:
        """Validate and clean system prompt."""
        if not isinstance(system_prompt, str):
            return None
        
        clean_prompt = system_prompt.strip()
        
        # Basic validation: not empty and reasonable length
        if clean_prompt and len(clean_prompt) <= 5000:  # 5KB limit for prompts
            return clean_prompt
        
        return None
    
    def _validate_slack_context_size(self, slack_context_size: int) -> Optional[int]:
        """Validate slack context size within min/max bounds."""
        if not isinstance(slack_context_size, int):
            return None
        
        # Ensure the value is within the configured min/max bounds
        if slack_context_size < self.slack_min_context:
            logger.warning("Slack context size %d is below minimum %d", slack_context_size, self.slack_min_context)
            return None
        
        if slack_context_size > self.slack_max_context:
            logger.warning("Slack context size %d is above maximum %d", slack_context_size, self.slack_max_context)
            return None
        
        return slack_context_size
    
    def get_current_config_for_display(self, room_id: str) -> Dict[str, Any]:
        """Get current room configuration formatted for display in UI."""
        config = self.get_room_config(room_id)
        
        # Check if this room has custom config or is using defaults
        stored_config = self.repository.get_room_config(room_id)
        has_custom_config = stored_config is not None
        
        return {
            "room_id": room_id,
            "assistant_list": config.assistant_list,
            "system_prompt": config.system_prompt,
            "slack_context_size": config.slack_context_size,
            "slack_min_context": self.slack_min_context,
            "slack_max_context": self.slack_max_context,
            "has_custom_config": has_custom_config,
            "assistant_list_json": json.dumps(config.assistant_list),  # For form display
        }
    
    def reset_to_defaults(self, room_id: str) -> bool:
        """Reset room configuration to defaults by deleting custom config."""
        try:
            return self.delete_room_config(room_id)
        except Exception as e:
            logger.error("Error resetting room config for %s: %s", room_id, e)
            return False