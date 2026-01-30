#!/usr/bin/env python3
"""Plot stock price with moving averages."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import pandas as pd

from tqqq.config import ROOT_DIR, MA_SHORT, MA_LONG, TICKER
from tqqq.database import get_connection, load_prices


def main():
    parser = argparse.ArgumentParser(description="Plot stock chart with moving averages")
    parser.add_argument(
        "--ticker",
        default=TICKER,
        help=f"Ticker to plot (default: {TICKER})",
    )
    args = parser.parse_args()

    ticker = args.ticker.upper()

    conn = get_connection()
    df = load_prices(conn, ticker)
    conn.close()

    if len(df) < MA_LONG:
        print(f"Not enough data for {ticker}. Need at least {MA_LONG} days.")
        return

    # Calculate moving averages
    df["MA_SHORT"] = df["close"].rolling(window=MA_SHORT).mean()
    df["MA_LONG"] = df["close"].rolling(window=MA_LONG).mean()
    df.set_index("date", inplace=True)

    # Plot
    plt.figure(figsize=(14, 7))
    plt.plot(df.index, df["close"], label="Close Price", alpha=0.7, linewidth=1)
    plt.plot(df.index, df["MA_SHORT"], label=f"{MA_SHORT}-Day MA", linewidth=2)
    plt.plot(df.index, df["MA_LONG"], label=f"{MA_LONG}-Day MA", linewidth=2)

    plt.title(f"{ticker} Stock Price with Moving Averages", fontsize=14)
    plt.xlabel("Date")
    plt.ylabel("Price ($)")
    plt.legend(loc="upper left")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Save to file
    output_path = ROOT_DIR / "data" / f"{ticker.lower()}_chart.png"
    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to {output_path}")

    # Show if display available
    plt.show()


if __name__ == "__main__":
    main()
