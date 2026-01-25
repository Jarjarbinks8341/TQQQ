"""Shared test fixtures."""

import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Create tables
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
            ma30 REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, signal_type)
        )
    """)

    conn.commit()

    yield conn, path

    conn.close()
    os.unlink(path)


@pytest.fixture
def sample_price_data():
    """Generate sample price data for testing."""
    dates = pd.date_range(start="2025-01-01", periods=40, freq="B")
    data = {
        "Open": [50 + i * 0.5 for i in range(40)],
        "High": [51 + i * 0.5 for i in range(40)],
        "Low": [49 + i * 0.5 for i in range(40)],
        "Close": [50 + i * 0.5 for i in range(40)],
        "Volume": [1000000 + i * 10000 for i in range(40)],
    }
    df = pd.DataFrame(data, index=dates)
    return df


@pytest.fixture
def sample_price_data_with_crossover():
    """Generate sample price data that creates a golden cross.

    MA5 and MA30 need enough data to calculate, and we need a clear crossover.
    With 40 days of data:
    - MA30 needs 30 days, so crossover can happen on day 31+
    - We create a decline for 35 days, then sharp rally to trigger golden cross
    """
    dates = pd.date_range(start="2025-01-01", periods=40, freq="B")

    # Decline for first 35 days, then rally
    prices = (
        [80, 78, 76, 74, 72]  # Days 1-5
        + [70, 68, 66, 64, 62]  # Days 6-10
        + [60, 58, 56, 54, 52]  # Days 11-15
        + [50, 48, 46, 44, 42]  # Days 16-20
        + [40, 39, 38, 37, 36]  # Days 21-25
        + [35, 34, 33, 32, 31]  # Days 26-30: MA30 starts here
        + [30, 29, 28, 27, 26]  # Days 31-35: continued decline
        + [40, 55, 70, 85, 100]  # Days 36-40: sharp rally to cross
    )

    data = {
        "Open": [float(p) for p in prices],
        "High": [float(p + 1) for p in prices],
        "Low": [float(p - 1) for p in prices],
        "Close": [float(p) for p in prices],
        "Volume": [1000000] * 40,
    }
    df = pd.DataFrame(data, index=dates)
    return df


@pytest.fixture
def populated_db(temp_db, sample_price_data):
    """Create a database populated with sample data."""
    conn, path = temp_db
    cursor = conn.cursor()

    for date, row in sample_price_data.iterrows():
        cursor.execute(
            """
            INSERT INTO tqqq_prices (date, open, high, low, close, adj_close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                date.strftime("%Y-%m-%d"),
                row["Open"],
                row["High"],
                row["Low"],
                row["Close"],
                row["Close"],
                int(row["Volume"]),
            ),
        )

    conn.commit()
    return conn, path


@pytest.fixture
def sample_signal():
    """Create a sample crossover signal."""
    return {
        "date": "2025-01-15",
        "signal_type": "GOLDEN_CROSS",
        "close_price": 55.50,
        "ma5": 54.00,
        "ma30": 53.50,
    }


@pytest.fixture
def sample_dead_cross_signal():
    """Create a sample dead cross signal."""
    return {
        "date": "2025-01-20",
        "signal_type": "DEAD_CROSS",
        "close_price": 48.00,
        "ma5": 49.00,
        "ma30": 50.00,
    }
