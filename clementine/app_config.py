"""Application configuration parsing and validation."""

import logging
import os

logger = logging.getLogger(__name__)


def get_slack_context_limits() -> tuple[int, int]:
    """Get and validate the Slack context min/max values from environment."""
    min_str = os.getenv("SLACK_MIN_CONTEXT", "50")
    max_str = os.getenv("SLACK_MAX_CONTEXT", "250")
    
    try:
        min_context = int(min_str)
        max_context = int(max_str)
        
        # Validate min context
        if min_context <= 0:
            logger.warning("Invalid min context value %d, must be positive. Using default 50.", min_context)
            min_context = 50
        if min_context > 1000:  # Reasonable upper bound for min
            logger.warning("Min context value %d too large, capping at 1000.", min_context)
            min_context = 1000
            
        # Validate max context
        if max_context <= 0:
            logger.warning("Invalid max context value %d, must be positive. Using default 250.", max_context)
            max_context = 250
        if max_context > 10000:  # Reasonable upper bound for max
            logger.warning("Max context value %d too large, capping at 10000.", max_context)
            max_context = 10000
            
        # Ensure max >= min
        if max_context < min_context:
            logger.warning("Max context %d is less than min context %d, setting max to min.", max_context, min_context)
            max_context = min_context
            
        return min_context, max_context
        
    except ValueError:
        logger.error("Invalid context values (min='%s', max='%s'), must be numbers. Using defaults (50, 250).", min_str, max_str)
        return 50, 250


def get_timeout_value() -> int:
    """Get and validate the API timeout value from environment."""
    timeout_str = os.getenv("TANGERINE_API_TIMEOUT", "500")
    try:
        timeout_value = int(timeout_str)
        if timeout_value <= 0:
            logger.warning("Invalid timeout value %d, must be positive. Using default 500.", timeout_value)
            return 500
        if timeout_value > 3600:  # 1 hour max
            logger.warning("Timeout value %d too large, capping at 3600 seconds.", timeout_value)
            return 3600
        return timeout_value
    except ValueError:
        logger.error("Invalid timeout value '%s', must be a number. Using default 500.", timeout_str)
        return 500


def get_model_override() -> str | None:
    """Get the model override value from environment."""
    model_override = os.getenv("MODEL_OVERRIDE")
    if model_override:
        model_override = model_override.strip()
        if not model_override:
            logger.warning("MODEL_OVERRIDE is set but empty, ignoring")
            return None
        logger.info("Using model override: %s", model_override)
        return model_override
    return None
