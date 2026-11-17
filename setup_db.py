"""Recreate the schema and restore the initial sample dataset.

Usage:  python setup_db.py          (uses DATABASE_URL or the default local URL)
"""
from sqlalchemy import text

from db import TABLES, create_schema, get_engine, seed_data


def main() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        create_schema(conn)
        seed_data(conn)
    with engine.connect() as conn:
        for table in TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            print(f"{table:22s} {count}")
    print("Database recreated and seeded.")


if __name__ == "__main__":
    main()
