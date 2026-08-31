"""
Final Production Dashboard - Reads JSON committed by Actions
Guaranteed to show data if pipeline ran successfully.
"""
import streamlit as st
from datetime import datetime
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import DB module but don't rely solely on it
try:
    from app.db import init_db, get_health_status
    DB_OK = True
except:
    DB_OK = False

st.set_page_config(page_title="Tender Monitor", layout="wide")

def get_data_from_git_json():
    """
    PRIMARY DATA SOURCE: Read JSON file committed by GitHub Actions.
    This is what makes "real" data appear on Streamlit Cloud.
    """
    paths_to_check = [
        "data/live_tendors.json",   # Primary (produced by run_agent.py)
        "data/tenders.json",        # Backup name
        "live_tenders.json",        # Root level fallback
    ]
    
    for path in paths_to_check:
        full_path = os.path.join(os.getcwd(), path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        st.session_state['data_source'] = "LIVE_JSON_FROM_ACTIONS"
                        return data
            except Exception as e:
                pass
    
    # Absolute last resort: Check DB
    if DB_OK:
        try:
            init_db()
            from app.db import get_all_open_tenders
            raw = get_all_open_tenders()
            if raw and len(raw) > 0:
                rows = []
                for item in raw:
                    rows.append({
                        "Title": str(getattr(item,'title','N/A')),
                        "Category": str(getattr(item,'category','N/A')),
                        "Closing Date": str(getattr(item,'closing_date','NOT SURE')),
                        "Issuer": str(getattr(item,'issued_by','NOT SURE')),
                        "Eligibility": str(getattr(item,'eligibility_status','NOT SURE')),
                        "Qualifications": str(getattr(item,'qualification_criteria','NOT SURE')),
                        "Cost Model": "✅ GROSS SAFE" if not getattr(item,'is_net_cost',False) else "❌ NET COST REJECTED",
                        "Open Now": "🟢 Active" if getattr(item,'is_open_now',False) else "⚫ Closed",
                        "Confidence": getattr(item,'extraction_confidence','LOW'),
                        "Source": str(getattr(item,'source_url',''))[:60],
                        "Detected At": str(getattr(item,'found_at',datetime.now()))[:16]
                    })
                st.session_state['data_source'] = "DATABASE_FALLBACK"
                return rows
        except:
            pass
    
    # Nothing worked
    return []

def main():
    st.title("Tender Intelligence Agent — Live Monitor")
    st.caption(f"Autonomous Procurement System | Last Updated: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # SIDEBAR
    with st.sidebar:
        st.header("System Health")
        source_tag = st.session_state.get('data_source', 'UNKNOWN')
        
        icons = {
            "LIVE_JSON_FROM_ACTIONS": ("🟢 LIVE FEED", "Real-time scraped from government portals via GitHub Actions"),
            "DATABASE_FALLBACK": ("📦 ARCHIVE", "Database snapshot"),
            "UNKNOWN": ("⚪ INITIALIZING", "Waiting for first data ingestion...")
        }
        
        icon, desc = icons.get(source_tag, icons["UNKNOWN"])
        st.metric("Data Status", icon)
        st.caption(desc)
        
        if source_tag == "LIVE_JSON_FROM_ACTIONS":
            st.success("Agent ran successfully on GitHub servers!")
        elif source_tag == "UNKNOWN":
            st.info("Trigger manual scan:\nActions → Run Workflow")
            st.markdown("[Click here to trigger](https://github.com/offoabhii/tender-intelligence-agent/actions)")

    # MAIN CONTENT
    data = get_data_from_git_json()
    
    col1, col2, col3 = st.columns(3)
    
    total = len(data)
    open_count = sum(1 for d in data if "Active" in str(d.get('Open Now', '')))
    high_conf = sum(1 for d in data if d.get('Confidence') == 'HIGH')
    
    col1.metric("Total Found", total)
    col2.metric("Currently Biddable", open_count)
    col3.metric("High Confidence", high_conf)
    
    st.divider()
    st.subheader("Live Opportunities")
    
    if data:
        # Category Filter
        cats = sorted(list(set([d['Category'] for d in data])))
        selected = st.multiselect("Filter:", options=cats, default=cats)
        filtered = [d for d in data if d['Category'] in selected]
        
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        
        # Export
        csv_data = "|".join(["Title","Category","Closing","Cost Model"])+ "\n" + "\n".join([f"{d['Title']}|{d['Category']}|{d['Closing Date']}|{d['Cost Model']}" for d in filtered])
        st.download_button("Export CSV", csv_data.encode(), "tenders.csv", "text/csv")
    else:
        st.error("No data found yet.")
        st.markdown("""### To populate:
        1. Go to [GitHub Actions](https://github.com/offoabhii/tender-intelligence-agent/actions)
        2. Click 'Tender Agent Auto-Run'
        3. Click 'Run workflow'
        4. Refresh this page in 90 seconds""")

if __name__ == "__main__":
    main()
