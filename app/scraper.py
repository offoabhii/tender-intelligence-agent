"""
Real web search layer using Tavily.

This does not invent tender links.
Every result includes a real source URL returned by Tavily.
"""

import os
from dotenv import load_dotenv
import requests

load_dotenv()

TAVILY_ENDPOINT = "https://api.tavily.com/search"


def fetch_tender_sources(search_query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web for real tender pages.

    Returns:
        [
            {
                "title": "...",
                "url": "https://actual-source-url",
                "content": "actual search/page content"
            }
        ]

    Raises RuntimeError for API/network failures.
    """

    api_key = os.getenv("TAVILY_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "TAVILY_API_KEY is missing. Add it locally in .env and "
            "in GitHub Actions Secrets."
        )

    payload = {
        "api_key": api_key,
        "query": search_query,
        "search_depth": "advanced",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": True,
        "include_images": False,
    }

    try:
        response = requests.post(
            TAVILY_ENDPOINT,
            json=payload,
            timeout=45,
        )
    except requests.RequestException as error:
        raise RuntimeError(f"Tavily connection failure: {error}") from error

    if response.status_code != 200:
        raise RuntimeError(
            f"Tavily API error {response.status_code}: {response.text[:500]}"
        )

    body = response.json()
    results = body.get("results", [])

    documents = []

    for result in results:
        url = str(result.get("url", "")).strip()
        title = str(result.get("title", "")).strip()

        # Tavily can return content or raw_content depending on its response.
        content = (
            result.get("raw_content")
            or result.get("content")
            or ""
        )

        content = str(content).strip()

        if not url or not content:
            continue

        documents.append(
            {
                "title": title,
                "url": url,
                "content": content[:14000],
            }
        )

    return documents
