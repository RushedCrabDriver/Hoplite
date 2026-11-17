"""Shared database helpers (SQLAlchemy engine + script loading)."""
import os
from pathlib import Path

from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"

DEFAULT_URL = "postgresql+psycopg2://conf:conf@localhost:5432/conference_db"


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    # Hosting providers often hand out postgres:// URLs.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def get_engine(echo: bool = False):
    return create_engine(database_url(), echo=echo, pool_pre_ping=True)


def read_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def create_schema(conn) -> None:
    """Part 2, item 1: create all tables, constraints and the view."""
    conn.exec_driver_sql(read_sql("schema.sql"))
    conn.exec_driver_sql(read_sql("view.sql"))


def seed_data(conn) -> None:
    """Part 2, item 2: populate the sample data."""
    conn.exec_driver_sql(read_sql("seed.sql"))


TABLES = [
    "app_user", "author", "author_research_area", "reviewer", "reviewer_expertise",
    "conference", "conference_host", "conference_reviewer", "track",
    "conference_session", "paper", "paper_keyword", "paper_author",
    "paper_version", "review",
]
