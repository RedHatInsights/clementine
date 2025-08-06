# Slack Context Questions Feature

This document describes the new Slack context questions feature that allows users to ask questions about the current Slack channel context.

## Usage

Use the `/clementine slack <question>` command to ask questions about the current channel's conversation history.

### Examples

```
/clementine slack what are andrew and psav talking about re: clowder
/clementine slack what was the main decision made in this channel today?
/clementine slack can you summarize the discussion about the API changes?
```

### User Name Display

The bot now displays real user names instead of user IDs in the conversation context, making it easier to ask questions about specific people. For example:

- Instead of: "User U123456: Hello everyone"  
- You'll see: "Andrew Chen: Hello everyone"

This allows you to ask natural questions like "what are andrew and psav talking about?" rather than having to use cryptic user IDs.

## How It Works

1. **Context Extraction**: When you ask a question, the bot retrieves recent messages from the current channel
2. **Advanced Chat API**: The conversation history is sent as "chunks" to the advanced chat API using the "bring your own chunks" feature with the "clowder" assistant
3. **Question Answering**: The LLM uses the channel context to answer your question
4. **Response Formatting**: The answer is formatted and posted back to Slack

## Architecture

The feature is implemented using clean OOP principles with separate responsibilities:

### New Classes

- **`SlackContextExtractor`**: Retrieves channel and thread history from Slack
- **`AdvancedChatClient`**: Handles communication with the "bring your own chunks" API  
- **`SlackQuestionBot`**: Orchestrates the complete workflow
- **`ChunksRequest`**: Value object for advanced chat API requests

### Design Principles

- **Single Responsibility**: Each class has one clear purpose
- **No Conditionals**: New classes were created instead of adding complexity to existing ones
- **Dependency Injection**: Classes depend on abstractions, not concrete implementations
- **Error Handling**: Comprehensive error handling throughout the workflow

## Configuration

No additional configuration is required. The feature uses the existing Tangerine API configuration.

## Limitations

- Only retrieves recent channel history (configurable, default 50 messages)
- Works with channel history, not private DMs
- Requires appropriate Slack permissions for message history access

## Testing

Comprehensive test coverage includes:
- Unit tests for all new classes
- Integration scenarios
- Error handling paths
- Mock-based testing to avoid external dependencies