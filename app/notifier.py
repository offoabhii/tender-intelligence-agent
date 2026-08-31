"""
Failure notifier.

Discord is optional. If no webhook is configured,
errors still appear in data/health.json and GitHub Actions logs.
"""

import os
from datetime import datetime, timezone

import requests


def send_alert(message: str, severity: str = "ERROR"):
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

    if not webhook:
        print("[NOTIFIER] Discord webhook not configured. Alert saved in logs only.")
        return

    payload = {
        "username": "Tender Intelligence Agent",
        "content": (
            f"**{severity.upper()} — Tender Intelligence Agent**\n"
            f"{message}\n"
            f"Time: {datetime.now(timezone.utc).isoformat()}"
        ),
    }

    try:
        response = requests.post(webhook, json=payload, timeout=15)

        if response.status_code not in {200, 204}:
            print(
                f"[NOTIFIER] Discord alert failed: "
                f"{response.status_code} {response.text[:300]}"
            )

    except requests.RequestException as error:
        print(f"[NOTIFIER] Discord notification error: {error}")
