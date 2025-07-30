"""
Clementine - A Slack bot for interacting with Tangerine AI assistants.

This package provides a clean, object-oriented interface for building
Slack bots that integrate with the Tangerine AI platform.
"""

from .bot import ClementineBot
from .slack_client import SlackClient, SlackEvent
from .tangerine import TangerineClient, TangerineResponse
from .formatters import MessageFormatter
from .error_handling import ErrorHandler

__version__ = "0.1.0"

__all__ = [
    "ClementineBot",
    "SlackClient", 
    "SlackEvent",
    "TangerineClient",
    "TangerineResponse", 
    "MessageFormatter",
    "ErrorHandler",
] 