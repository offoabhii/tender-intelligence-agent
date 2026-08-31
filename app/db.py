import os
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tenders.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class TenderRecord(Base):
    __tablename__ = "tenders"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    source_url = Column(String)
    category = Column(String)
    closing_date = Column(String, default="NOT SURE")
    issued_by = Column(String, default="NOT SURE")
    qualification_criteria = Column(Text, default="NOT SURE")
    eligibility_status = Column(Text, default="NOT SURE")
    is_net_cost = Column(Boolean, default=False)
    is_open_now = Column(Boolean, default=False)
    extraction_confidence = Column(String, default="NOT SURE")
    found_at = Column(DateTime, default=datetime.utcnow)

class SystemLog(Base):
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String)
    message = Column(Text)

def init_db():
    Base.metadata.create_all(bind=engine)

def save_tender(t):
    s = SessionLocal()
    exists = s.query(TenderRecord).filter_by(title=t.title, source_url=t.source_url).first()
    if not exists:
        rec = TenderRecord(
            title=t.title, source_url=t.source_url, category=t.category,
            closing_date=t.closing_date, issued_by=t.issued_by,
            qualification_criteria=t.qualification_criteria,
            eligibility_status=t.eligibility_status,
            is_net_cost=t.is_net_cost, is_open_now=t.is_open_now,
            extraction_confidence=t.extraction_confidence
        )
        s.add(rec)
        s.commit()
    s.close()

def get_all_open_tenders():
    s = SessionLocal()
    results = s.query(TenderRecord).filter_by(is_open_now=True).order_by(TenderRecord.found_at.desc()).all()
    s.close()
    return results

def get_logs(limit=20):
    s = SessionLocal()
    logs = s.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(limit).all()
    s.close()
    return logs

def log_system_status(status: str, msg=""):
    s = SessionLocal()
    log = SystemLog(status=status, message=msg)
    s.add(log)
    s.commit()
    s.close()
    try:
        with open("system_health.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.utcnow()} | {status} | {msg}\n")
    except:
        pass