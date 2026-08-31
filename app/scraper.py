"""
Guaranteed Scraper v3 - Uses Tavily Search API exclusively
Falls back to direct HTTP only if Tavily fails completely.
"""
import os
import requests
import json
from dotenv import load_dotenv
load_dotenv()

def fetch_tender_sources(source_name):
    """
    Robust scraper. Tries Tavily first (renders JS sites), then direct HTTP.
    Always returns text string (never crashes).
    """
    
    # Get TAVILY KEY
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    # Map source names to actual search queries
    queries = {
        "charging": "site:nic.in OR site:gem.gov.in electric vehicle charging station O&M operation tender 2025 status:Open",
        "solar": "site:mnre.gov.in OR site:nredcap.in solar rooftop installation tender 2025 open",
        "bus_ops": "site:etender.hry.nic.in OR site:tendernotice.com bus operations gross cost contract 2025 open",  
        "bus_body": "site:cppt.goa.gov.in OR site:tenders.gov.in bus body building fabrication 2025"
    }
    
    query = queries.get(source_name, f"{source_name} government tender open 2025")
    
    print(f"[Scrape] Starting: {source_name}")
    
    # METHOD 1: TAVILY PREFERRED (Handles JavaScript portals)
    if tavily_key:
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": 5,
                    "include_answer": False,
                    "include_raw_content": True,
                    "include_images": False
                },
                timeout=30
            )
            
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                
                if len(results) > 0:
                    combined = []
                    for r in results:
                        title = r.get("title", "")
                        url = r.get("url", "")
                        content = r.get("content", "") # This is rendered page text!
                        
                        entry = f"""
SOURCE: {title}
URL: {url}
---
{content}
"""
                        combined.append(entry)
                    
                    final_text = "\n\n".join(combined)
                    print(f"[Scrape] ✅ SUCCESS via Tavily: {len(final_text)} chars from {len(results)} sources")
                    return final_text
                else:
                    print(f"[Scrape] ⚠️ Tavily returned 0 results for query")
                    
            else:
                print(f"[Scrape] ❌ Tavily error: {resp.status_code}")
                
        except Exception as e:
            print(f"[Scrape] ❌ Tavily exception: {e}")
    
    # METHOD 2: Direct URL Fetch (Fallback)
    print(f"[Scrape] Trying direct URL fetch fallback...")
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        # If input looks like URL use directly, else skip
        if source_name.startswith("http"):
            url_to_fetch = source_name
        else:
            # Try constructing common portal URLs
            urls_map = {
                "charging": "https://gem.gov.in/search?q=charging+station+tender+status:Open&type:TENDER",
                "solar": "https://mnre.gov.in/en/tenders?type=open",
                "bus_ops": "https://etender.hry.nic.in/nicgep/app?page=list_tender_notice",
                "bus_body": "https://acma.goa.gov.in/TenderNotice.aspx"
            }
            url_to_fetch = urls_map.get(source_name, "")
            
        if not url_to_fetch:
            return "ERROR: No URL available for direct fetch"
            
        resp = requests.get(url_to_fetch, headers=headers, timeout=20)
        
        if resp.status_code == 200 and len(resp.text) > 500:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'lxml')
            for tag in soup(['script','style','nav','footer','header']):
                tag.decompose()
            text = soup.get_text(separator='\n', strip=True)[:12000]
            print(f"[Scrape] ✅ Direct fetch OK: {len(text)} chars")
            return text
        else:
            return f"ERROR: Direct fetch short/failed ({resp.status_code})"
            
    except Exception as e:
        return f"ERROR: All scraping methods failed: {str(e)}"
