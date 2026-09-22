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
        from sqlalchemy.pool import QueuePool
        eng = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=15,
            pool_recycle=300,
            pool_pre_ping=True,
        )
        return eng
    except Exception as exc:
        sqlite_fallback = "sqlite:///campaign.db"
        server_info = url.split("@")[-1] if "@" in url else url
        print(f"[Notice] Could not initialize PostgreSQL engine at {server_info} ({exc}).")
        print(f"[Notice] Automatically falling back to local SQLite database: '{sqlite_fallback}'.")
        return create_engine(sqlite_fallback, connect_args={"check_same_thread": False, "timeout": 30})


engine = _init_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()
_DB_INITIALIZED = False


def init_db():
    """Ensures all tables are created and applies non-breaking schema migrations."""
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return

    from sqlalchemy import inspect, text
    import Backend.models  # Ensure all model tables are registered on Base

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
        ("template_id", "VARCHAR"),
        ("template_name", "VARCHAR"),
    ]
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if "campaign_log" not in tables:
            Base.metadata.create_all(bind=engine)
        else:
            existing_cols = {col["name"] for col in inspector.get_columns("campaign_log")}
            missing = [c for c in new_cols if c[0] not in existing_cols]
            if missing:
                with engine.connect() as conn:
                    for col_name, col_type in missing:
                        try:
                            conn.execute(text(f"ALTER TABLE campaign_log ADD COLUMN {col_name} {col_type};"))
                            conn.commit()
                        except Exception:
                            conn.rollback()
    except Exception as e:
        print(f"[init_db notice] DB initialization/check note: {e}")

    _DB_INITIALIZED = True
