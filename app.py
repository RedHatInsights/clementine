from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
from dotenv import load_dotenv
from clementine import TangerineClient, ClementineBot

load_dotenv()

# Load config from environment
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")  # xoxb-...
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")  # xapp-...

BOT_NAME = os.getenv("BOT_NAME", "Clementine")
ASSISTANT_LIST = os.getenv("ASSISTANT_LIST", "konflux").split(",")
DEFAULT_PROMPT = os.getenv("DEFAULT_PROMPT", "You are a helpful assistant.")
TANGERINE_API_URL = os.getenv("TANGERINE_API_URL")
TANGERINE_API_TOKEN = os.getenv("TANGERINE_API_TOKEN")
TANGERINE_API_TIMEOUT = int(os.getenv("TANGERINE_API_TIMEOUT", 500))

# Initialize the Slack app
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

# Initialize the bot components
tangerine_client = TangerineClient(
    api_url=TANGERINE_API_URL,
    api_token=TANGERINE_API_TOKEN,
    timeout=TANGERINE_API_TIMEOUT
)

clementine_bot = ClementineBot(
    tangerine_client=tangerine_client,
    bot_name=BOT_NAME,
    assistant_list=ASSISTANT_LIST,
    default_prompt=DEFAULT_PROMPT
)

@app.event("app_mention")
def handle_mention(event, say, client):
    """Handle app mentions by delegating to the ClementineBot."""
    clementine_bot.handle_mention(event, client)

# Start the app using Socket Mode
if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()