import os, json, re
from app.schema import Tender
from app.config import TODAY

SYSTEM_PROMPT = f"""You are STRICT Procurement Auditor. Today is {TODAY}.
ONLY 4 categories: Charging point operations, Solar, Bus operations (gross cost only), Bus body building.
Bus ops: Net Cost/Net Rate -> is_net_cost=true REJECT. Only Gross Cost allowed.
If closing date not found write NOT SURE. Never invent.
Return JSON: {{"tenders": [{{"title": "...", "category": "...", "closing_date": "NOT SURE", "issued_by": "...", "qualification_criteria": "...", "eligibility_status": "...", "is_net_cost": false, "is_open_now": true, "extraction_confidence": "HIGH"}}]}}"""

def extract_json(text: str):
    try:
        text = re.sub(r'```json|```','',text).strip()
        s=text.find('{'); e=text.rfind('}')+1
        if s!=-1 and e!=-1: return json.loads(text[s:e])
        return json.loads(text)
    except: return None

def heuristic_from_search(result: dict):
    low = (result.get("title","")+result.get("content","")).lower()
    cat=None
    if "charging" in low and ("point" in low or "ev" in low): cat="Charging point operations"
    elif "solar" in low: cat="Solar"
    elif "bus body" in low or "body building" in low: cat="Bus body building"
    elif "bus operat" in low or "gross cost" in low or "gcc" in low: cat="Bus operations (gross cost only)"
    if not cat: return []
    is_net = "net cost" in low and "gross cost" not in low
    if cat=="Bus operations (gross cost only)" and is_net: return []
    title = result.get("title") or low[:100]
    return [Tender(title=title[:200], source_url=result["url"], category=cat, closing_date="NOT SURE", issued_by="NOT SURE", qualification_criteria="NOT SURE", eligibility_status="NOT SURE", is_net_cost=is_net, is_open_now=True, extraction_confidence="MEDIUM")]

def audit_and_extract(raw_text: str, url: str) -> list[Tender]:
    if "SCRAPE_FAILED" in raw_text and len(raw_text)<500:
        # will be handled by heuristic_from_search in runner
        return []
    # Try Gemini first - most stable free
    gem_key=os.getenv("GEMINI_API_KEY")
    if gem_key and "AIza" in gem_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gem_key)
            model=genai.GenerativeModel("gemini-1.5-flash")
            resp=model.generate_content(SYSTEM_PROMPT+f"\nURL:{url}\nTEXT:\n{raw_text[:7000]}")
            data=extract_json(resp.text)
            if data:
                valid=[]
                for item in data.get("tenders",[]):
                    try:
                        t=Tender(**item, source_url=url)
                        if t.category=="Bus operations (gross cost only)" and t.is_net_cost: continue
                        valid.append(t)
                    except: continue
                if valid: 
                    print(f"[GEMINI OK] {len(valid)}"); return valid
        except Exception as e: print(f"[GEMINI FAIL] {e}")
    # Fallback heuristic from raw_text
    low=raw_text.lower()
    cat=None
    if "charging" in low: cat="Charging point operations"
    elif "solar" in low: cat="Solar"
    elif "bus body" in low: cat="Bus body building"
    elif "bus operat" in low: cat="Bus operations (gross cost only)"
    if cat:
        return [Tender(title=raw_text[:120].split("\n")[0], source_url=url, category=cat, closing_date="NOT SURE", issued_by="NOT SURE", qualification_criteria="NOT SURE", eligibility_status="NOT SURE", is_net_cost=False, is_open_now=True, extraction_confidence="LOW")]
    return []
