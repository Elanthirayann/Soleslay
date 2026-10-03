"""
Database engine / session setup.

Storage strategy
-----------------
This project ships with no cloud-provider-specific config (no Dockerfile,
no Procfile, no vercel/render/fly config was found in the repository), so we
cannot assume which platform it will run on. To stay safe under that
uncertainty:

* By default we use a SQLite file at app/data/soleslay.db. This works
  correctly ONLY if the deployment target gives the app a persistent disk
  (a VPS, a container with a mounted volume, etc). Every write goes through
  SQLAlchemy so this is a one-env-var change away from Postgres.

* If a DATABASE_URL environment variable is set (e.g. a managed Postgres
  instance, which is the norm on most modern PaaS platforms with ephemeral
  filesystems), it is used instead — no code changes required. This is the
  strongly recommended setting for any platform whose filesystem is wiped
  on redeploy/restart (Heroku, most containers-without-volumes, etc).

Never assume the SQLite file survives a redeploy unless you have verified
the platform mounts a persistent volume at that path.
"""
import os
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATA_DIR = Path(__file__).resolve().parent / "data"
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# Render / Supabase / Neon sometimes provide 'postgres://' which SQLAlchemy 1.4/2.0+ does not accept
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    # If running on Vercel / AWS Lambda, the root filesystem is read-only except /tmp
    if os.environ.get("VERCEL"):
        import shutil
        tmp_dir = Path("/tmp")
        tmp_db = tmp_dir / "soleslay.db"
        src_db = DATA_DIR / "soleslay.db"
        if not tmp_db.exists() and src_db.exists():
            try:
                shutil.copy2(src_db, tmp_db)
            except Exception:
                pass
        DATABASE_URL = f"sqlite:///{tmp_db.as_posix()}"
    else:
        DATABASE_URL = f"sqlite:///{(DATA_DIR / 'soleslay.db').as_posix()}"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

if DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Context manager for scripts (migration, admin creation) outside of a request."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
