import os, json, re
from app.schema import Tender
SYSTEM_PROMPT = "You are STRICT auditor. ONLY 4 cats: Charging point operations, Solar, Bus operations (gross cost only), Bus body building. Net Cost bus -> REJECT. If not found write NOT SURE."

def heuristic_from_search(result: dict):
    low=(result.get("title","")+result.get("content","")).lower()
    cat=None
    if "charging" in low and ("point" in low or "ev" in low): cat="Charging point operations"
    elif "solar" in low: cat="Solar"
    elif "bus body" in low or "body building" in low: cat="Bus body building"
    elif "bus operat" in low or "gross cost" in low or "gcc" in low or "electric bus" in low: cat="Bus operations (gross cost only)"
    if not cat: return []
    is_net="net cost" in low and "gross cost" not in low
    if cat=="Bus operations (gross cost only)" and is_net: return []
    title=result.get("title") or low[:120]
    return [Tender(title=title[:200], source_url=result["url"], category=cat, closing_date="NOT SURE", issued_by="NOT SURE", qualification_criteria="NOT SURE", eligibility_status="NOT SURE", is_net_cost=is_net, is_open_now=True, extraction_confidence="MEDIUM")]

def audit_and_extract(raw_text: str, url: str):
    if "SCRAPE_FAILED" in raw_text and len(raw_text)<500: return []
    gem_key=os.getenv("GEMINI_API_KEY")
    if gem_key and "AIza" in gem_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gem_key)
            model=genai.GenerativeModel("gemini-1.5-flash")
            resp=model.generate_content(f"{SYSTEM_PROMPT}\nURL:{url}\nTEXT:\n{raw_text[:7000]}\nReturn JSON {{\"tenders\": [{{\"title\":\"\",\"category\":\"\",\"closing_date\":\"NOT SURE\",\"issued_by\":\"\",\"qualification_criteria\":\"\",\"eligibility_status\":\"\",\"is_net_cost\":false,\"is_open_now\":true,\"extraction_confidence\":\"HIGH\"}}]}}")
            txt=re.sub(r'```json|```','',resp.text).strip()
            data=json.loads(txt[txt.find('{'):txt.rfind('}')+1])
            valid=[]
            for item in data.get("tenders",[]):
                try:
                    t=Tender(**item, source_url=url)
                    if t.category=="Bus operations (gross cost only)" and t.is_net_cost: continue
                    valid.append(t)
                except: continue
            if valid: return valid
        except Exception as e: print(f"Gemini fail {e}")
    return []
