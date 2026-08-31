import os, requests, random
from bs4 import BeautifulSoup
USER_AGENTS = ["Mozilla/5.0 TenderAgent/1.0"]

def fetch_text(url: str) -> str:
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        resp = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script","style","nav","footer","header"]): tag.decompose()
        text = "\n".join([l.strip() for l in soup.get_text("\n").splitlines() if l.strip()])
        if len(text) < 200: return f"SCRAPE_FAILED_JS: {text[:200]}"
        return text[:15000]
    except Exception as e:
        return f"SCRAPE_FAILED: {e}"

def search_free_duckduckgo_enriched(query: str, max_results=5):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [{"url": r.get("href"), "title": r.get("title",""), "content": r.get("body","")} for r in results if r.get("href")]
    except Exception as e:
        print(f"DDG fail: {e}"); return []

def search_with_tavily_enriched(query: str, max_results=5):
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or "tvly-" not in api_key:
        return search_free_duckduckgo_enriched(query, max_results)
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        res = client.search(query, max_results=max_results, search_depth="advanced", include_domains=["gov.in","gem.gov.in"])
        return [{"url": r["url"], "title": r.get("title",""), "content": r.get("content","")} for r in res.get("results",[])]
    except:
        return search_free_duckduckgo_enriched(query, max_results)

def scrape_etenders_direct():
    """REAL HTML - no JS - always works"""
    url = "https://etenders.gov.in/eprocure/app?page=FrontEndLatestActiveTenders&service=page"
    try:
        r = requests.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=30)
        soup = BeautifulSoup(r.text, "lxml")
        results=[]
        for tr in soup.find_all("tr"):
            txt = tr.get_text(" ", strip=True)
            if len(txt)<40: continue
            low=txt.lower()
            if any(k in low for k in ["solar","bus","charging","ev","gross cost","body building","electric"]):
                a=tr.find("a", href=True)
                link=a["href"] if a else url
                if link.startswith("/"): link="https://etenders.gov.in"+link
                if not link.startswith("http"): link=url
                results.append({"url": link, "title": txt[:250], "content": txt})
        print(f"etenders found {len(results)}")
        return results[:20]
    except Exception as e:
        print(f"etenders fail {e}"); return []

def scrape_cppp_direct():
    url = "https://eprocure.gov.in/cppp/latestactivetenders"
    try:
        r = requests.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=30)
        soup = BeautifulSoup(r.text, "lxml")
        results=[]
        for tr in soup.find_all("tr"):
            txt=tr.get_text(" ", strip=True)
            if len(txt)>40 and any(k in txt.lower() for k in ["solar","bus","charging","ev","gross cost","body building"]):
                a=tr.find("a", href=True)
                link=a["href"] if a else url
                if link.startswith("/"): link="https://eprocure.gov.in"+link
                results.append({"url": link, "title": txt[:250], "content": txt})
        print(f"cppp found {len(results)}")
        return results[:20]
    except Exception as e:
        print(f"cppp fail {e}"); return []
