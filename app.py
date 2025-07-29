from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
import logging
import logging.config
from dotenv import load_dotenv
from clementine import TangerineClient, ClementineBot, SlackClient

load_dotenv()

# Configure logging
def setup_logging():
    """Configure logging with appropriate levels and formatting."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.StreamHandler(),  # Console output
            # Add file handler if LOG_FILE is specified
            *([logging.FileHandler(os.getenv("LOG_FILE"))] if os.getenv("LOG_FILE") else [])
        ]
    )
    
    # Set specific loggers to appropriate levels
    logging.getLogger("slack_bolt").setLevel(logging.WARNING)  # Reduce slack_bolt noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)     # Reduce HTTP noise
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configured - Level: %s", log_level)
    return logger

logger = setup_logging()
# Load config from environment
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")  # xoxb-...
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")  # xapp-...

BOT_NAME = os.getenv("BOT_NAME", "Clementine")
ASSISTANT_LIST = os.getenv("ASSISTANT_LIST", "konflux").split(",")
DEFAULT_PROMPT = os.getenv("DEFAULT_PROMPT", "You are a helpful assistant.")
TANGERINE_API_URL = os.getenv("TANGERINE_API_URL")
TANGERINE_API_TOKEN = os.getenv("TANGERINE_API_TOKEN")

# Validate timeout value with proper error handling
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

TANGERINE_API_TIMEOUT = get_timeout_value()
logger.info("Using Tangerine API timeout: %d seconds", TANGERINE_API_TIMEOUT)

# Initialize the Slack app
logger.info("Initializing Slack app")
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

# Initialize the bot components
logger.info("Initializing bot components")
tangerine_client = TangerineClient(
    api_url=TANGERINE_API_URL,
    api_token=TANGERINE_API_TOKEN,
    timeout=TANGERINE_API_TIMEOUT
)

slack_client = SlackClient(app.client)

clementine_bot = ClementineBot(
    tangerine_client=tangerine_client,
    slack_client=slack_client,
    bot_name=BOT_NAME,
    assistant_list=ASSISTANT_LIST,
    default_prompt=DEFAULT_PROMPT
)

logger.info("Bot '%s' initialized with assistants: %s", BOT_NAME, ASSISTANT_LIST)

@app.event("app_mention")
def handle_mention(event, say, client):
    """Handle app mentions by delegating to the ClementineBot."""
    logger.debug("Received app mention from user %s in channel %s", 
                event.get('user'), event.get('channel'))
    clementine_bot.handle_mention(event, client)

# Start the app using Socket Mode
if __name__ == "__main__":
    logger.info("Starting %s bot in Socket Mode", BOT_NAME)
    try:
        SocketModeHandler(app, SLACK_APP_TOKEN).start()
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.exception("Fatal error starting bot: %s", e)
        raise