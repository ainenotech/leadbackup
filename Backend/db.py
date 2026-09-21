import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Postgres connection string, e.g.
# postgresql+psycopg2://user:password@localhost:5432/lead_reengagement
# Or SQLite: sqlite:///campaign.db
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/lead_reengagement",
)


def _init_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})
    try:
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as conn:
            pass
        return eng
    except Exception as exc:
        sqlite_fallback = "sqlite:///campaign.db"
        server_info = url.split("@")[-1] if "@" in url else url
        print(f"[Notice] Could not connect to PostgreSQL at {server_info} ({exc}).")
        print(f"[Notice] Automatically falling back to local SQLite database: '{sqlite_fallback}'.")
        return create_engine(sqlite_fallback, connect_args={"check_same_thread": False, "timeout": 30})


engine = _init_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


def init_db():
    """Ensures all tables are created and applies non-breaking schema migrations."""
    from sqlalchemy import inspect, text
    import Backend.models  # Ensure all model tables are registered on Base

    Base.metadata.create_all(bind=engine)
    new_cols = [
        ("phone", "VARCHAR"),
        ("opened", "BOOLEAN DEFAULT FALSE"),
        ("open_count", "INTEGER DEFAULT 0"),
        ("first_open_at", "TIMESTAMP"),
        ("last_open_at", "TIMESTAMP"),
        ("clicked_link", "BOOLEAN DEFAULT FALSE"),
        ("click_count", "INTEGER DEFAULT 0"),
        ("first_click_at", "TIMESTAMP"),
        ("last_click_at", "TIMESTAMP"),
        ("clicked_urls", "TEXT"),
        ("unsubscribed", "BOOLEAN DEFAULT FALSE"),
        ("unsubscribed_at", "TIMESTAMP"),
        ("bounced", "BOOLEAN DEFAULT FALSE"),
        ("bounce_reason", "TEXT"),
        ("engagement_score", "FLOAT DEFAULT 0.0"),
        ("form_filled_at", "TIMESTAMP"),
        ("submitted_availability", "TEXT"),
        ("note", "TEXT"),
        ("reply_body", "TEXT"),
        ("reply_intent", "VARCHAR"),
        ("reply_received_at", "TIMESTAMP"),
        ("ai_reply_sent", "TEXT"),
        ("ai_reply_sent_at", "TIMESTAMP"),
        ("proposed_slot", "TEXT"),
        ("confirmed_slot", "VARCHAR"),
        ("meet_link", "VARCHAR"),
        ("booking_status", "VARCHAR"),
        ("scheduling_error", "TEXT"),
    ]
    inspector = inspect(engine)
    if "campaign_log" in inspector.get_table_names():
        existing_cols = {col["name"] for col in inspector.get_columns("campaign_log")}
        with engine.connect() as conn:
            for col_name, col_type in new_cols:
                if col_name not in existing_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE campaign_log ADD COLUMN {col_name} {col_type};"))
                        conn.commit()
                    except Exception:
                        conn.rollback()


