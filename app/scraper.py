import os, requests, random
from bs4 import BeautifulSoup

USER_AGENTS = ["Mozilla/5.0 TenderAgent/1.0"]

def fetch_text(url: str) -> str:
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script","style","nav","footer","header"]): tag.decompose()
        text = soup.get_text(separator="\n")
        cleaned = "\n".join([l.strip() for l in text.splitlines() if l.strip()])
        if len(cleaned) < 400: return f"SCRAPE_FAILED_JS: {cleaned[:200]}"
        return cleaned[:15000]
    except Exception as e:
        return f"SCRAPE_FAILED: {e}"

def search_free_duckduckgo_enriched(query: str, max_results=5):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        # return dicts with url, title, content
        return [{"url": r.get("href"), "title": r.get("title"), "content": r.get("body","")} for r in results]
    except Exception as e:
        print(f"DDG fail: {e}"); return []

def search_with_tavily_enriched(query: str, max_results=5):
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or "tvly-" not in api_key:
        return search_free_duckduckgo_enriched(query, max_results)
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        res = client.search(query, max_results=max_results, search_depth="advanced", include_answer=True, include_domains=["gov.in","gem.gov.in"])
        return [{"url": r["url"], "title": r.get("title",""), "content": r.get("content","")} for r in res.get("results",[])]
    except Exception as e:
        print(f"Tavily fail {e}, fallback DDG")
        return search_free_duckduckgo_enriched(query, max_results)

# keep old names for compatibility
def search_with_tavily(q, max_results=5):
    return [r["url"] for r in search_with_tavily_enriched(q, max_results)]
