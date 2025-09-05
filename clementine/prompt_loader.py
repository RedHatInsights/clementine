"""Prompt loader service for loading system and user prompts from files."""

import os
import logging
from typing import NamedTuple
from pathlib import Path

logger = logging.getLogger(__name__)


class Prompts(NamedTuple):
    """Container for loaded prompts."""
    system_prompt: str
    user_prompt: str
    slack_analysis_user_prompt: str


class PromptLoader:
    """Service for loading prompts from text files at startup."""
    
    def __init__(self, prompts_dir: str = None):
        """Initialize prompt loader with prompts directory path.
        
        Args:
            prompts_dir: Path to directory containing prompt files.
                        Defaults to 'prompts' directory in project root.
        """
        if prompts_dir is None:
            # Default to prompts directory in project root
            project_root = Path(__file__).parent.parent
            self.prompts_dir = project_root / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)
        
        logger.info("PromptLoader initialized with directory: %s", self.prompts_dir)
    
    def load_prompts(self) -> Prompts:
        """Load system and user prompts from files.
        
        Returns:
            Prompts: Named tuple containing system_prompt and user_prompt
            
        Raises:
            FileNotFoundError: If prompt files are missing
            ValueError: If prompt files are empty or invalid
        """
        logger.info("Loading prompts from %s", self.prompts_dir)
        
        system_prompt_path = self.prompts_dir / "default_system_prompt.txt"
        user_prompt_path = self.prompts_dir / "default_user_prompt.txt"
        slack_user_prompt_path = self.prompts_dir / "slack_analysis_user_prompt.txt"
        
        # Load system prompt
        system_prompt = self._load_prompt_file(system_prompt_path, "system prompt")
        
        # Load user prompt
        user_prompt = self._load_prompt_file(user_prompt_path, "user prompt")
        
        # Load Slack-specific user prompt (optional)
        slack_analysis_user_prompt = None
        try:
            slack_analysis_user_prompt = self._load_prompt_file(slack_user_prompt_path, "slack analysis user prompt")
        except FileNotFoundError:
            logger.warning("Slack analysis user prompt file not found, using default user prompt")
            slack_analysis_user_prompt = user_prompt
        
        logger.info("Successfully loaded prompts - system: %d chars, user: %d chars, slack user: %d chars", 
                   len(system_prompt), len(user_prompt), len(slack_analysis_user_prompt))
        
        return Prompts(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            slack_analysis_user_prompt=slack_analysis_user_prompt
        )
    
    def _load_prompt_file(self, file_path: Path, prompt_type: str) -> str:
        """Load a single prompt file with validation.
        
        Args:
            file_path: Path to the prompt file
            prompt_type: Human-readable description for logging
            
        Returns:
            str: The loaded prompt content
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file is empty
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Missing {prompt_type} file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                raise ValueError(f"Empty {prompt_type} file: {file_path}")
            
            logger.debug("Loaded %s from %s (%d characters)", prompt_type, file_path, len(content))
            return content
            
        except Exception as e:
            logger.error("Failed to load %s from %s: %s", prompt_type, file_path, e)
            raise
