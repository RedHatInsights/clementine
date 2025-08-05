"""Configuration modal handler for Slack BlockKit interactions."""

import logging
import json
from typing import Dict, Any, Optional, List

from .room_config_service import RoomConfigService
from .slack_client import SlackClient

logger = logging.getLogger(__name__)


class ConfigModalHandler:
    """Handles Slack modal interactions for room configuration."""
    
    def __init__(self, room_config_service: RoomConfigService, slack_client: SlackClient):
        self.room_config_service = room_config_service
        self.slack_client = slack_client
    
    def create_config_modal(self, room_id: str, trigger_id: str) -> bool:
        """Create and show configuration modal for a room."""
        try:
            current_config = self.room_config_service.get_current_config_for_display(room_id)
            modal_blocks = self._build_modal_blocks(current_config)
            
            modal_view = {
                "type": "modal",
                "callback_id": "room_config_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Room Configuration"
                },
                "submit": {
                    "type": "plain_text", 
                    "text": "Save"
                },
                "close": {
                    "type": "plain_text",
                    "text": "Cancel"
                },
                "blocks": modal_blocks,
                "private_metadata": json.dumps({"room_id": room_id})
            }
            
            # Open the modal using Slack API
            response = self.slack_client.client.views_open(
                trigger_id=trigger_id,
                view=modal_view
            )
            
            if response["ok"]:
                logger.info("Successfully opened config modal for room %s", room_id)
                return True
            else:
                logger.error("Failed to open config modal: %s", response.get("error", "Unknown error"))
                return False
                
        except Exception as e:
            logger.error("Error creating config modal for room %s: %s", room_id, e)
            return False
    
    def handle_modal_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle modal submission and save configuration."""
        try:
            # Extract room ID from private metadata
            private_metadata = json.loads(payload["view"]["private_metadata"])
            room_id = private_metadata["room_id"]
            
            # Extract form values
            form_values = self._extract_form_values(payload["view"]["state"]["values"])
            
            # Validate and save configuration
            validation_result = self._validate_and_save_config(room_id, form_values)
            
            if validation_result["success"]:
                logger.info("Successfully saved configuration for room %s", room_id)
                return {
                    "response_action": "clear"
                }
            else:
                logger.warning("Validation failed for room %s: %s", room_id, validation_result["errors"])
                return {
                    "response_action": "errors",
                    "errors": validation_result["errors"]
                }
                
        except Exception as e:
            logger.error("Error handling modal submission: %s", e)
            return {
                "response_action": "errors",
                "errors": {
                    "general": "An unexpected error occurred. Please try again."
                }
            }
    
    def _build_modal_blocks(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build BlockKit blocks for the configuration modal."""
        blocks = []
        
        # Info section
        if config["has_custom_config"]:
            info_text = "📝 This room has custom configuration. You can modify it below or reset to defaults."
        else:
            info_text = "🏠 This room is using default configuration. Set custom values below."
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": info_text
            }
        })
        
        blocks.append({
            "type": "divider"
        })
        
        # Assistant list configuration
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Assistant List*\nEnter assistants as a comma-separated list (e.g., `konflux, assistant2, assistant3`)"
            }
        })
        
        blocks.append({
            "type": "input",
            "block_id": "assistant_list_block",
            "element": {
                "type": "plain_text_input",
                "action_id": "assistant_list_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "konflux, assistant2, assistant3"
                },
                "initial_value": ", ".join(config["assistant_list"])
            },
            "label": {
                "type": "plain_text",
                "text": "Assistants"
            },
            "optional": True
        })
        
        # System prompt configuration
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*System Prompt*\nCustomize the AI's behavior and personality for this room"
            }
        })
        
        blocks.append({
            "type": "input",
            "block_id": "system_prompt_block",
            "element": {
                "type": "plain_text_input",
                "action_id": "system_prompt_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "You are a helpful assistant..."
                },
                "initial_value": config["system_prompt"]
            },
            "label": {
                "type": "plain_text",
                "text": "System Prompt"
            },
            "optional": True
        })
        
        # Reset option
        if config["has_custom_config"]:
            blocks.append({
                "type": "divider"
            })
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Reset to Defaults*\nCheck this box to remove custom configuration and use system defaults"
                },
                "accessory": {
                    "type": "checkboxes",
                    "action_id": "reset_to_defaults",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Reset to defaults"
                            },
                            "value": "reset"
                        }
                    ]
                }
            })
        
        return blocks
    
    def _extract_form_values(self, state_values: Dict[str, Any]) -> Dict[str, Any]:
        """Extract form values from modal state."""
        form_values = {}
        
        # Extract assistant list
        assistant_block = state_values.get("assistant_list_block", {})
        assistant_input = assistant_block.get("assistant_list_input", {})
        assistant_value = assistant_input.get("value", "").strip()
        if assistant_value:
            # Parse comma-separated list
            assistants = [a.strip() for a in assistant_value.split(",") if a.strip()]
            form_values["assistant_list"] = assistants
        
        # Extract system prompt
        prompt_block = state_values.get("system_prompt_block", {})
        prompt_input = prompt_block.get("system_prompt_input", {})
        prompt_value = prompt_input.get("value", "").strip()
        if prompt_value:
            form_values["system_prompt"] = prompt_value
        
        # Check for reset option
        reset_section = state_values.get("reset_to_defaults", {})
        if reset_section:
            reset_options = reset_section.get("reset_to_defaults", {}).get("selected_options", [])
            form_values["reset_to_defaults"] = len(reset_options) > 0
        else:
            form_values["reset_to_defaults"] = False
        
        return form_values
    
    def _validate_and_save_config(self, room_id: str, form_values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate form values and save configuration."""
        errors = {}
        
        # Handle reset to defaults
        if form_values.get("reset_to_defaults", False):
            success = self.room_config_service.reset_to_defaults(room_id)
            return {
                "success": success,
                "errors": {} if success else {"general": "Failed to reset configuration"}
            }
        
        # Validate assistant list
        assistant_list = form_values.get("assistant_list")
        if assistant_list is not None:
            if not assistant_list:
                errors["assistant_list_block"] = "Assistant list cannot be empty"
            elif len(assistant_list) > 10:  # Reasonable limit
                errors["assistant_list_block"] = "Too many assistants (max 10)"
            elif any(len(a) > 100 for a in assistant_list):  # Individual assistant name limit
                errors["assistant_list_block"] = "Assistant names must be under 100 characters"
        
        # Validate system prompt
        system_prompt = form_values.get("system_prompt")
        if system_prompt is not None:
            if len(system_prompt) > 5000:  # 5KB limit
                errors["system_prompt_block"] = "System prompt is too long (max 5000 characters)"
        
        # If we have validation errors, return them
        if errors:
            return {"success": False, "errors": errors}
        
        # Check if we actually have something to save
        if assistant_list is None and system_prompt is None:
            errors["general"] = "Please provide at least one configuration value"
            return {"success": False, "errors": errors}
        
        # Save the configuration
        success = self.room_config_service.save_room_config(
            room_id=room_id,
            assistant_list=assistant_list,
            system_prompt=system_prompt
        )
        
        if not success:
            errors["general"] = "Failed to save configuration. Please try again."
        
        return {
            "success": success,
            "errors": errors
        }