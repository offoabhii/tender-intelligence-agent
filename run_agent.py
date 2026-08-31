"""
Main entry point for the Tender Intelligence Agent.

This file is executed by GitHub Actions:
    python run_agent.py
"""

import sys
from app.agent_runner import run_pipeline


if __name__ == "__main__":
    try:
        count = run_pipeline()

        print(f"\nPipeline completed successfully.")
        print(f"Real tenders saved: {count}")

        # Important:
        # Zero results is NOT a program crash.
        # It may simply mean no matching currently-open tenders were found.
        sys.exit(0)

    except Exception as error:
        print(f"\nPIPELINE ERROR: {error}")
        sys.exit(1)
