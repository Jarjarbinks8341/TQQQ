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
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crossover_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            close_price REAL,
            ma5 REAL,
            ma30 REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, date, signal_type)
        )
    """)

    conn.commit()


def get_last_date(conn: sqlite3.Connection, ticker: str) -> Optional[str]:
    """Get the most recent date in the database for a specific ticker."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(date) FROM tqqq_prices WHERE ticker = ?", (ticker,))
    result = cursor.fetchone()[0]
    return result


def save_prices(conn: sqlite3.Connection, ticker: str, df: pd.DataFrame) -> int:
    """Save price data to database for a specific ticker."""
    cursor = conn.cursor()
    rows_inserted = 0

    for date, row in df.iterrows():
        date_str = date.strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT OR REPLACE INTO tqqq_prices
            (ticker, date, open, high, low, close, adj_close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker,
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


def load_prices(conn: sqlite3.Connection, ticker: str) -> pd.DataFrame:
    """Load all price data from database for a specific ticker."""
    df = pd.read_sql_query(
        "SELECT date, close FROM tqqq_prices WHERE ticker = ? ORDER BY date",
        conn,
        params=(ticker,),
        parse_dates=["date"]
    )
    # Ensure close is numeric
    if len(df) > 0:
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df


def get_new_signals(conn: sqlite3.Connection, ticker: str, signals: List[Dict]) -> List[Dict]:
    """Filter out signals that have already been recorded for a specific ticker."""
    cursor = conn.cursor()
    new_signals = []

    for signal in signals:
        cursor.execute(
            "SELECT 1 FROM crossover_signals WHERE ticker = ? AND date = ? AND signal_type = ?",
            (ticker, signal["date"], signal["signal_type"])
        )
        if cursor.fetchone() is None:
            new_signals.append(signal)

    return new_signals


def save_signals(conn: sqlite3.Connection, ticker: str, signals: List[Dict]) -> int:
    """Save new signals to the database for a specific ticker."""
    cursor = conn.cursor()
    saved = 0

    for signal in signals:
        cursor.execute("""
            INSERT OR IGNORE INTO crossover_signals
            (ticker, date, signal_type, close_price, ma5, ma30)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            signal["date"],
            signal["signal_type"],
            signal["close_price"],
            signal["ma5"],
            signal["ma30"]
        ))
        saved += cursor.rowcount

    conn.commit()
    return saved


def get_price_count(conn: sqlite3.Connection, ticker: Optional[str] = None) -> int:
    """Get total number of price records. If ticker is None, returns count for all tickers."""
    cursor = conn.cursor()
    if ticker:
        cursor.execute("SELECT COUNT(*) FROM tqqq_prices WHERE ticker = ?", (ticker,))
    else:
        cursor.execute("SELECT COUNT(*) FROM tqqq_prices")
    return cursor.fetchone()[0]


def get_date_range(conn: sqlite3.Connection, ticker: str) -> tuple:
    """Get min and max dates in database for a specific ticker."""
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(date), MAX(date) FROM tqqq_prices WHERE ticker = ?", (ticker,))
    return cursor.fetchone()


def get_all_tickers(conn: sqlite3.Connection) -> List[str]:
    """Get list of all tickers in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ticker FROM tqqq_prices ORDER BY ticker")
    return [row[0] for row in cursor.fetchall()]


def get_ticker_stats(conn: sqlite3.Connection) -> Dict[str, Dict]:
    """Get statistics for all tickers in the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            ticker,
            COUNT(*) as record_count,
            MIN(date) as first_date,
            MAX(date) as last_date
        FROM tqqq_prices
        GROUP BY ticker
        ORDER BY ticker
    """)

    stats = {}
    for row in cursor.fetchall():
        stats[row[0]] = {
            "record_count": row[1],
            "first_date": row[2],
            "last_date": row[3]
        }
    return stats
