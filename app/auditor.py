"""
Intelligent Auditor - Error-proof version
Always returns list (never crashes). Uses Groq or OpenAI dynamically.
"""
import os
import json
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotypes()

from config import CATEGORIES_ALLOWED, REJECT_NET_COST_CATEGORIES, TODAY_DATE

class IntelligentAuditor:
    def __init__(self):
        self.client = None
        self.provider = None
        self.model = None
        
        # Initialize LLM client with automatic fallback
        groq_key = os.getenv("GROQ_API_KEY")
        oai_key = os.getenv("OPENAI_API_KEY")
        
        if groq_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=groq_key)
                self.provider = "GROQ"
                # Dynamic model discovery
                self.model = self._find_working_groq_model(self.client)
                print(f"[Auditor] Using GROQ: {self.model}")
                return
            except:
                pass
                
        if oai_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=oai_key)
                self.provider = "OPENAI"
                self.model = "gpt-4o-mini"
                print(f"[Auditor] Using OPENAI fallback")
                return
            except:
                pass
        
        raise RuntimeError("""
⛔ NO AI PROVIDER AVAILABLE!
Fix: Add ONE of these to .env file:
1. GROQ_API_KEY=gsk_xxx (Free - https://console.groq.com)
2. OPENAI_API_KEY=sk-proj_xxx (Paid - https://platform.openai.com)
""")

    def _find_working_groq_model(self, client):
        """Test which model is alive today (Groq deprecates old ones often)"""
        candidates = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"]
        for m in candidates:
            try:
                client.chat.completions.create(model=m, messages=[{"role":"user","content":"ok"}], max_tokens=5)
                return m
            except:
                continue
        return candidates[0]  # Fallback anyway

    SYSTEM_PROMPT = f"""You are a Government Tender Analyst.

EXTRACT ONLY tenders matching these 4 categories:
1. Charging point operations
2. Solar
3. Bus operations (GROSS COST CONTRACT ONLY) - Reject Net Cost/L1 Net models immediately
4. Bus body building

RULES:
- Today's date: {TODAY_DATE}
- Only extract open/future tenders
- Unknown fields → write "NOT SURE" (never invent)
- Return JSON array"""

    def analyze_page(self, raw_content: str, source_url: str) -> list:
        """Analyze page text and return list of dicts. Never crashes."""
        if not raw_content or len(raw_content) < 100 or raw_content.startswith("ERROR"):
            print(f"[Audit] Skipping bad content: {raw_content[:50]}...")
            return []
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Extract from:\n{raw_content[:10000]}"}
                ],
                temperature=0.05,
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            items = result.get("tenders", result.get("results", []))
            if isinstance(result, list): items = result
            
            # Apply business rules filter
            filtered = []
            for item in items:
                cat = item.get("category","").strip()
                if cat not in CATEGORIES_ALLOWED: continue
                
                if cat in REJECT_NET_COST_CATEGORIES and item.get("is_net_cost_model"):
                    continue
                    
                # Clean up None values
                for k in ['closing_date','issued_by','qualification_criteria','eligibility_status']:
                    if not item.get(k) or str(item[k]).strip() in ['','-','N/A','None','null']:
                        item[k] = "NOT_SURE"
                
                item['source_url'] = source_url
                filtered.append(item)
            
            print(f"[Audit] ✅ Found {len(filtered)} valid tenders")
            return filtered
            
        except Exception as e:
            print(f"[Audit] ❌ Error: {e}")
            return []
