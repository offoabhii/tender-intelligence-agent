import sys,os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
if ROOT not in sys.path: sys.path.insert(0,ROOT)
import streamlit as st,pandas as pd
from app.db import get_all_open_tenders,get_logs,init_db,save_tender
from app.scraper import scrape_via_jina
from app.auditor import heuristic_from_search
st.set_page_config(page_title="Tender Intelligence - Live",layout="wide")
init_db()
st.title("Tender Intelligence Agent — Live Monitor")
logs=get_logs(5)
st.sidebar.header("System Health")
if logs and logs[0].status=="FAILED": st.sidebar.error(f"FAILED {logs[0].message}")
elif logs: st.sidebar.success(f"🟢 Agent Active\nLast: {logs[0].timestamp}")
else: st.sidebar.success("🟢 Agent Active - Live Jina Mode")
tenders=get_all_open_tenders()
if not tenders:
    with st.spinner("DB empty, fetching LIVE REAL from etenders.gov.in via Jina..."):
        live=scrape_via_jina("https://etenders.gov.in/eprocure/app?page=FrontEndLatestActiveTenders&service=page")
        live+=scrape_via_jina("https://eprocure.gov.in/cppp/latestactivetenders")
        for res in live[:20]:
            for t in heuristic_from_search(res): save_tender(t)
        tenders=get_all_open_tenders()
st.metric("Active Open Tenders - REAL from gov.in",len(tenders))
if not tenders:
    st.error("No tenders even after live fetch. Check Actions logs.")
    st.stop()
st.dataframe(pd.DataFrame([{"Title":t.title,"Category":t.category,"Closing":t.closing_date,"Issuer":t.issued_by,"Source":t.source_url} for t in tenders]),use_container_width=True)
for t in tenders:
    with st.container(border=True):
        st.subheader(t.title)
        st.write(f"**Category:** {t.category} | **Issuer:** {t.issued_by} | **Closing:** {t.closing_date}")
        st.write(f"**What it is:** {t.title}")
        st.write(f"**Qualification:** {t.qualification_criteria} | **Eligibility:** {t.eligibility_status}")
        st.link_button("🔗 Verify Real - gov.in",t.source_url)
