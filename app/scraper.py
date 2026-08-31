import os, requests, re
from bs4 import BeautifulSoup

def fetch_via_jina(url: str) -> str:
    try:
        r = requests.get(f"https://r.jina.ai/{url}", timeout=45, headers={"X-Return-Format": "markdown"})
        if r.status_code==200 and len(r.text)>300:
            return r.text[:15000]
    except Exception as e:
        print(f"Jina fail {e}")
    return ""

def scrape_via_jina(url: str):
    text = fetch_via_jina(url)
    results=[]
    for line in text.splitlines():
        low=line.lower()
        if any(k in low for k in ["solar","bus","charging","ev","gross cost","gcc","body building","electric","e-bus"]):
            m=re.search(r'\[([^\]]+)\]\((https?://[^\)]+)\)', line)
            title, link = (m.group(1), m.group(2)) if m else (line.strip()[:250], url)
            if len(title)>20:
                results.append({"url": link, "title": title, "content": line})
    print(f"Jina {url[:45]} found {len(results)}")
    return results[:20]

def search_with_tavily_enriched(query: str, max_results=5):
    api_key=os.getenv("TAVILY_API_KEY")
    if api_key and "tvly-" in api_key:
        try:
            from tavily import TavilyClient
            res=TavilyClient(api_key=api_key).search(query, max_results=max_results, include_domains=["gov.in","gem.gov.in"])
            return [{"url": r["url"], "title": r.get("title",""), "content": r.get("content","")} for r in res.get("results",[])]
        except: pass
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results=list(ddgs.text(query, max_results=max_results))
        return [{"url": r.get("href"), "title": r.get("title",""), "content": r.get("body","")} for r in results if r.get("href") and "gov.in" in r.get("href","")]
    except Exception as e:
        print(f"DDG fail {e}"); return []
