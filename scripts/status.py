#!/usr/bin/env python3
"""Show current TQQQ status and recent signals."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqqq.database import get_connection, get_price_count, get_date_range
from tqqq.signals import get_current_status


def main():
    conn = get_connection()

    # Database stats
    count = get_price_count(conn)
    min_date, max_date = get_date_range(conn)

    print("=" * 50)
    print("TQQQ TRADING BOT STATUS")
    print("=" * 50)

    print(f"\nDatabase: {count} price records")
    print(f"Date Range: {min_date} to {max_date}")

    # Current MA status
    status = get_current_status(conn)

    if status.get("status") == "INSUFFICIENT_DATA":
        print("\nNot enough data to calculate moving averages")
    else:
        emoji = "🟢" if status["status"] == "BULLISH" else "🔴"
        print(f"\n{emoji} Current Status: {status['status']}")
        print(f"  Date:  {status['date']}")
        print(f"  Close: ${status['close']:.2f}")
        print(f"  MA5:   ${status['ma_short']:.2f}")
        print(f"  MA20:  ${status['ma_long']:.2f}")
        print(f"  Gap:   ${status['gap']:.2f}")

    # Recent signals
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, signal_type, close_price
        FROM crossover_signals
        ORDER BY date DESC
        LIMIT 5
    """)
    recent = cursor.fetchall()

    if recent:
        print("\nRecent Signals:")
        print("-" * 50)
        for date, signal_type, close in recent:
            emoji = "🟢" if signal_type == "GOLDEN_CROSS" else "🔴"
            name = "Golden Cross" if signal_type == "GOLDEN_CROSS" else "Dead Cross"
            print(f"  {emoji} {date}: {name} @ ${close:.2f}")

    conn.close()


if __name__ == "__main__":
    main()
