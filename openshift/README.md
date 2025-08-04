# Clementine Slack Bot - OpenShift Deployment

Simple OpenShift deployment for the Clementine Slack bot.

## 📁 What's Included

- **`clementine-template.yaml`** - OpenShift template with all resources
- **`parameters.env`** - Example parameters file
- **`README.md`** - This guide

## 🏗️ What Gets Deployed

- **Deployment** - The bot application
- **Service** - For health checks  
- **ConfigMap** - Non-sensitive configuration
- **PersistentVolumeClaim** - Storage for application data

## 🚀 How to Deploy

### 1. Create Your Parameters File

Copy and edit the parameters file:

```bash
cp parameters.env my-parameters.env
```

Edit `my-parameters.env` with your values:

```bash
# Required - Your vault system will fill these
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-secret  
SLACK_APP_TOKEN=xapp-your-token
TANGERINE_API_URL=https://your-api.com
TANGERINE_API_TOKEN=your-token

# Optional - Customize as needed
NAMESPACE=my-project
BOT_NAME=Clementine
ASSISTANT_LIST=konflux
```

### 2. Deploy to OpenShift

```bash
# Create project (if it doesn't exist)
oc new-project my-project

# Process and apply template
oc process -f clementine-template.yaml \
  --param-file=my-parameters.env | \
  oc apply -f -
```

### 3. Check Status

```bash
# View all resources
oc get all -l app=clementine-slack-bot

# Watch logs
oc logs -f deployment/clementine-slack-bot

# Check pod status
oc get pods -l app=clementine-slack-bot
```

## 🔧 Configuration

### Environment Variables

The template accepts these parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `SLACK_BOT_TOKEN` | Slack bot token | Required |
| `SLACK_SIGNING_SECRET` | Slack signing secret | Required |
| `SLACK_APP_TOKEN` | Slack app token | Required |
| `TANGERINE_API_URL` | Tangerine API URL | Required |
| `TANGERINE_API_TOKEN` | Tangerine API token | Required |
| `BOT_NAME` | Bot display name | Clementine |
| `ASSISTANT_LIST` | Available assistants | konflux |
| `LOG_LEVEL` | Logging level | INFO |
| `MEMORY_LIMIT` | Memory limit | 512Mi |
| `CPU_LIMIT` | CPU limit | 500m |

### Updating Configuration

```bash
# Update ConfigMap
oc edit configmap clementine-slack-bot-config

# Restart to pick up changes
oc rollout restart deployment/clementine-slack-bot
```

## 🔒 Security

The deployment includes basic security:

- **Non-root user** (UID 1001)
- **Security context** with dropped capabilities
- **Resource limits** to prevent resource exhaustion
- **Health checks** for reliability

## 🐛 Troubleshooting

### Pod Won't Start

```bash
# Check pod events
oc describe pod -l app=clementine-slack-bot

# Check logs
oc logs -l app=clementine-slack-bot
```

### Bot Not Responding

1. Check if pod is running: `oc get pods`
2. Check logs for errors: `oc logs deployment/clementine-slack-bot`
3. Verify environment variables: `oc set env deployment/clementine-slack-bot --list`

### Resource Issues

```bash
# Check resource usage
oc top pods -l app=clementine-slack-bot

# Check resource limits
oc describe pod -l app=clementine-slack-bot | grep -A 5 "Limits\|Requests"
```

## 🔄 Updates

To update the bot:

```bash
# If using a new image
oc set image deployment/clementine-slack-bot clementine-bot=your-registry/clementine-slack-bot:new-tag

# Check rollout status
oc rollout status deployment/clementine-slack-bot
```

## 💾 Data Storage

The bot uses a persistent volume for data storage at `/app/data`. Logs are handled automatically by your cluster's logging system.

---

That's it! Keep it simple, keep it working. 🎯 