"""
SQLite persistence.

GitHub Actions and Streamlit primarily use JSON because JSON can be committed
to GitHub and read by Streamlit Cloud. SQLite is retained as a local audit copy.
"""

import os
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/tenders.db")

# Ensure SQLite directory exists before database initialization.
if DATABASE_URL.startswith("sqlite:///"):
    database_path = DATABASE_URL.replace("sqlite:///", "", 1)
    database_folder = os.path.dirname(database_path)

    if database_folder:
        os.makedirs(database_folder, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


class TenderRecord(Base):
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True)
    title = Column(String(1000), nullable=False)
    source_url = Column(String(2000), nullable=False)
    category = Column(String(200), nullable=False)
    closing_date = Column(String(30), nullable=False)
    issued_by = Column(String(500), default="NOT SURE")
    qualification_criteria = Column(Text, default="NOT SURE")
    eligibility_status = Column(String(50), default="NOT SURE")
    is_net_cost = Column(Boolean, default=False)
    is_open_now = Column(Boolean, default=False)
    confidence = Column(String(20), default="LOW")
    evidence = Column(Text, default="NOT SURE")
    found_at = Column(DateTime, default=datetime.utcnow)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(30), nullable=False)
    message = Column(Text, nullable=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def save_tender(tender: dict):
    """Save a real tender only once based on title + URL."""

    session = SessionLocal()

    try:
        existing = session.query(TenderRecord).filter_by(
            title=tender["title"],
            source_url=tender["source_url"],
        ).first()

        if existing:
            return False

        session.add(
            TenderRecord(
                title=tender["title"],
                source_url=tender["source_url"],
                category=tender["category"],
                closing_date=tender["closing_date"],
                issued_by=tender.get("issued_by", "NOT SURE"),
                qualification_criteria=tender.get(
                    "qualification_criteria",
                    "NOT SURE",
                ),
                eligibility_status=tender.get(
                    "eligibility_status",
                    "NOT SURE",
                ),
                is_net_cost=tender.get("is_net_cost", False),
                is_open_now=tender.get("is_open_now", False),
                confidence=tender.get("confidence", "LOW"),
                evidence=tender.get("evidence", "NOT SURE"),
            )
        )

        session.commit()
        return True

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def log_system_status(status: str, message: str):
    """Write health status to SQLite."""

    session = SessionLocal()

    try:
        session.add(
            SystemLog(
                status=status.upper(),
                message=message,
            )
        )
        session.commit()

    except Exception:
        session.rollback()

    finally:
        session.close()
