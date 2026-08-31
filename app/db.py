import os, sqlite3
from datetime import datetime
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_FILE = os.path.join(ROOT_DIR, "tenders.db")

class TenderRecordObj:
    def __init__(self, id, title, source_url, category, closing_date, issued_by, qualification_criteria, eligibility_status, is_net_cost, is_open_now, extraction_confidence, found_at):
        self.id=id; self.title=title; self.source_url=source_url; self.category=category
        self.closing_date=closing_date; self.issued_by=issued_by; self.qualification_criteria=qualification_criteria
        self.eligibility_status=eligibility_status; self.is_net_cost=bool(is_net_cost); self.is_open_now=bool(is_open_now)
        self.extraction_confidence=extraction_confidence; self.found_at=found_at

class SystemLogObj:
    def __init__(self, id, timestamp, status, message):
        self.id=id; self.timestamp=timestamp; self.status=status; self.message=message

def get_conn():
    conn=sqlite3.connect(DB_FILE); conn.row_factory=sqlite3.Row; return conn

def init_db():
    conn=get_conn(); cur=conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS tenders (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, source_url TEXT, category TEXT, closing_date TEXT DEFAULT 'NOT SURE', issued_by TEXT DEFAULT 'NOT SURE', qualification_criteria TEXT DEFAULT 'NOT SURE', eligibility_status TEXT DEFAULT 'NOT SURE', is_net_cost INTEGER DEFAULT 0, is_open_now INTEGER DEFAULT 0, extraction_confidence TEXT DEFAULT 'NOT SURE', found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS system_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT, message TEXT)")
    conn.commit(); conn.close()

def save_tender(t):
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT id FROM tenders WHERE title=? AND source_url=?", (t.title, t.source_url))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO tenders (title, source_url, category, closing_date, issued_by, qualification_criteria, eligibility_status, is_net_cost, is_open_now, extraction_confidence, found_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (t.title, t.source_url, t.category, t.closing_date, t.issued_by, t.qualification_criteria, t.eligibility_status, int(t.is_net_cost), int(t.is_open_now), t.extraction_confidence, datetime.utcnow()))
        conn.commit()
    conn.close()

def get_all_open_tenders():
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM tenders WHERE is_open_now=1 ORDER BY found_at DESC")
    rows=cur.fetchall(); conn.close()
    res=[]
    for r in rows:
        try: ts=datetime.fromisoformat(r["found_at"])
        except: ts=datetime.utcnow()
        res.append(TenderRecordObj(r["id"], r["title"], r["source_url"], r["category"], r["closing_date"], r["issued_by"], r["qualification_criteria"], r["eligibility_status"], r["is_net_cost"], r["is_open_now"], r["extraction_confidence"], ts))
    return res

def get_logs(limit=20):
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM system_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows=cur.fetchall(); conn.close()
    logs=[]
    for r in rows:
        try: ts=datetime.fromisoformat(r["timestamp"])
        except: ts=datetime.utcnow()
        logs.append(SystemLogObj(r["id"], ts, r["status"], r["message"]))
    return logs

def log_system_status(status: str, msg=""):
    conn=get_conn(); cur=conn.cursor()
    cur.execute("INSERT INTO system_logs (status, message, timestamp) VALUES (?,?,?)", (status, msg, datetime.utcnow()))
    conn.commit(); conn.close()
