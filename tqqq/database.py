"""Database operations for TQQQ trading bot."""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict

import pandas as pd

from .config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Get database connection and ensure tables exist."""
    conn = sqlite3.connect(str(DB_PATH))
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    """Create database tables if they don't exist."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tqqq_prices (
            date TEXT PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crossover_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            close_price REAL,
            ma5 REAL,
            ma20 REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, signal_type)
        )
    """)

    conn.commit()


def get_last_date(conn: sqlite3.Connection) -> Optional[str]:
    """Get the most recent date in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(date) FROM tqqq_prices")
    result = cursor.fetchone()[0]
    return result


def save_prices(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    """Save price data to database."""
    cursor = conn.cursor()
    rows_inserted = 0

    for date, row in df.iterrows():
        date_str = date.strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT OR REPLACE INTO tqqq_prices
            (date, open, high, low, close, adj_close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            date_str,
            row["Open"],
            row["High"],
            row["Low"],
            row["Close"],
            row.get("Adj Close", row["Close"]),
            int(row["Volume"])
        ))
        rows_inserted += 1

    conn.commit()
    return rows_inserted


def load_prices(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load all price data from database."""
    df = pd.read_sql_query(
        "SELECT date, close FROM tqqq_prices ORDER BY date",
        conn,
        parse_dates=["date"]
    )
    # Ensure close is numeric
    if len(df) > 0:
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df


def get_new_signals(conn: sqlite3.Connection, signals: List[Dict]) -> List[Dict]:
    """Filter out signals that have already been recorded."""
    cursor = conn.cursor()
    new_signals = []

    for signal in signals:
        cursor.execute(
            "SELECT 1 FROM crossover_signals WHERE date = ? AND signal_type = ?",
            (signal["date"], signal["signal_type"])
        )
        if cursor.fetchone() is None:
            new_signals.append(signal)

    return new_signals


def save_signals(conn: sqlite3.Connection, signals: List[Dict]) -> int:
    """Save new signals to the database."""
    cursor = conn.cursor()
    saved = 0

    for signal in signals:
        cursor.execute("""
            INSERT OR IGNORE INTO crossover_signals
            (date, signal_type, close_price, ma5, ma20)
            VALUES (?, ?, ?, ?, ?)
        """, (
            signal["date"],
            signal["signal_type"],
            signal["close_price"],
            signal["ma5"],
            signal["ma20"]
        ))
        saved += cursor.rowcount

    conn.commit()
    return saved


def get_price_count(conn: sqlite3.Connection) -> int:
    """Get total number of price records."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tqqq_prices")
    return cursor.fetchone()[0]


def get_date_range(conn: sqlite3.Connection) -> tuple:
    """Get min and max dates in database."""
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(date), MAX(date) FROM tqqq_prices")
    return cursor.fetchone()
