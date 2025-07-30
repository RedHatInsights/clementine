"""Tests for LoadingMessageProvider."""

import unittest
from unittest.mock import patch
from clementine.loading_message_provider import LoadingMessageProvider


class TestLoadingMessageProvider(unittest.TestCase):
    """Test cases for LoadingMessageProvider."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_messages = [
            "🔍 Test message 1",
            "🤔 Test message 2", 
            "✨ Test message 3"
        ]
    
    def test_init_with_default_messages(self):
        """Test initialization with default messages."""
        provider = LoadingMessageProvider()
        self.assertGreater(provider.get_message_count(), 0)
    
    def test_init_with_custom_messages(self):
        """Test initialization with custom messages."""
        provider = LoadingMessageProvider(self.test_messages)
        self.assertEqual(provider.get_message_count(), 3)
    
    def test_init_with_empty_messages_raises_error(self):
        """Test that empty message list raises ValueError."""
        with self.assertRaises(ValueError):
            LoadingMessageProvider([])
    
    def test_get_random_message_returns_string(self):
        """Test that get_random_message returns a string."""
        provider = LoadingMessageProvider(self.test_messages)
        message = provider.get_random_message()
        self.assertIsInstance(message, str)
        self.assertIn(message, self.test_messages)
    
    def test_get_random_message_varies(self):
        """Test that get_random_message returns different messages over time."""
        provider = LoadingMessageProvider(self.test_messages)
        
        # Get multiple messages and check we get variety (probabilistic test)
        messages = [provider.get_random_message() for _ in range(20)]
        unique_messages = set(messages)
        
        # With 20 attempts and 3 messages, we should get some variety
        # This is probabilistic but very likely to pass
        self.assertGreater(len(unique_messages), 1)
    
    @patch('clementine.loading_message_provider.random.choice')
    def test_get_random_message_uses_random_choice(self, mock_choice):
        """Test that get_random_message uses random.choice."""
        mock_choice.return_value = "🔍 Test message 1"
        provider = LoadingMessageProvider(self.test_messages)
        
        result = provider.get_random_message()
        
        mock_choice.assert_called_once_with(self.test_messages)
        self.assertEqual(result, "🔍 Test message 1")
    
    def test_get_message_count_returns_correct_count(self):
        """Test that get_message_count returns correct number."""
        provider = LoadingMessageProvider(self.test_messages)
        self.assertEqual(provider.get_message_count(), len(self.test_messages))
    
    def test_messages_are_copied_not_referenced(self):
        """Test that provider copies messages, doesn't reference them."""
        original_messages = self.test_messages.copy()
        provider = LoadingMessageProvider(self.test_messages)
        
        # Modify original list
        self.test_messages.append("🎯 Added message")
        
        # Provider should still have original count
        self.assertEqual(provider.get_message_count(), len(original_messages))


if __name__ == '__main__':
    unittest.main()