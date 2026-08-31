import os
import requests
from bs4 import BeautifulSoup
import random

USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) TenderAgent/1.0"]

def fetch_text(url: str) -> str:
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script","style","nav","footer","header"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        cleaned = "\n".join([l.strip() for l in text.splitlines() if l.strip()])
        if len(cleaned) < 400:
            return f"SCRAPE_FAILED_JS: Too little text from {url}"
        return cleaned[:15000]
    except Exception as e:
        return f"SCRAPE_FAILED: {e}"

def search_free_duckduckgo(query: str, max_results=5):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [r["href"] for r in results]
    except Exception as e:
        print(f"Free search failed: {e}")
        return []

def search_with_tavily(query: str, max_results=5):
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or "tvly-" not in api_key:
        return search_free_duckduckgo(query, max_results)
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        res = client.search(query, max_results=max_results, search_depth="advanced")
        return [r["url"] for r in res.get("results", [])]
    except:
        return search_free_duckduckgo(query, max_results)