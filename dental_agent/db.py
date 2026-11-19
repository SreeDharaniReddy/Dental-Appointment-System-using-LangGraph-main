"""
db.py - connects Python to the PostgreSQL database.

Every other file that needs the database will do:

    from dental_agent.db import get_connection

    with get_connection() as conn:
        rows = conn.execute("SELECT ...").fetchall()
"""

import os

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Read the settings from the .env file (DB_HOST, DB_PASSWORD, ...)
load_dotenv()


def get_connection():
    """Open a new connection to PostgreSQL using the values from .env."""
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "dental_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        row_factory=dict_row,  # each row comes back as a dict: {"doctor_name": ...}
    )


# ---------------------------------------------------------------
# Quick test: run  python -m dental_agent.db
# ---------------------------------------------------------------
if __name__ == "__main__":
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*)                                 AS total,
                   COUNT(*) FILTER (WHERE is_available)     AS free,
                   COUNT(*) FILTER (WHERE NOT is_available) AS booked
            FROM appointments
            """
        ).fetchone()

    print("Connected to PostgreSQL!")
    print(f"Total slots : {row['total']}")
    print(f"Free slots  : {row['free']}")
    print(f"Booked slots: {row['booked']}")