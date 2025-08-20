# OpenShift Deployment

This directory contains OpenShift deployment templates and configuration for the Clementine Slack bot.

## Files

- `openshift-template.yaml` - Complete OpenShift template with all necessary resources
- `parameters.env.example` - Example parameter file for template deployment
- `README.md` - This documentation file

## Prerequisites

- OpenShift CLI (`oc`) installed and configured
- Access to an OpenShift cluster
- Container image built and pushed to a registry accessible by OpenShift
- Slack app configured with bot tokens
- Tangerine API accessible from the OpenShift cluster

## Quick Start

1. **Prepare parameters file:**
   ```bash
   cp parameters.env.example parameters.env
   # Edit parameters.env with your actual values
   ```

2. **Deploy using the template:**
   ```bash
   oc process -f openshift-template.yaml --param-file=parameters.env | oc apply -f -
   ```

3. **Monitor deployment:**
   ```bash
   oc get pods -l app=clementine
   oc logs -f deployment/clementine
   ```

## Detailed Deployment Steps

### 1. Build and Push Container Image

First, build your container image and push it to a registry:

```bash
# Build the image
docker build -t your-registry.example.com/clementine:latest .

# Push to registry
docker push your-registry.example.com/clementine:latest
```

### 2. Configure Parameters

Copy the example parameters file and update it with your configuration:

```bash
cp parameters.env.example parameters.env
```

Edit `parameters.env` and set the required values:

#### Required Parameters:
- `IMAGE` - Your container image location
- `SLACK_BOT_TOKEN` - Slack bot token (xoxb-...)
- `SLACK_SIGNING_SECRET` - Slack signing secret
- `SLACK_APP_TOKEN` - Slack app token for Socket Mode (xapp-...)
- `TANGERINE_API_URL` - Base URL for Tangerine API
- `TANGERINE_API_TOKEN` - Tangerine API authentication token

#### Optional Parameters:
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `BOT_NAME` - Display name for the bot
- `ASSISTANT_LIST` - Comma-separated list of available assistants
- Resource limits and requests
- Storage size for persistent database

### 3. Deploy to OpenShift

Deploy using the OpenShift CLI:

```bash
# Create a new project (optional)
oc new-project clementine-bot

# Process and apply the template
oc process -f openshift-template.yaml --param-file=parameters.env | oc apply -f -
```

Alternative deployment using individual parameters:

```bash
oc process -f openshift-template.yaml \
  -p IMAGE=your-registry.example.com/clementine:latest \
  -p SLACK_BOT_TOKEN=xoxb-your-token \
  -p SLACK_SIGNING_SECRET=your-secret \
  -p SLACK_APP_TOKEN=xapp-your-token \
  -p TANGERINE_API_URL=https://api.example.com \
  -p TANGERINE_API_TOKEN=your-api-token \
  | oc apply -f -
```

### 4. Verify Deployment

Check that all resources are created successfully:

```bash
# Check all resources
oc get all -l app=clementine

# Check secrets and configmaps
oc get secrets,configmaps -l app=clementine

# Check persistent volume claim
oc get pvc -l app=clementine

# View deployment status
oc rollout status deployment/clementine

# View pod logs
oc logs -f deployment/clementine
```

## Template Resources

The OpenShift template creates the following resources:

### Core Resources:
- **Deployment** - Runs the Clementine bot container
- **Secret** - Stores sensitive configuration (tokens, secrets)
- **ConfigMap** - Stores non-sensitive configuration
- **PersistentVolumeClaim** - Provides persistent storage for the SQLite database
- **Service** - Exposes the application (for monitoring, not required for Socket Mode)

### Security Features:
- Non-root container execution
- Read-only root filesystem (where possible)
- Security context with dropped capabilities
- Resource limits and requests

### Monitoring:
- Liveness and readiness probes
- Health checks for database connectivity

## Configuration

### Environment Variables

The template supports all environment variables used by the application:

#### Required:
- `SLACK_BOT_TOKEN` - Slack bot token
- `SLACK_SIGNING_SECRET` - Slack signing secret
- `SLACK_APP_TOKEN` - Slack app token for Socket Mode
- `TANGERINE_API_URL` - Tangerine API base URL
- `TANGERINE_API_TOKEN` - Tangerine API token

#### Optional (with defaults):
- `LOG_LEVEL` - Logging level (default: INFO)
- `BOT_NAME` - Bot display name (default: Clementine)
- `ASSISTANT_LIST` - Available assistants (default: konflux)
- `DEFAULT_PROMPT` - Default AI prompt
- `TANGERINE_API_TIMEOUT` - API timeout in seconds (default: 500)
- `AI_DISCLOSURE_ENABLED` - Show AI disclosure messages (default: true)
- `FEEDBACK_ENABLED` - Enable user feedback (default: true)

### Persistent Storage

The template creates a persistent volume claim for the SQLite database used by the bot. The default size is 1Gi, which can be adjusted using the `STORAGE_SIZE` parameter.

### Resource Management

Default resource configuration:
- Memory: 256Mi request, 512Mi limit
- CPU: 100m request, 500m limit

These can be adjusted using the `MEMORY_REQUEST`, `MEMORY_LIMIT`, `CPU_REQUEST`, and `CPU_LIMIT` parameters.

## Troubleshooting

### Common Issues:

1. **Pod fails to start**
   ```bash
   # Check pod events
   oc describe pod -l app=clementine
   
   # Check deployment events
   oc describe deployment clementine
   ```

2. **Database connection issues**
   ```bash
   # Check persistent volume
   oc get pvc clementine-data
   
   # Check volume mounts
   oc describe pod -l app=clementine | grep -A 10 "Mounts:"
   ```

3. **Configuration issues**
   ```bash
   # Check secrets
   oc get secret clementine-secrets -o yaml
   
   # Check configmap
   oc get configmap clementine-config -o yaml
   ```

4. **Application logs**
   ```bash
   # View recent logs
   oc logs deployment/clementine --tail=100
   
   # Follow logs in real-time
   oc logs -f deployment/clementine
   ```

### Updating Configuration:

To update configuration after deployment:

```bash
# Update the template with new parameters
oc process -f openshift-template.yaml --param-file=parameters.env | oc apply -f -

# Or update individual resources
oc edit secret clementine-secrets
oc edit configmap clementine-config

# Restart deployment to pick up changes
oc rollout restart deployment/clementine
```

## Security Considerations

- Sensitive configuration is stored in Kubernetes secrets
- Container runs as non-root user
- Resource limits prevent resource exhaustion
- Network policies can be added for additional security
- Consider using OpenShift's built-in certificate management for TLS

## Scaling

The bot is designed to run as a single instance due to:
- Socket Mode connection to Slack
- SQLite database (single-writer)
- Stateful nature of the application

If you need high availability, consider:
- Using external database instead of SQLite
- Implementing leader election for Socket Mode connections
- Setting up monitoring and automatic restarts
