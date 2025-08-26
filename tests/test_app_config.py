"""Tests for app-level configuration functions."""

import pytest
from unittest.mock import patch
import os

from clementine.app_config import get_slack_context_limits, get_timeout_value


class TestSlackContextLimits:
    """Test get_slack_context_limits function."""
    
    @patch.dict(os.environ, {'SLACK_MIN_CONTEXT': '50', 'SLACK_MAX_CONTEXT': '250'})
    def test_valid_env_vars(self):
        """Test with valid environment variables."""
        min_context, max_context = get_slack_context_limits()
        assert min_context == 50
        assert max_context == 250
    
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_vars_use_defaults(self):
        """Test that missing environment variables use defaults."""
        min_context, max_context = get_slack_context_limits()
        assert min_context == 50  # Default
        assert max_context == 250  # Default
    
    @patch.dict(os.environ, {'SLACK_MIN_CONTEXT': 'invalid', 'SLACK_MAX_CONTEXT': 'not_a_number'})
    def test_non_numeric_inputs_use_defaults(self):
        """Test that non-numeric inputs fall back to defaults."""

        min_context, max_context = get_slack_context_limits()
        assert min_context == 50  # Default fallback
        assert max_context == 250  # Default fallback
    
    @patch.dict(os.environ, {'SLACK_MIN_CONTEXT': '-10', 'SLACK_MAX_CONTEXT': '0'})
    def test_negative_zero_values_use_defaults(self):
        """Test that negative and zero values use defaults."""

        min_context, max_context = get_slack_context_limits()
        assert min_context == 50  # Corrected from -10
        assert max_context == 250  # Corrected from 0
    
    @patch.dict(os.environ, {'SLACK_MIN_CONTEXT': '1500', 'SLACK_MAX_CONTEXT': '15000'})
    def test_very_large_values_capped(self):
        """Test that very large values are capped at reasonable limits."""

        min_context, max_context = get_slack_context_limits()
        assert min_context == 1000  # Capped at upper bound
        assert max_context == 10000  # Capped at upper bound
    
    @patch.dict(os.environ, {'SLACK_MIN_CONTEXT': '300', 'SLACK_MAX_CONTEXT': '100'})
    def test_min_greater_than_max_sets_max_to_min(self):
        """Test that when min > max, max is set to min."""

        min_context, max_context = get_slack_context_limits()
        assert min_context == 300
        assert max_context == 300  # Set to min value
    
    @patch.dict(os.environ, {'SLACK_MIN_CONTEXT': '1001', 'SLACK_MAX_CONTEXT': '50'})
    def test_min_over_limit_and_max_under_min_handled(self):
        """Test edge case where min is over limit and max is under corrected min."""

        min_context, max_context = get_slack_context_limits()
        assert min_context == 1000  # Capped at 1000
        assert max_context == 1000  # Set to min after capping
    
    @patch.dict(os.environ, {'SLACK_MIN_CONTEXT': '75', 'SLACK_MAX_CONTEXT': '150'})
    def test_valid_custom_values(self):
        """Test that valid custom values are preserved."""

        min_context, max_context = get_slack_context_limits()
        assert min_context == 75
        assert max_context == 150
    
    @patch.dict(os.environ, {'SLACK_MIN_CONTEXT': '1', 'SLACK_MAX_CONTEXT': '10000'})
    def test_boundary_values(self):
        """Test boundary values at the edges of acceptable ranges."""

        min_context, max_context = get_slack_context_limits()
        assert min_context == 1  # Minimum allowed
        assert max_context == 10000  # Maximum allowed


class TestTimeoutValue:
    """Test get_timeout_value function for completeness."""
    
    @patch.dict(os.environ, {'TANGERINE_API_TIMEOUT': '600'})
    def test_valid_timeout(self):
        """Test valid timeout value."""

        timeout = get_timeout_value()
        assert timeout == 600
    
    @patch.dict(os.environ, {'TANGERINE_API_TIMEOUT': 'invalid'})
    def test_invalid_timeout_uses_default(self):
        """Test invalid timeout falls back to default."""

        timeout = get_timeout_value()
        assert timeout == 500  # Default
    
    @patch.dict(os.environ, {'TANGERINE_API_TIMEOUT': '-100'})
    def test_negative_timeout_uses_default(self):
        """Test negative timeout uses default."""

        timeout = get_timeout_value()
        assert timeout == 500  # Default
    
    @patch.dict(os.environ, {'TANGERINE_API_TIMEOUT': '5000'})
    def test_too_large_timeout_capped(self):
        """Test timeout over 1 hour is capped."""

        timeout = get_timeout_value()
        assert timeout == 3600  # Capped at 1 hour
