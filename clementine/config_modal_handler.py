
"""Configuration modal handler for Slack BlockKit interactions."""

import logging
import json
from typing import Dict, Any, Optional, List

from .room_config_service import RoomConfigService
from .slack_client import SlackClient
from .tangerine import TangerineClient

logger = logging.getLogger(__name__)


class ConfigModalHandler:
    """Handles Slack modal interactions for room configuration."""
    
    def __init__(self, room_config_service: RoomConfigService, slack_client: SlackClient, tangerine_client: TangerineClient):
        self.room_config_service = room_config_service
        self.slack_client = slack_client
        self.tangerine_client = tangerine_client
    
    def create_config_modal(self, room_id: str, trigger_id: str) -> bool:
        """Create and show configuration modal for a room."""
        try:
            logger.debug("Creating config modal for room %s", room_id)
            current_config = self.room_config_service.get_current_config_for_display(room_id)
            logger.debug("Got current config: %s", current_config)
            modal_blocks = self._build_modal_blocks(current_config)
            logger.debug("Built modal blocks, count: %d", len(modal_blocks))
            
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
        assistant_options = self._fetch_assistant_options()
        
        # Find currently selected assistants that exist in available options
        current_assistants = config["assistant_list"]
        initial_options = []
        available_assistant_names = {option["value"] for option in assistant_options}
        
        for assistant_name in current_assistants:
            # Only include if the assistant exists in available options
            if assistant_name in available_assistant_names:
                for option in assistant_options:
                    if option["value"] == assistant_name:
                        initial_options.append(option)
                        break
            else:
                logger.warning("Assistant '%s' not found in available options, skipping from initial selection", assistant_name)
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Assistant List*\nSelect one or more assistants to use in this room"
            }
        })
        
        blocks.append({
            "type": "input",
            "block_id": "assistant_list_block",
            "element": {
                "type": "multi_static_select",
                "action_id": "assistant_list_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select assistants..."
                },
                "options": assistant_options,
                "initial_options": initial_options
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
        
        # Slack context size configuration
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Slack Context Size*\nNumber of messages to analyze (range: {config['slack_min_context']}-{config['slack_max_context']})"
            }
        })
        
        blocks.append({
            "type": "input",
            "block_id": "slack_context_size_block",
            "element": {
                "type": "number_input",
                "action_id": "slack_context_size_input",
                "is_decimal_allowed": False,
                "min_value": str(config['slack_min_context']),
                "max_value": str(config['slack_max_context']),
                "initial_value": str(config["slack_context_size"])
            },
            "label": {
                "type": "plain_text",
                "text": "Context Size"
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
                "block_id": "reset_to_defaults_block",
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
    
    def _fetch_assistant_options(self) -> List[Dict[str, Any]]:
        """Fetch assistants from API and format them as Slack select options."""
        try:
            logger.debug("Fetching assistants from API for modal options")
            assistants = self.tangerine_client.fetch_assistants()
            logger.debug("Fetched %d assistants from API", len(assistants))
            options = []
            for assistant in assistants:
                # Create option object for Slack multi-select using just the name
                assistant_name = assistant.get('name', 'unknown')
                option = {
                    "text": {
                        "type": "plain_text",
                        "text": assistant_name
                    },
                    "value": assistant_name
                }
                options.append(option)
                logger.debug("Added assistant option: %s", assistant_name)
            logger.debug("Created %d assistant options for modal", len(options))
            return options
        except Exception as e:
            logger.error("Failed to fetch assistants for modal: %s", e)
            logger.exception("Full traceback:")
            # Return fallback options if API call fails
            logger.info("Using fallback assistant options")
            return [
                {
                    "text": {
                        "type": "plain_text",
                        "text": "konflux"
                    },
                    "value": "konflux"
                }
            ]
    
    def _extract_form_values(self, state_values: Dict[str, Any]) -> Dict[str, Any]:
        """Extract form values from modal state."""
        form_values = {}
        
        # Extract assistant list from multi-select
        assistant_block = state_values.get("assistant_list_block", {})
        assistant_select = assistant_block.get("assistant_list_select", {})
        selected_options = assistant_select.get("selected_options", [])
        if selected_options:
            # Extract assistant names from selected options
            assistants = [option["value"] for option in selected_options]
            form_values["assistant_list"] = assistants
        
        # Extract system prompt
        prompt_block = state_values.get("system_prompt_block", {})
        prompt_input = prompt_block.get("system_prompt_input", {})
        prompt_value = prompt_input.get("value", "").strip()
        if prompt_value:
            form_values["system_prompt"] = prompt_value
        
        # Extract slack context size
        context_size_block = state_values.get("slack_context_size_block", {})
        context_size_input = context_size_block.get("slack_context_size_input", {})
        context_size_value = context_size_input.get("value", "").strip()
        if context_size_value:
            try:
                form_values["slack_context_size"] = int(context_size_value)
            except ValueError:
                # Invalid number will be caught in validation
                form_values["slack_context_size"] = context_size_value
        
        # Check for reset option
        reset_section = state_values.get("reset_to_defaults_block", {})
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
        
        # Validate slack context size
        slack_context_size = form_values.get("slack_context_size")
        if slack_context_size is not None:
            if not isinstance(slack_context_size, int):
                errors["slack_context_size_block"] = "Context size must be a valid number"
            else:
                # Get current config to check min/max bounds
                current_config = self.room_config_service.get_current_config_for_display(room_id)
                min_context = current_config["slack_min_context"]
                max_context = current_config["slack_max_context"]
                
                if slack_context_size < min_context:
                    errors["slack_context_size_block"] = f"Context size must be at least {min_context}"
                elif slack_context_size > max_context:
                    errors["slack_context_size_block"] = f"Context size must be at most {max_context}"
        
        # If we have validation errors, return them
        if errors:
            return {"success": False, "errors": errors}
        
        # Check if we actually have something to save
        if assistant_list is None and system_prompt is None and slack_context_size is None:
            errors["general"] = "Please provide at least one configuration value"
            return {"success": False, "errors": errors}
        
        # Save the configuration
        success = self.room_config_service.save_room_config(
            room_id=room_id,
            assistant_list=assistant_list,
            system_prompt=system_prompt,
            slack_context_size=slack_context_size
        )
        
        if not success:
            errors["general"] = "Failed to save configuration. Please try again."
        
        return {
            "success": success,
            "errors": errors
        }