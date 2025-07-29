from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

# Load config from environment
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
BOT_NAME = os.getenv("BOT_NAME", "Clementine")
ASSISTANT_LIST = os.getenv("ASSISTANT_LIST", "support docs,knowledge base").split(",")
DEFAULT_PROMPT = os.getenv("DEFAULT_PROMPT", "You are a helpful assistant.")
TANGERINE_API_URL = os.getenv("TANGERINE_API_URL")
TANGERINE_API_TOKEN = os.getenv("TANGERINE_API_TOKEN")

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)


@app.event("app_mention")
def handle_mention(event, say):
    user_msg = event["text"]
    session_id = event["user"]
    interaction_id = str(uuid.uuid4())
    thread_ts = event.get("thread_ts", event["ts"])

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
            TANGERINE_API_URL,
            headers={
                "Authorization": f"Bearer {TANGERINE_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        text = data.get("text_content", "(No response from assistant)").strip()
        metadata = data.get("search_metadata", [])

        if metadata:
            sources = metadata[:3]  # Limit to 3 sources
            links = "\n".join(
                f"<{m['metadata']['citation_url']}|{m['metadata']['title']}>"
                for m in sources
                if m.get("metadata", {}).get("citation_url")
            )
            if links:
                text += "\n\n*Sources:*\n" + links

        say(text, thread_ts=thread_ts)

    except Exception as e:
        error_message = f"Oops, {BOT_NAME} hit a snag: `{e}`"
        say(error_message, thread_ts=thread_ts)


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_BOT_TOKEN).start()