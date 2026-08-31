import sys
import os
# FIX: Add project root to path so `from app.db` works on Windows + Streamlit
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
import pandas as pd
from app.db import get_all_open_tenders, get_logs, init_db

st.set_page_config(page_title="Tender Intelligence Agent - Live", layout="wide")
init_db()

st.title("Tender Intelligence Agent — Live Monitor")
st.caption("Autonomous system: Finds new, real, currently open tenders every 6 hours.")

st.sidebar.header("System Health")
logs = get_logs(5)
if logs:
    last = logs[0]
    if last.status == "FAILED":
        st.sidebar.error(f"⚠️ FAILED at {last.timestamp}\n{last.message}")
    else:
        st.sidebar.success(f"🟢 Agent Active\nLast Run: {last.timestamp}\n{last.message}")
else:
    st.sidebar.info("No runs yet. Run `python run_agent.py` once.")

tenders = get_all_open_tenders()
col1, col2, col3 = st.columns(3)
col1.metric("Active Open Tenders", len(tenders))
col2.metric("Categories Enforced", 4)
col3.metric("Last Check", logs[0].timestamp.strftime("%Y-%m-%d %H:%M") if logs else "Never")

st.subheader("Live Open Tenders")
if not tenders:
    st.warning("No open tenders in DB yet. Run `python run_agent.py` first. This page will NEVER silently show empty if agent broke - it will show FAILED in sidebar.")
else:
    df = pd.DataFrame([{
        "Title": t.title,
        "Category": t.category,
        "Closing": t.closing_date,
        "Issuer": t.issued_by,
        "Eligibility": t.eligibility_status,
        "Source": t.source_url,
        "Found": t.found_at
    } for t in tenders])
    st.dataframe(df, use_container_width=True)
    for t in tenders:
        with st.expander(f"{t.title[:80]} - {t.category}"):
            st.write(f"**Issuer:** {t.issued_by}")
            st.write(f"**Qualification:** {t.qualification_criteria}")
            st.write(f"**Link:** {t.source_url}")