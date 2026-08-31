import os
import json
import re
from app.schema import Tender
from app.config import TODAY

SYSTEM_PROMPT = f"""
You are a STRICT Procurement Auditor. Today is {TODAY}.
RULES:
1. ONLY 4 categories: Charging point operations, Solar, Bus operations (gross cost only), Bus body building.
2. Bus ops: If text says Net Cost, Net Rate, Net Revenue, set is_net_cost=true and REJECT. Only Gross Cost allowed.
3. Only OPEN tenders. If closing date before {TODAY}, is_open_now=false.
4. If you cannot find closing date, issuer, qualification, write exactly "NOT SURE". NEVER invent.
5. Output ONLY pure JSON like this: {{"tenders": [{{"title": "...", "category": "...", "closing_date": "NOT SURE", "issued_by": "...", "qualification_criteria": "...", "eligibility_status": "...", "is_net_cost": false, "is_open_now": true, "extraction_confidence": "HIGH"}}]}}
"""

def extract_json(text: str):
    try:
        text = re.sub(r'```json|```', '', text).strip()
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            return json.loads(text[start:end])
        return json.loads(text)
    except:
        return None

def heuristic_extract(raw_text: str, url: str):
    low = raw_text.lower()
    category = None
    if "charging" in low and ("point" in low or "ev" in low): category = "Charging point operations"
    elif "solar" in low: category = "Solar"
    elif "bus body" in low or "body building" in low: category = "Bus body building"
    elif "bus operat" in low or "gross cost" in low or "gcc" in low: category = "Bus operations (gross cost only)"
    
    if category:
        is_net = "net cost" in low and "gross cost" not in low
        if category == "Bus operations (gross cost only)" and is_net:
            return []
        title = raw_text[:150].split("\n")[0].strip() or f"{category} Tender"
        return [Tender(
            title=title, source_url=url, category=category,
            closing_date="NOT SURE", issued_by="NOT SURE",
            qualification_criteria="NOT SURE", eligibility_status="NOT SURE",
            is_net_cost=is_net, is_open_now=True, extraction_confidence="LOW"
        )]
    return []

def try_gemini(raw_text: str, url: str):
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key or "AIza" not in gemini_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = SYSTEM_PROMPT + f"\n\nURL: {url}\nPAGE TEXT:\n{raw_text[:7000]}"
        resp = model.generate_content(prompt)
        data = extract_json(resp.text)
        if not data: return []
        items = data.get("tenders", [])
        valid = []
        for item in items:
            try:
                t = Tender(**item, source_url=url)
                if t.category == "Bus operations (gross cost only)" and t.is_net_cost: continue
                valid.append(t)
            except: continue
        print(f"[GEMINI OK] found {len(valid)} tenders")
        return valid
    except Exception as e:
        print(f"[GEMINI FAIL] {e}")
        return None

def try_groq_dynamic(raw_text: str, url: str):
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
    if not api_key or api_key.startswith("sk-proj-..."): return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        # AUTO-DISCOVER MODELS - Never hardcode again
        models = [m.id for m in client.models.list().data]
        print(f"Available Groq models: {models[:5]}")
        # Prefer these
        preferred = [m for m in models if any(x in m for x in ["llama-3.3", "llama-3.1-8b", "gemma2", "qwen", "maverick", "scout"])]
        to_try = preferred + models
        for model in to_try[:8]:
            try:
                print(f"Trying Groq model: {model}")
                resp = client.chat.completions.create(
                    model=model, temperature=0.1,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"URL: {url}\nPAGE TEXT:\n{raw_text[:7000]}"}
                    ]
                )
                data = extract_json(resp.choices[0].message.content)
                if not data: continue
                items = data.get("tenders", [])
                valid = []
                for item in items:
                    try:
                        t = Tender(**item, source_url=url)
                        if t.category == "Bus operations (gross cost only)" and t.is_net_cost: continue
                        valid.append(t)
                    except: continue
                if valid:
                    print(f"[GROQ OK] {model} found {len(valid)}")
                    return valid
                return valid
            except Exception as e:
                print(f"[GROQ FAIL] {model}: {e}")
                continue
        return None
    except Exception as e:
        print(f"[GROQ LIST FAIL] {e}")
        return None

def audit_and_extract(raw_text: str, url: str) -> list[Tender]:
    if "SCRAPE_FAILED" in raw_text or len(raw_text) < 100:
        return []
    # 1. Try Gemini (most stable free)
    res = try_gemini(raw_text, url)
    if res is not None: return res
    # 2. Try Groq with dynamic model list
    res = try_groq_dynamic(raw_text, url)
    if res is not None: return res
    # 3. Always fallback - ensures DB never empty
    print("Using heuristic fallback - ensures dashboard not empty")
    return heuristic_extract(raw_text, url)
