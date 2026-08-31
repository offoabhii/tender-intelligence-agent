"""
Main entry point.

Local:
    python run_agent.py

GitHub Actions:
    python run_agent.py
"""

import sys

from app.agent_runner import run_pipeline


if __name__ == "__main__":
    try:
        count = run_pipeline()

        print(f"\nPipeline complete. Tender count: {count}")

        # Zero tenders is not a code failure.
        sys.exit(0)

    except Exception as error:
        print(f"\nPIPELINE FAILED: {error}")
        sys.exit(1)
