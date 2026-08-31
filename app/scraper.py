"""
Tavily real-web search integration.

Every result returned contains a real source URL.
This module never creates sample/fake tender data.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TAVILY_ENDPOINT = "https://api.tavily.com/search"


def fetch_tender_sources(search_query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web for current tender-related pages.

    Returns:
        [
            {
                "title": "...",
                "url": "https://real-source-url",
                "content": "content returned by Tavily"
            }
        ]
    """

    api_key = os.getenv("TAVILY_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "TAVILY_API_KEY is missing. Add it in .env and GitHub Secrets."
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
        raise RuntimeError(f"Tavily connection error: {error}") from error

    if response.status_code != 200:
        raise RuntimeError(
            f"Tavily API error {response.status_code}: {response.text[:500]}"
        )

    response_data = response.json()
    raw_results = response_data.get("results", [])

    documents = []

    for result in raw_results:
        title = str(result.get("title", "")).strip()
        url = str(result.get("url", "")).strip()

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
