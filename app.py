from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
import requests
import os
import uuid
from dotenv import load_dotenv

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

TANGERINE_CHAT_API_URL = TANGERINE_API_URL + "/api/assistants/chat"

# Initialize the Slack app
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

@app.event("app_mention")
def handle_mention(event, say, client):
    user_msg = event["text"]
    session_id = event["user"]
    interaction_id = str(uuid.uuid4())
    thread_ts = event.get("thread_ts", event["ts"])

    # 1. Post temporary loading message
    try:
        loading = client.chat_postMessage(
            channel=event["channel"],
            text=":hourglass_flowing_sand: Thinking...",
            thread_ts=thread_ts
        )
        loading_ts = loading["ts"]
    except SlackApiError as e:
        print(f"⚠️ Failed to post loading message: {e}")
        return

    # 2. Prepare the payload for Tangerine
    payload = {
        "assistants": ASSISTANT_LIST,
        "query": user_msg,
        "sessionId": session_id,
        "interactionId": interaction_id,
        "client": BOT_NAME,
        "stream": False,
        "prompt": DEFAULT_PROMPT
    }

    try:
        response = requests.post(
            TANGERINE_CHAT_API_URL,
            headers={
                "Authorization": f"Bearer {TANGERINE_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=TANGERINE_API_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()

        text = data.get("text_content", "(No response from assistant)").strip()
        metadata = data.get("search_metadata", [])

        if metadata:
            sources = metadata[:3]
            links = "\n".join(
                f"<{m['metadata']['citation_url']}|{m['metadata']['title']}>"
                for m in sources
                if m.get("metadata", {}).get("citation_url")
            )
            if links:
                text += "\n\n*Sources:*\n" + links

        # 3. Update the placeholder message with the real content
        client.chat_update(
            channel=event["channel"],
            ts=loading_ts,
            text=text
        )

    except Exception as e:
        error_msg = f"Oops, {BOT_NAME} hit a snag: `{e}`"
        print(error_msg)

        # Replace loading message with error message
        client.chat_update(
            channel=event["channel"],
            ts=loading_ts,
            text=error_msg
        )

# Start the app using Socket Mode
if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()