import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
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

    from sqlalchemy.pool import QueuePool
    from sqlalchemy import text

    # 1. Try standard driver (psycopg2 for Linux / Render production)
    try:
        eng = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=25,
            pool_recycle=300,
            pool_pre_ping=True,
        )
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return eng
    except Exception as exc_primary:
        # 2. Try pure-python pg8000 driver (works on Windows without C DLL blocks)
        try:
            import ssl
            ctx = ssl.create_default_context()
            pg8000_url = url
            if "postgresql+psycopg2://" in pg8000_url:
                pg8000_url = pg8000_url.replace("postgresql+psycopg2://", "postgresql+pg8000://")
            elif pg8000_url.startswith("postgresql://"):
                pg8000_url = "postgresql+pg8000://" + pg8000_url[len("postgresql://"):]

            base_url = pg8000_url.split("?")[0]
            eng = create_engine(
                base_url,
                connect_args={"ssl_context": ctx},
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_timeout=25,
                pool_recycle=300,
                pool_pre_ping=True,
            )
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[Notice] Connected to PostgreSQL via pure-python pg8000 driver.")
            return eng
        except Exception as exc_pg8000:
            sqlite_fallback = "sqlite:///campaign.db"
            server_info = url.split("@")[-1] if "@" in url else url
            print(f"[Notice] Could not initialize PostgreSQL engine at {server_info} ({exc_pg8000}).")
            print(f"[Notice] Automatically falling back to local SQLite database: '{sqlite_fallback}'.")
            return create_engine(sqlite_fallback, connect_args={"check_same_thread": False, "timeout": 30})


engine = _init_engine(DATABASE_URL)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if type(dbapi_connection).__module__.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        finally:
            cursor.close()


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
    import Backend.master_db_models  # Ensure Master DB tables are registered on Base

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

    # ── Master DB tables ──
    # create_all is safe: it only creates tables that do not yet exist.
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[init_db notice] Master DB table creation note: {e}")

    # Add master_lead_id FK column to campaign_log (nullable, non-breaking)
    try:
        from sqlalchemy import inspect as _insp, text as _txt
        _inspector = _insp(engine)
        if "campaign_log" in _inspector.get_table_names():
            _existing = {c["name"] for c in _inspector.get_columns("campaign_log")}
            if "master_lead_id" not in _existing:
                with engine.connect() as conn:
                    try:
                        conn.execute(_txt("ALTER TABLE campaign_log ADD COLUMN master_lead_id VARCHAR;"))
                        conn.commit()
                    except Exception:
                        conn.rollback()
    except Exception as e:
        print(f"[init_db notice] master_lead_id migration note: {e}")

    _DB_INITIALIZED = True
