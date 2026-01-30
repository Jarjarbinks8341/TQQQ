#!/usr/bin/env python3
"""Simulate crossover detection for a date range."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from tqqq.config import MA_SHORT, MA_LONG, TICKER
from tqqq.database import get_connection, load_prices


def main():
    parser = argparse.ArgumentParser(description="Simulate crossover detection")
    parser.add_argument(
        "--start",
        default="2026-01-01",
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        default="2026-01-25",
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--ticker",
        default=TICKER,
        help=f"Ticker to simulate (default: {TICKER})",
    )
    args = parser.parse_args()

    ticker = args.ticker.upper()

    conn = get_connection()
    df = load_prices(conn, ticker)
    conn.close()

    # Calculate moving averages
    df["MA_SHORT"] = df["close"].rolling(window=MA_SHORT).mean()
    df["MA_LONG"] = df["close"].rolling(window=MA_LONG).mean()
    df = df.dropna()

    # Detect crossovers
    df["short_above"] = df["MA_SHORT"] > df["MA_LONG"]
    df["prev_short_above"] = df["short_above"].shift(1)

    # Filter date range
    mask = (df["date"] >= args.start) & (df["date"] <= args.end)
    data = df[mask].copy()

    print("=" * 80)
    print(f"{ticker} CROSSOVER SIMULATION: {args.start} to {args.end}")
    print("=" * 80)

    print(f"\n{'Date':<12} {'Close':>8} {'MA5':>8} {'MA30':>8} {'Status':>12} {'Signal':>20}")
    print("-" * 80)

    signals = []

    for _, row in data.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d")
        status = "BULLISH" if row["short_above"] else "BEARISH"

        signal = ""
        if row["short_above"] == True and row["prev_short_above"] == False:
            signal = "🟢 GOLDEN CROSS"
            signals.append({"date": date_str, "type": "GOLDEN", "close": row["close"]})
        elif row["short_above"] == False and row["prev_short_above"] == True:
            signal = "🔴 DEAD CROSS"
            signals.append({"date": date_str, "type": "DEAD", "close": row["close"]})

        marker = " <<<" if signal else ""
        print(
            f"{date_str:<12} ${row['close']:>7.2f} ${row['MA_SHORT']:>7.2f} "
            f"${row['MA_LONG']:>7.2f} {status:>12} {signal:>20}{marker}"
        )

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    golden = sum(1 for s in signals if s["type"] == "GOLDEN")
    dead = sum(1 for s in signals if s["type"] == "DEAD")

    print(f"Golden Crosses: {golden}")
    print(f"Dead Crosses: {dead}")
    print(f"Total Alerts: {len(signals)}")

    if len(data) > 0:
        last = data.iloc[-1]
        status = "BULLISH (MA5 > MA30)" if last["short_above"] else "BEARISH (MA5 < MA30)"
        print(f"\nCurrent Status ({last['date'].strftime('%Y-%m-%d')}): {status}")
        print(f"  MA5:  ${last['MA_SHORT']:.2f}")
        print(f"  MA30: ${last['MA_LONG']:.2f}")


if __name__ == "__main__":
    main()
