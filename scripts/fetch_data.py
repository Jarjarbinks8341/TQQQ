#!/usr/bin/env python3
"""Main script to fetch TQQQ data and check for crossover signals."""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqqq.config import HISTORY_DAYS
from tqqq.database import (
    get_connection,
    get_last_date,
    save_prices,
    get_price_count,
    get_date_range,
    get_new_signals,
    save_signals,
)
from tqqq.fetcher import fetch_prices
from tqqq.signals import detect_crossovers
from tqqq.notifications import trigger_all_notifications


def main():
    parser = argparse.ArgumentParser(description="Fetch TQQQ stock data")
    parser.add_argument(
        "--full",
        action="store_true",
        help=f"Fetch full {HISTORY_DAYS} days (default: incremental update)",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Starting TQQQ data fetch...")

    conn = get_connection()

    # Fetch data
    if args.full:
        print(f"[{timestamp}] Fetching full {HISTORY_DAYS} days of data...")
        df = fetch_prices(days=HISTORY_DAYS)
    else:
        last_date = get_last_date(conn)
        if last_date:
            start_date = datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)
            print(f"[{timestamp}] Incremental update from {last_date}...")
            df = fetch_prices(start_date=start_date)
        else:
            print(f"[{timestamp}] No existing data, fetching full {HISTORY_DAYS} days...")
            df = fetch_prices(days=HISTORY_DAYS)

    print(f"[{timestamp}] Fetched {len(df)} days of data")

    # Save to database
    if len(df) > 0:
        rows = save_prices(conn, df)
        print(f"[{timestamp}] Saved {rows} rows to database")
    else:
        print(f"[{timestamp}] No new data to save")

    # Show stats
    count = get_price_count(conn)
    min_date, max_date = get_date_range(conn)
    print(f"[{timestamp}] Total rows in database: {count}")
    print(f"[{timestamp}] Date range: {min_date} to {max_date}")

    # Detect and process crossover signals
    print(f"[{timestamp}] Checking for crossover signals...")
    all_signals = detect_crossovers(conn)
    new_signals = get_new_signals(conn, all_signals)

    if new_signals:
        print(f"[{timestamp}] Found {len(new_signals)} new crossover signal(s)!")
        save_signals(conn, new_signals)
        for signal in new_signals:
            trigger_all_notifications(signal, timestamp)
    else:
        print(f"[{timestamp}] No new crossover signals")

    conn.close()
    print(f"[{timestamp}] Done!")


if __name__ == "__main__":
    main()
