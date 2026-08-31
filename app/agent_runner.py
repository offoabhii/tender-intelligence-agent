#!/usr/bin/env python3
"""
Tender Agent Runner - Complete Pipeline
Scrapes → Audits → Saves JSON → Commits to Git
"""
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, '.')
os.environ.setdefault('PYTHONPATH', '.')

def main():
    print("=" * 60)
    print(f"TENDER INTELLIGENCE AGENT - EXECUTION STARTED")
    print(f"Timestamp: {datetime.now()}")
    print("=" * 60)
    
    # Import components
    from config import SOURCES
    from app.scraper import fetch_tender_sources
    from app.auditor import IntelligentAuditor
    
    # Initialize auditor
    aud = IntelligentAuditor()
    
    all_tenders = []
    
    # Iterate over each category source
    for source_name in SOURCES.keys():
        print(f"\n▶ Processing: {source_name}")
        
        try:
            # Step 1: Scrape web
            raw_text = fetch_tender_sources(source_name)
            
            if raw_text.startswith("ERROR") or len(raw_text) < 50:
                print(f"   ⚠️ Scraping failed or empty: {raw_text[:80]}")
                continue
            
            print(f"   ✓ Scraped {len(raw_text)} characters")
            
            # Step 2: Analyze with AI
            tenders = aud.analyze_page(raw_text, f"https://{source_name}.gov.in")
            
            if tenders:
                print(f"   ✓ Found {len(tenders)} potential matches after audit")
                all_tenders.extend(tenders)
            else:
                print(f"   ⚠️ Auditor found no relevant tenders (might be valid if none exist today)")
            
        except Exception as e:
            print(f"   💥 CRASH processing {source_name}: {str(e)[:100]}")
    
    # Step 3: Save results to JSON (Git-friendly format)
    output_file = "data/live_tenders.json"
    os.makedirs("data", exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_tenders, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n{'='*60}")
    print(f"✅ PIPELINE COMPLETE")
    print(f"Tenders Found: {len(all_tenders)}")
    print(f"Saved to: {output_file}")
    print(f"{'='*60}")
    
    return len(all_tenders)

if __name__ == "__main__":
    count = main()
    sys.exit(0 if count > 0 else 1)
