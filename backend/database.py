from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine, Session
from backend.config import DATABASE_URL

engine_kwargs = {"echo": False}
if DATABASE_URL in {"sqlite://", "sqlite:///:memory:"}:
    # Keep a single SQLite in-memory connection for tests.
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **engine_kwargs)

def get_session():
    with Session(engine) as session:
        yield session
