"""
Optional Discord failure notifications.
"""

import os
from datetime import datetime, timezone

import requests


def send_alert(message: str, severity: str = "ERROR"):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

    if not webhook_url:
        print("[NOTIFIER] Discord webhook not configured.")
        return

    payload = {
        "username": "Tender Intelligence Agent",
        "content": (
            f"**{severity.upper()} — Tender Intelligence Agent**\n"
            f"{message}\n"
            f"UTC: {datetime.now(timezone.utc).isoformat()}"
        ),
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=15,
        )

        if response.status_code not in {200, 204}:
            print(
                f"[NOTIFIER] Discord error {response.status_code}: "
                f"{response.text[:300]}"
            )

    except requests.RequestException as error:
        print(f"[NOTIFIER] Discord notification failed: {error}")
