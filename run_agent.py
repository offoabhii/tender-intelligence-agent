#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs("data", exist_ok=True)

print("=== Running Agent ===")
from dotenv import load_dotenv
load_dotenv()

try:
    from config import SOURCES
    from app.scraper import fetch_tender_sources
    from app.auditor import IntelligentAuditor
    import json
    
    aud = IntelligentAuditor()
    all_items = []
    
    for src in list(SOURCES.keys())[:4]:
        print(f"Processing: {src}")
        try:
            raw = fetch_tender_sources(src)
            if raw and len(raw) > 50 and not str(raw).startswith("ERROR"):
                found = aud.analyze_page(raw, f"https://{src}.gov.in")
                if found:
                    all_items.extend(found)
                    print(f"  -> Found {len(found)}")
                else:
                    print("  -> 0 matches")
            else:
                print("  -> Empty/Error")
        except Exception as e:
            print(f"  -> Exception: {str(e)[:100]}")
    
    with open("data/live_tenders.json", "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, default=str)
        
    print(f"=== Done === Total: {len(all_items)}")
    
except Exception as e:
    print(f"PIPELINE ERROR: {e}")
    with open("data/live_tenders.json", "w") as f:
        import json
        json.dump([], f)
    print("Wrote empty JSON")

sys.exit(0)
