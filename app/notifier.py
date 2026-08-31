import os
import requests

def send_alert(message: str):
    """If it breaks, tell us instead of showing empty page."""
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook:
        try:
            requests.post(webhook, json={"content": f"🚨 **TENDER AGENT ALERT**\n{message}"}, timeout=10)
        except Exception as e:
            print(f"Failed to send discord alert: {e}")
    
    # Always log locally
    with open("errors.alert", "a") as f:
        f.write(message + "\n")
    print(message)