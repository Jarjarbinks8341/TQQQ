"""Crossover signal detection."""

import sqlite3
from typing import List, Dict

import pandas as pd

from .config import MA_SHORT, MA_LONG
from .database import load_prices


def detect_crossovers(conn: sqlite3.Connection) -> List[Dict]:
    """Detect golden cross and dead cross signals from price data.

    Golden Cross: Short MA crosses above Long MA (bullish)
    Dead Cross: Short MA crosses below Long MA (bearish)

    Returns:
        List of signal dictionaries with date, type, and price info.
    """
    df = load_prices(conn)

    if len(df) < MA_LONG:
        return []

    # Calculate moving averages
    df["MA_SHORT"] = df["close"].rolling(window=MA_SHORT).mean()
    df["MA_LONG"] = df["close"].rolling(window=MA_LONG).mean()
    df = df.dropna()

    # Detect crossovers
    df["short_above"] = df["MA_SHORT"] > df["MA_LONG"]
    df["prev_short_above"] = df["short_above"].shift(1)

    signals = []

    # Golden Cross: Short MA crosses from below to above Long MA
    golden = df[(df["short_above"] == True) & (df["prev_short_above"] == False)]
    for _, row in golden.iterrows():
        signals.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "signal_type": "GOLDEN_CROSS",
            "close_price": row["close"],
            "ma5": row["MA_SHORT"],
            "ma30": row["MA_LONG"]
        })

    # Dead Cross: Short MA crosses from above to below Long MA
    dead = df[(df["short_above"] == False) & (df["prev_short_above"] == True)]
    for _, row in dead.iterrows():
        signals.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "signal_type": "DEAD_CROSS",
            "close_price": row["close"],
            "ma5": row["MA_SHORT"],
            "ma30": row["MA_LONG"]
        })

    return signals


def get_current_status(conn: sqlite3.Connection) -> Dict:
    """Get current MA status and values.

    Returns:
        Dictionary with current status, MA values, and gap.
    """
    df = load_prices(conn)

    if len(df) < MA_LONG:
        return {"status": "INSUFFICIENT_DATA"}

    df["MA_SHORT"] = df["close"].rolling(window=MA_SHORT).mean()
    df["MA_LONG"] = df["close"].rolling(window=MA_LONG).mean()

    last = df.iloc[-1]
    is_bullish = last["MA_SHORT"] > last["MA_LONG"]

    return {
        "date": last["date"].strftime("%Y-%m-%d"),
        "status": "BULLISH" if is_bullish else "BEARISH",
        "close": last["close"],
        "ma_short": last["MA_SHORT"],
        "ma_long": last["MA_LONG"],
        "gap": last["MA_SHORT"] - last["MA_LONG"]
    }
