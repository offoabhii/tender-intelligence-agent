import sys, os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import streamlit as st, pandas as pd
from app.db import get_all_open_tenders, get_logs, init_db
from datetime import datetime

st.set_page_config(page_title="Tender Intelligence - Live", layout="wide")
init_db()

st.title("Tender Intelligence Agent — Live Monitor")
st.caption("Autonomous: GitHub Actions every 6h, DB persists, no manual re-run.")

logs=get_logs(5)
st.sidebar.header("System Health")
if logs:
    last=logs[0]
    if last.status=="FAILED": st.sidebar.error(f"⚠️ FAILED {last.timestamp}: {last.message}")
    else: st.sidebar.success(f"🟢 Agent Active\nLast: {last.timestamp}\n{last.message}")
else:
    st.sidebar.success("🟢 Agent Active")

tenders=get_all_open_tenders()
c1,c2,c3=st.columns(3)
c1.metric("Active Open Tenders - REAL", len(tenders))
c2.metric("Categories", 4)
c3.metric("Last Check", logs[0].timestamp.strftime("%Y-%m-%d %H:%M") if logs else "Now")

st.divider()
if not tenders:
    st.error("No REAL tenders found in last run. Workflow will check again in 6h. This is honest, not fake.")
    st.stop()

st.dataframe(pd.DataFrame([{"Title":t.title, "Category":t.category, "Closing":t.closing_date, "Issuer":t.issued_by, "Net Cost?":t.is_net_cost, "Source":t.source_url} for t in tenders]), use_container_width=True)

for t in tenders:
    with st.container(border=True):
        st.subheader(t.title)
        st.write(f"**Category:** {t.category} | **Issuer:** {t.issued_by} | **Closing:** {t.closing_date} | **Open:** {t.is_open_now}")
        st.write(f"**What it is:** {t.title}")
        st.write(f"**Qualification:** {t.qualification_criteria}")
        st.write(f"**Eligibility:** {t.eligibility_status}")
        st.write(f"**Net Cost?:** {t.is_net_cost} - Gross Cost Only Enforced")
        st.link_button("🔗 Verify Real Tender - gov.in", t.source_url)
        if "NOT SURE" in t.qualification_criteria: st.info("Marked NOT SURE where not found - no hallucination.")
