# Clementine Slack Bot

Clementine is a Slack bot that provides AI-powered assistance by integrating with the Tangerine API service. It offers intelligent responses to user questions and can analyze Slack channel context to provide relevant information.

## Features

- **AI Assistant**: Responds to @mentions with intelligent answers using configurable AI assistants
- **Slack Context Analysis**: Analyze channel conversations with `/clementine slack <question>` command
- **Room Configuration**: Per-channel configuration for assistants, prompts, and context size
- **User Feedback**: Like/dislike buttons for response quality feedback
- **AI Disclosure**: Optional disclaimers for AI-generated content
- **Health Monitoring**: Built-in health checks for container deployments


## Quick Start

### For Developers (Local Development)

#### Prerequisites

- Python 3.11+
- pipenv (for dependency management)
- Docker and Docker Compose (for containerized development)
- Access to a Slack workspace with admin privileges
- Access to a Tangerine API instance

#### Local Setup

1. **Clone and install dependencies:**
   ```bash
   git clone <repository-url>
   cd clementine
   pipenv install --dev
   pipenv shell
   ```

2. **Create environment file:**
   ```bash
   cp docker-compose.yml.example docker-compose.yml
   # Edit docker-compose.yml with your configuration
   ```
   
   Or create a `.env` file:
   ```bash
   # Required Slack Configuration
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   SLACK_SIGNING_SECRET=your-signing-secret-here
   SLACK_APP_TOKEN=xapp-your-app-token-here
   
   # Required Tangerine API Configuration
   TANGERINE_API_URL=https://your-tangerine-api.example.com
   TANGERINE_API_TOKEN=your-tangerine-api-token-here
   
   # Optional: Advanced Configuration
   SLACK_MIN_CONTEXT=50
   SLACK_MAX_CONTEXT=250
   MODEL_OVERRIDE=chatgpt-4o
   ```

3. **Run locally:**
   ```bash
   python app.py
   ```

4. **Or run with Docker:**
   ```bash
   docker-compose up --build
   ```

#### Running Tests

```bash
pipenv shell
pytest
pytest --cov=clementine  # With coverage
```

### For SREs/DevOps (Production Deployment)

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SLACK_BOT_TOKEN` | Slack bot user OAuth token | `xoxb-123-456-789` |
| `SLACK_SIGNING_SECRET` | Slack signing secret for request verification | `abc123def456` |
| `SLACK_APP_TOKEN` | Slack app-level token for Socket Mode | `xapp-1-A123-456-789` |
| `TANGERINE_API_URL` | Base URL for Tangerine API service | `https://api.tangerine.example.com` |
| `TANGERINE_API_TOKEN` | Authentication token for Tangerine API | `your-api-token` |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | Standard format | Python logging format string |
| `LOG_FILE` | (none) | Path to log file (console only if empty) |
| `BOT_NAME` | `Clementine` | Display name for the bot |
| `ASSISTANT_LIST` | `konflux` | Comma-separated list of available assistants |
| `DEFAULT_PROMPT` | Generic prompt | Default system prompt for AI responses |
| `TANGERINE_API_TIMEOUT` | `500` | API request timeout in seconds |
| `MODEL_OVERRIDE` | (none) | Override model for all Tangerine API requests (e.g., `chatgpt-4o`) |
| `ROOM_CONFIG_DB_PATH` | `room_configs.db` | Path to SQLite database file |
| `AI_DISCLOSURE_ENABLED` | `true` | Whether to show AI disclosure messages |
| `AI_DISCLOSURE_TEXT` | Standard text | Text shown in AI disclosure |
| `FEEDBACK_ENABLED` | `true` | Whether to enable user feedback buttons |
| `SLACK_MIN_CONTEXT` | `50` | Minimum number of messages for Slack context analysis |
| `SLACK_MAX_CONTEXT` | `250` | Maximum number of messages for Slack context analysis |

## Slack App Configuration

### Creating the Slack App

1. **Create a new Slack app** at https://api.slack.com/apps
2. **Configure OAuth & Permissions** with these Bot Token Scopes:
   - `app_mentions:read` - Read messages mentioning the bot
   - `channels:history` - Read channel message history
   - `channels:read` - Read channel information
   - `chat:write` - Send messages
   - `commands` - Add slash commands
   - `users:read` - Read user information for name display

3. **Enable Socket Mode:**
   - Go to Socket Mode settings
   - Enable Socket Mode
   - Generate an app-level token with `connections:write` scope
   - Save the token as `SLACK_APP_TOKEN`

4. **Configure Event Subscriptions:**
   - Enable Events
   - Subscribe to `app_mention` events

5. **Add Slash Commands:**
   - Command: `/clementine`
   - Request URL: Not needed (Socket Mode)
   - Description: "Configure bot settings and ask context questions"

6. **Install to Workspace:**
   - Install the app to your workspace
   - Copy the Bot User OAuth Token as `SLACK_BOT_TOKEN`
   - Copy the Signing Secret as `SLACK_SIGNING_SECRET`

### Permissions Required

The bot requires access to channels where it will operate. Invite the bot to channels or ensure it has appropriate permissions to read channel history.

## Deployment

### OpenShift Deployment

#### Prerequisites

- OpenShift CLI (`oc`) installed and configured
- Access to an OpenShift cluster
- Container registry with the built image

#### Build and Push Image

```bash
# Build the image
docker build -t your-registry.example.com/clementine:latest .

# Push to registry
docker push your-registry.example.com/clementine:latest
```

#### Deploy with Template

1. **Create parameters file:**
   ```bash
   cp deploy/parameters.env.example deploy/parameters.env
   ```

2. **Edit parameters file** with your configuration:
   ```bash
   # Container Image Configuration
   IMAGE=your-registry.example.com/clementine
   IMAGE_TAG=latest
   APP_NAME=clementine
   
   # Required Slack Configuration
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   SLACK_SIGNING_SECRET=your-signing-secret-here
   SLACK_APP_TOKEN=xapp-your-app-token-here
   
   # Required Tangerine API Configuration
   TANGERINE_API_URL=https://your-tangerine-api.example.com
   TANGERINE_API_TOKEN=your-tangerine-api-token-here
   
   # Optional: Model Override
   # MODEL_OVERRIDE=chatgpt-4o
   ```

3. **Deploy using the script:**
   ```bash
   cd deploy
   ./deploy.sh --namespace my-clementine-bot
   ```

   Or manually:
   ```bash
   oc process -f deploy/openshift-template.yaml --param-file=deploy/parameters.env | oc apply -f -
   ```

#### OpenShift Template Features

The template creates:
- **Secret**: Stores sensitive configuration (tokens, secrets)
- **ConfigMap**: Stores non-sensitive configuration
- **PersistentVolumeClaim**: Database storage (1Gi default)
- **Deployment**: Single replica with health checks
- **Service**: ClusterIP service (optional, for monitoring)

#### Resource Requirements

Default resource allocation:
- **Memory**: 256Mi request, 512Mi limit
- **CPU**: 100m request, 500m limit
- **Storage**: 1Gi persistent volume

Adjust in `deploy/parameters.env`:
```bash
MEMORY_LIMIT=1Gi
MEMORY_REQUEST=512Mi
CPU_LIMIT=1000m
CPU_REQUEST=200m
STORAGE_SIZE=2Gi
```

### Docker Deployment

For simple Docker deployments:

```bash
docker run -d \
  --name clementine-bot \
  --restart unless-stopped \
  -v clementine_data:/app/data \
  -e SLACK_BOT_TOKEN="xoxb-your-token" \
  -e SLACK_SIGNING_SECRET="your-secret" \
  -e SLACK_APP_TOKEN="xapp-your-token" \
  -e TANGERINE_API_URL="https://api.example.com" \
  -e TANGERINE_API_TOKEN="your-api-token" \
  -e SLACK_MIN_CONTEXT="50" \
  -e SLACK_MAX_CONTEXT="250" \
  -e MODEL_OVERRIDE="chatgpt-4o" \
  your-registry.example.com/clementine:latest
```

## Usage

### Basic Usage

1. **Mention the bot** in any channel: `@Clementine What is Kubernetes?`
2. **Configure per-channel settings**: `/clementine config`
3. **Ask about channel context**: `/clementine slack what was discussed about the API changes?`

### Channel Configuration

Each channel can have its own:
- **Assistants**: Which AI assistants to use
- **Custom Prompt**: Channel-specific system prompt
- **Slack Context Size**: Number of messages to analyze (between min/max limits)
- **Settings**: Override default bot behavior

Use `/clementine config` to open the configuration modal.

### Context Questions

The bot can analyze recent channel conversations using the `/clementine slack` command. The number of messages analyzed is configurable per channel and defaults to the minimum context size (50 messages).

Examples:
```
/clementine slack what are andrew and psav talking about re: clowder
/clementine slack summarize today's discussion about the deployment
/clementine slack what was the main decision made in this thread?
```

**Context Size Configuration:**
- Default: Uses `SLACK_MIN_CONTEXT` value (50 messages)
- Per-channel: Configure via `/clementine config` within the min/max bounds
- Global limits: Set by `SLACK_MIN_CONTEXT` and `SLACK_MAX_CONTEXT` environment variables
- Larger context provides more comprehensive analysis but may increase API usage/cost and latency

**Model Override:**
When `MODEL_OVERRIDE` is set, all API requests to Tangerine will include the specified model. This is a global setting that applies to all chat requests, including both @mentions and context analysis. Leave unset to use the Tangerine API's default model selection.

## Monitoring and Troubleshooting

### Health Checks

The application provides multiple health check mechanisms:

1. **File-based health**: Updates `/tmp/health` every 30 seconds
2. **Database connectivity**: Verifies SQLite database access
3. **Liveness/Readiness probes**: Configured in OpenShift template

### Logging

Configure logging verbosity with `LOG_LEVEL`:
- `DEBUG`: Detailed debugging information
- `INFO`: General operational messages (default)
- `WARNING`: Warning messages only
- `ERROR`: Error messages only

### Common Issues

**Bot not responding to mentions:**
- Check Slack app has `app_mentions:read` permission
- Verify bot is invited to the channel
- Check logs for authentication errors

**Context questions not working:**
- Ensure bot has `channels:history` permission
- Verify Tangerine API connectivity
- Check API timeout settings

**Database errors:**
- Verify persistent storage is writable
- Check database file permissions
- Ensure sufficient disk space

### Monitoring Commands

```bash
# Check deployment status
oc get pods -l app=clementine

# View logs
oc logs -f deployment/clementine

# Check resource usage
oc top pods -l app=clementine

# Verify configuration
oc describe configmap clementine-config
oc describe secret clementine-secrets
```

## Architecture

The bot uses Socket Mode for Slack connectivity, eliminating the need for webhook endpoints or ingress configuration. It maintains a local SQLite database for room configurations and integrates with the Tangerine API for AI responses.

Key components:
- **SlackBot**: Main application logic
- **TangerineClient**: API integration
- **RoomConfigService**: Per-channel configuration
- **FeedbackHandler**: User feedback processing
- **SlackQuestionBot**: Context analysis feature

## Security Considerations

- All sensitive configuration is stored in Kubernetes secrets
- The container runs as non-root user (UID 1001)
- Read-only root filesystem with writable data volume
- No privileged capabilities required
- Socket Mode eliminates webhook security concerns

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run the test suite: `pytest`
5. Submit a pull request

### Development Tools

- **Black**: Code formatting (`black .`)
- **Flake8**: Linting (`flake8 .`)
- **isort**: Import sorting (`isort .`)
- **pytest**: Testing framework

## Support

For issues and support:
- Check the logs for error messages
- Verify Slack app configuration
- Ensure Tangerine API connectivity
- Review resource utilization in your cluster
