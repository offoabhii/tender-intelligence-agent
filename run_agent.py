"""
GitHub Actions entry point.

Run locally:
    python run_agent.py
"""

import sys

from app.agent_runner import run_pipeline


if __name__ == "__main__":
    try:
        total = run_pipeline()
        print(f"\nPipeline finished. Verified tender count: {total}")

        # A zero result is a valid successful scan.
        sys.exit(0)

    except Exception as error:
        print(f"\nPIPELINE FAILED: {error}")
        sys.exit(1)
