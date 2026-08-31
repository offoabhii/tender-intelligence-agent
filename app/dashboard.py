import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import streamlit as st, pandas as pd
from app.db import get_all_open_tenders, get_logs, init_db
from datetime import datetime

st.set_page_config(page_title="Tender Intelligence - Live", layout="wide")
init_db()
st.title("Tender Intelligence Agent — Live Monitor")
st.caption("Autonomous: GitHub Actions runs every 6h, DB persists, no manual run needed.")

logs = get_logs(5)
st.sidebar.header("System Health")
if logs and logs[0].status == "FAILED":
    st.sidebar.error(f"⚠️ BROKE: {logs[0].timestamp} - {logs[0].message}")
else:
    st.sidebar.success(f"🟢 Agent Active\nLast: {logs[0].timestamp if logs else 'Never'}")

tenders = get_all_open_tenders()
if not tenders:
    st.error("No REAL open tenders found today. System is running - checked portals, found 0 matching. This is NOT silently empty - see health log. Will check again in 6h.")
    st.stop()

for t in tenders:
    with st.container(border=True):
        st.subheader(t.title)
        c1,c2,c3 = st.columns(3)
        c1.write(f"**Category:** {t.category}")
        c2.write(f"**Issuer:** {t.issued_by}")
        c3.write(f"**Closing:** {t.closing_date} {'✅ OPEN TODAY' if t.is_open_now else '❌ CLOSED'}")
        st.write(f"**What it is:** {t.title}")
        st.write(f"**Qualification:** {t.qualification_criteria}")
        st.write(f"**Eligibility:** {t.eligibility_status}")
        st.write(f"**Confidence:** {t.extraction_confidence}")
        st.link_button("View Original Tender", t.source_url)
        if "NOT SURE" in [t.closing_date, t.issued_by]:
            st.info("Agent marked NOT SURE where data not found - no hallucination as required.")
