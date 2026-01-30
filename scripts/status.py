#!/usr/bin/env python3
"""Show current status and recent signals for tracked tickers."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqqq.database import get_connection, get_price_count, get_date_range, get_all_tickers
from tqqq.signals import get_current_status
from tqqq.fear_greed import fetch_fear_greed, format_fear_greed_message


def show_ticker_status(conn, ticker: str):
    """Show status for a specific ticker."""
    print("=" * 50)
    print(f"{ticker} TRADING BOT STATUS")
    print("=" * 50)

    # Database stats
    count = get_price_count(conn, ticker)
    min_date, max_date = get_date_range(conn, ticker)

    print(f"\nDatabase: {count} price records")
    if min_date and max_date:
        print(f"Date Range: {min_date} to {max_date}")

    # Current MA status
    status = get_current_status(conn, ticker)

    if status.get("status") == "INSUFFICIENT_DATA":
        print("\nNot enough data to calculate moving averages")
    else:
        emoji = "🟢" if status["status"] == "BULLISH" else "🔴"
        print(f"\n{emoji} Current Status: {status['status']}")
        print(f"  Date:  {status['date']}")
        print(f"  Close: ${status['close']:.2f}")
        print(f"  MA5:   ${status['ma_short']:.2f}")
        print(f"  MA30:  ${status['ma_long']:.2f}")
        print(f"  Gap:   ${status['gap']:.2f}")

    # Recent signals
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, signal_type, close_price
        FROM crossover_signals
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT 5
    """, (ticker,))
    recent = cursor.fetchall()

    if recent:
        print("\nRecent Signals:")
        print("-" * 50)
        for date, signal_type, close in recent:
            emoji = "🟢" if signal_type == "GOLDEN_CROSS" else "🔴"
            name = "Golden Cross" if signal_type == "GOLDEN_CROSS" else "Dead Cross"
            print(f"  {emoji} {date}: {name} @ ${close:.2f}")


def main():
    parser = argparse.ArgumentParser(description="Show trading bot status")
    parser.add_argument(
        "--ticker",
        help="Show specific ticker (default: all tracked tickers)",
    )
    args = parser.parse_args()

    conn = get_connection()

    # Determine which tickers to show
    if args.ticker:
        tickers = [args.ticker.upper()]
    else:
        tickers = get_all_tickers(conn)
        if not tickers:
            print("No tickers found in database. Run fetch_data.py first.")
            conn.close()
            return

    # Show status for each ticker
    for i, ticker in enumerate(tickers):
        if i > 0:
            print("\n")  # Add spacing between tickers
        show_ticker_status(conn, ticker)

    conn.close()

    # Fear & Greed Index (once for all tickers)
    print("\n" + "=" * 50)
    print("CNN FEAR & GREED INDEX")
    print("=" * 50)
    fg_data = fetch_fear_greed()
    if fg_data:
        print(f"\n{format_fear_greed_message(fg_data)}")
    else:
        print("\nUnable to fetch Fear & Greed Index")


if __name__ == "__main__":
    main()
