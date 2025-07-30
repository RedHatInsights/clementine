"""Feedback interaction handling for user feedback flow."""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

from .feedback_client import FeedbackClient, FeedbackRequest
from .slack_client import SlackClient

logger = logging.getLogger(__name__)


@dataclass
class FeedbackInteraction:
    """Value object representing a feedback interaction context."""
    interaction_id: str
    channel: str
    message_ts: str
    user_id: str


class FeedbackHandler:
    """Manages the user feedback interaction flow."""
    
    def __init__(self, feedback_client: FeedbackClient, slack_client: SlackClient):
        self.feedback_client = feedback_client
        self.slack_client = slack_client
    
    def show_sending_feedback_message(self, interaction_payload: Dict, respond_func) -> None:
        """Immediately show 'Sending feedback...' message by updating the original message."""
        try:
            # Get the current message blocks from the interaction
            message = interaction_payload.get("message", {})
            current_blocks = message.get("blocks", [])
            
            # Remove feedback buttons and add "Sending feedback..." message
            updated_blocks = self._remove_feedback_buttons_and_add_sending(current_blocks)
            
            # Update the message immediately using Slack's response mechanism
            respond_func({
                "replace_original": True,
                "blocks": updated_blocks,
                "text": message.get("text", "")
            })
            
            logger.debug("Displayed 'Sending feedback...' message")
            
        except Exception as e:
            logger.error("Error showing sending feedback message: %s", e)
    
    def handle_feedback_button_async(self, interaction_payload: Dict, respond_func) -> None:
        """Handle feedback button click asynchronously after showing initial response."""
        try:
            feedback_interaction = self._parse_interaction(interaction_payload)
            feedback_request = self._build_feedback_request(interaction_payload, feedback_interaction)
            
            logger.info("Processing feedback from user %s for interaction %s", 
                       feedback_interaction.user_id, feedback_interaction.interaction_id)
            
            # Send feedback to API
            success = self.feedback_client.send_feedback(feedback_request)
            
            # Get current message blocks and update with final result
            message = interaction_payload.get("message", {})
            current_blocks = message.get("blocks", [])
            
            if success:
                final_blocks = self._remove_feedback_buttons_and_add_thanks(current_blocks)
                logger.info("Feedback sent successfully for interaction %s", feedback_interaction.interaction_id)
            else:
                final_blocks = self._remove_feedback_buttons_and_add_error(current_blocks)
                logger.warning("Feedback failed for interaction %s", feedback_interaction.interaction_id)
            
            # Update with final result
            respond_func({
                "replace_original": True,
                "blocks": final_blocks,
                "text": message.get("text", "")
            })
                
        except Exception as e:
            logger.error("Error handling feedback button: %s", e)
            # Show error message
            try:
                message = interaction_payload.get("message", {})
                current_blocks = message.get("blocks", [])
                error_blocks = self._remove_feedback_buttons_and_add_error(current_blocks)
                respond_func({
                    "replace_original": True,
                    "blocks": error_blocks,
                    "text": message.get("text", "")
                })
            except:
                logger.error("Could not show error message to user")

    def handle_feedback_button(self, interaction_payload: Dict) -> None:
        """Handle feedback button click and orchestrate the feedback flow."""
        try:
            feedback_interaction = self._parse_interaction(interaction_payload)
            feedback_request = self._build_feedback_request(interaction_payload, feedback_interaction)
            
            logger.info("Processing feedback from user %s for interaction %s", 
                       feedback_interaction.user_id, feedback_interaction.interaction_id)
            
            # Send feedback to API
            success = self.feedback_client.send_feedback(feedback_request)
            
            # Update UI based on result - try both approaches for reliability
            if success:
                self._show_feedback_response(feedback_interaction, is_success=True)
            else:
                self._show_feedback_response(feedback_interaction, is_success=False)
                
        except Exception as e:
            logger.error("Error handling feedback button: %s", e)
            # Try to show generic error if we can extract basic interaction info
            try:
                feedback_interaction = self._parse_interaction(interaction_payload)
                self._show_feedback_response(feedback_interaction, is_success=False)
            except:
                logger.error("Could not show error message to user due to malformed interaction")
    
    def _parse_interaction(self, interaction_payload: Dict) -> FeedbackInteraction:
        """Parse Slack interaction payload into structured data."""
        try:
            container = interaction_payload.get("container", {})
            user = interaction_payload.get("user", {})
            
            # Extract interaction_id from action value
            actions = interaction_payload.get("actions", [])
            if not actions:
                raise ValueError("No actions found in interaction payload")
            
            action = actions[0]
            action_value = action.get("value", "")
            
            # Action value format: "feedback_like_<interaction_id>" or "feedback_dislike_<interaction_id>"
            if not action_value.startswith(("feedback_like_", "feedback_dislike_")):
                raise ValueError(f"Invalid action value format: {action_value}")
            
            interaction_id = action_value.split("_", 2)[2]  # Extract ID after second underscore
            
            channel_id = container.get("channel_id", "")
            message_ts = container.get("message_ts", "")
            user_id = user.get("id", "")
            
            logger.debug("Parsed feedback interaction - Channel: %s, Message TS: %s, User: %s, Interaction: %s", 
                        channel_id, message_ts, user_id, interaction_id)
            
            return FeedbackInteraction(
                interaction_id=interaction_id,
                channel=channel_id,
                message_ts=message_ts,
                user_id=user_id
            )
        except (KeyError, IndexError, ValueError) as e:
            logger.error("Failed to parse interaction payload: %s", e)
            logger.debug("Full interaction payload: %s", interaction_payload)
            raise ValueError(f"Invalid interaction payload format: {e}")
    
    def _build_feedback_request(self, interaction_payload: Dict, 
                              feedback_interaction: FeedbackInteraction) -> FeedbackRequest:
        """Build feedback request from interaction payload."""
        actions = interaction_payload.get("actions", [])
        action = actions[0]
        action_value = action.get("value", "")
        
        # Determine like/dislike from action value
        is_like = action_value.startswith("feedback_like_")
        
        return FeedbackRequest(
            like=is_like,
            dislike=not is_like,
            feedback="",  # No text feedback for button interactions
            interaction_id=feedback_interaction.interaction_id
        )
    
    def _show_feedback_response(self, feedback_interaction: FeedbackInteraction, is_success: bool) -> None:
        """Show feedback response with multiple fallback strategies."""
        try:
            # First, try to update the original message
            updated_successfully = self._try_update_original_message(feedback_interaction, is_success)
            
            if not updated_successfully:
                # Fallback: Post a new threaded message
                self._post_threaded_response(feedback_interaction, is_success)
                
        except Exception as e:
            logger.error("Error showing feedback response: %s", e)
            # Last resort: try just posting the threaded message
            try:
                self._post_threaded_response(feedback_interaction, is_success)
            except Exception as fallback_error:
                logger.error("Failed to show any feedback response: %s", fallback_error)
    
    def _try_update_original_message(self, feedback_interaction: FeedbackInteraction, is_success: bool) -> bool:
        """Try to update the original message. Returns True if successful."""
        try:
            current_message = self.slack_client.get_message(
                feedback_interaction.channel,
                feedback_interaction.message_ts
            )
            
            if current_message and "blocks" in current_message:
                if is_success:
                    updated_blocks = self._remove_feedback_buttons_and_add_thanks(current_message["blocks"])
                else:
                    updated_blocks = self._remove_feedback_buttons_and_add_error(current_message["blocks"])
                
                success = self.slack_client.update_message_with_blocks(
                    feedback_interaction.channel,
                    feedback_interaction.message_ts,
                    {"blocks": updated_blocks, "text": current_message.get("text", "")}
                )
                
                if success:
                    status = "thank you" if is_success else "error"
                    logger.info("Successfully updated message with %s for interaction %s", 
                               status, feedback_interaction.interaction_id)
                    return True
                    
            return False
            
        except Exception as e:
            logger.debug("Failed to update original message: %s", e)
            return False
    
    def _post_threaded_response(self, feedback_interaction: FeedbackInteraction, is_success: bool) -> None:
        """Post a threaded response message."""
        if is_success:
            blocks = [{
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": "✅ Thank you for your feedback!"
                }]
            }]
            text = "Thank you for your feedback!"
        else:
            blocks = [{
                "type": "context", 
                "elements": [{
                    "type": "mrkdwn",
                    "text": "⚠️ Oops, something went wrong sending feedback!"
                }]
            }]
            text = "Oops, something went wrong sending feedback!"
        
        self.slack_client.client.chat_postMessage(
            channel=feedback_interaction.channel,
            thread_ts=feedback_interaction.message_ts,
            blocks=blocks,
            text=text
        )
        
        status = "thank you" if is_success else "error"
        logger.info("Posted threaded %s message for interaction %s", 
                   status, feedback_interaction.interaction_id)

    def _show_thank_you_message(self, feedback_interaction: FeedbackInteraction) -> None:
        """Update message to show thank you and remove feedback buttons."""
        try:
            # Get current message to preserve content
            current_message = self.slack_client.get_message(
                feedback_interaction.channel, 
                feedback_interaction.message_ts
            )
            
            if current_message and "blocks" in current_message:
                # Remove feedback buttons and add thank you
                updated_blocks = self._remove_feedback_buttons_and_add_thanks(current_message["blocks"])
                
                success = self.slack_client.update_message_with_blocks(
                    feedback_interaction.channel,
                    feedback_interaction.message_ts,
                    {"blocks": updated_blocks, "text": current_message.get("text", "")}
                )
                
                if success:
                    logger.info("Successfully showed thank you message for interaction %s", 
                               feedback_interaction.interaction_id)
                else:
                    logger.warning("Failed to update message with thank you for interaction %s", 
                                  feedback_interaction.interaction_id)
            else:
                # Fallback: just try to update with a simple thank you message if we can't get current message
                logger.warning("Could not retrieve current message (likely missing Slack permissions), using fallback approach")
                fallback_blocks = [
                    {
                        "type": "context",
                        "block_id": "feedback_thanks",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "✅ Thank you for your feedback!"
                            }
                        ]
                    }
                ]
                
                # Try to post as a new message in the thread instead
                self.slack_client.client.chat_postMessage(
                    channel=feedback_interaction.channel,
                    thread_ts=feedback_interaction.message_ts,
                    blocks=fallback_blocks,
                    text="Thank you for your feedback!"
                )
                logger.info("Posted fallback thank you message in thread for interaction %s", 
                           feedback_interaction.interaction_id)
        except Exception as e:
            logger.error("Error showing thank you message: %s", e)
    
    def _show_error_message(self, feedback_interaction: FeedbackInteraction) -> None:
        """Update message to show error and remove feedback buttons."""
        try:
            # Get current message to preserve content  
            current_message = self.slack_client.get_message(
                feedback_interaction.channel,
                feedback_interaction.message_ts
            )
            
            if current_message and "blocks" in current_message:
                # Remove feedback buttons and add error message
                updated_blocks = self._remove_feedback_buttons_and_add_error(current_message["blocks"])
                
                success = self.slack_client.update_message_with_blocks(
                    feedback_interaction.channel,
                    feedback_interaction.message_ts,
                    {"blocks": updated_blocks, "text": current_message.get("text", "")}
                )
                
                if success:
                    logger.info("Successfully showed error message for interaction %s", 
                               feedback_interaction.interaction_id)
                else:
                    logger.warning("Failed to update message with error for interaction %s", 
                                  feedback_interaction.interaction_id)
            else:
                # Fallback: just try to post error message if we can't get current message
                logger.warning("Could not retrieve current message (likely missing Slack permissions), using fallback approach")
                fallback_blocks = [
                    {
                        "type": "context",
                        "block_id": "feedback_error",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "⚠️ Oops, something went wrong sending feedback!"
                            }
                        ]
                    }
                ]
                
                # Try to post as a new message in the thread instead
                self.slack_client.client.chat_postMessage(
                    channel=feedback_interaction.channel,
                    thread_ts=feedback_interaction.message_ts,
                    blocks=fallback_blocks,
                    text="Oops, something went wrong sending feedback!"
                )
                logger.info("Posted fallback error message in thread for interaction %s", 
                           feedback_interaction.interaction_id)
        except Exception as e:
            logger.error("Error showing error message: %s", e)
    
    def _remove_feedback_buttons_and_add_sending(self, blocks: list) -> list:
        """Remove feedback action block and add sending feedback message."""
        # Remove any existing feedback blocks
        filtered_blocks = [block for block in blocks 
                          if not (block.get("block_id") in ["feedback_actions", "feedback_thanks", "feedback_error", "feedback_sending"])]
        
        # Add sending feedback block
        sending_block = {
            "type": "context",
            "block_id": "feedback_sending",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "⏳ Sending feedback..."
                }
            ]
        }
        
        filtered_blocks.append(sending_block)
        return filtered_blocks

    def _remove_feedback_buttons_and_add_thanks(self, blocks: list) -> list:
        """Remove feedback action block and add thank you context block."""
        # Remove any existing feedback or thank you blocks
        filtered_blocks = [block for block in blocks 
                          if not (block.get("block_id") in ["feedback_actions", "feedback_thanks", "feedback_error", "feedback_sending"])]
        
        # Add thank you block
        thank_you_block = {
            "type": "context",
            "block_id": "feedback_thanks",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "✅ Thank you for your feedback!"
                }
            ]
        }
        
        filtered_blocks.append(thank_you_block)
        return filtered_blocks
    
    def _remove_feedback_buttons_and_add_error(self, blocks: list) -> list:
        """Remove feedback action block and add error context block."""
        # Remove any existing feedback or thank you blocks
        filtered_blocks = [block for block in blocks 
                          if not (block.get("block_id") in ["feedback_actions", "feedback_thanks", "feedback_error", "feedback_sending"])]
        
        # Add error block
        error_block = {
            "type": "context", 
            "block_id": "feedback_error",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "⚠️ Oops, something went wrong sending feedback!"
                }
            ]
        }
        
        filtered_blocks.append(error_block)
        return filtered_blocks 