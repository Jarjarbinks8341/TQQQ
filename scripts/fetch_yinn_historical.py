#!/usr/bin/env python3
"""Fetch extended YINN historical data from 2020-01-01."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tqqq.database import get_connection, save_prices, get_new_signals, save_signals
from tqqq.fetcher import fetch_prices
from tqqq.signals import detect_crossovers
from tqqq.notifications import trigger_all_notifications

def main():
    print("Fetching YINN data from January 1, 2020...")

    # Fetch from 2020-01-01
    start_date = datetime(2020, 1, 1)
    ticker = "YINN"

    print(f"Fetching {ticker} from {start_date.strftime('%Y-%m-%d')}...")
    df = fetch_prices(ticker, start_date=start_date)

    print(f"Fetched {len(df)} days of data")

    if len(df) == 0:
        print("No data fetched. Exiting.")
        return

    # Save to database
    conn = get_connection()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = save_prices(conn, ticker, df)
    print(f"Saved {rows} rows to database")

    # Detect signals
    print("Detecting crossover signals...")
    all_signals = detect_crossovers(conn, ticker)
    new_signals = get_new_signals(conn, ticker, all_signals)

    if new_signals:
        print(f"Found {len(new_signals)} new crossover signal(s)!")
        save_signals(conn, ticker, new_signals)

        # Display signals (don't trigger notifications for historical data)
        for signal in new_signals:
            emoji = "🟢" if signal["signal_type"] == "GOLDEN_CROSS" else "🔴"
            sig_type = "Golden Cross" if signal["signal_type"] == "GOLDEN_CROSS" else "Dead Cross"
            print(f"{emoji} {signal['date']}: {sig_type} @ ${signal['close_price']:.2f}")
    else:
        print("No new crossover signals")

    conn.close()
    print("Done!")

if __name__ == "__main__":
    main()
