#!/usr/bin/env python3
"""Test notification system by simulating a crossover signal.

This script creates a mock Golden Cross or Dead Cross signal and sends
notifications via all configured channels (console, file, email, webhooks).
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tqqq.notifications import trigger_all_notifications
from tqqq.config import EMAIL_ENABLED, EMAIL_RECIPIENTS


def test_golden_cross(ticker="TQQQ"):
    """Test Golden Cross notification."""
    print("=" * 80)
    print(f"TESTING GOLDEN CROSS NOTIFICATION FOR {ticker}")
    print("=" * 80)
    print()

    # Create mock Golden Cross signal
    signal = {
        "ticker": ticker,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "signal_type": "GOLDEN_CROSS",
        "close_price": 55.50,
        "ma5": 54.25,
        "ma30": 53.80,
    }

    print(f"Mock Signal Details:")
    print(f"  Ticker: {signal['ticker']}")
    print(f"  Date: {signal['date']}")
    print(f"  Type: {signal['signal_type']}")
    print(f"  Close Price: ${signal['close_price']:.2f}")
    print(f"  MA5: ${signal['ma5']:.2f}")
    print(f"  MA30: ${signal['ma30']:.2f}")
    print()

    # Send notifications
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("Sending notifications...")
    trigger_all_notifications(signal, timestamp)
    print()

    # Check email configuration
    print("Email Configuration:")
    print(f"  Email Enabled: {EMAIL_ENABLED}")
    if EMAIL_ENABLED:
        print(f"  Recipients: {', '.join(EMAIL_RECIPIENTS)}")
        print()
        print("✅ If email is configured correctly, you should receive an email!")
    else:
        print("  ⚠️  Email notifications are disabled in .env")
        print("     Set TQQQ_EMAIL_ENABLED=true to enable")
    print()


def test_dead_cross(ticker="YINN"):
    """Test Dead Cross notification."""
    print("=" * 80)
    print(f"TESTING DEAD CROSS NOTIFICATION FOR {ticker}")
    print("=" * 80)
    print()

    # Create mock Dead Cross signal
    signal = {
        "ticker": ticker,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "signal_type": "DEAD_CROSS",
        "close_price": 45.30,
        "ma5": 46.20,
        "ma30": 47.50,
    }

    print(f"Mock Signal Details:")
    print(f"  Ticker: {signal['ticker']}")
    print(f"  Date: {signal['date']}")
    print(f"  Type: {signal['signal_type']}")
    print(f"  Close Price: ${signal['close_price']:.2f}")
    print(f"  MA5: ${signal['ma5']:.2f}")
    print(f"  MA30: ${signal['ma30']:.2f}")
    print()

    # Send notifications
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("Sending notifications...")
    trigger_all_notifications(signal, timestamp)
    print()

    # Check email configuration
    print("Email Configuration:")
    print(f"  Email Enabled: {EMAIL_ENABLED}")
    if EMAIL_ENABLED:
        print(f"  Recipients: {', '.join(EMAIL_RECIPIENTS)}")
        print()
        print("✅ If email is configured correctly, you should receive an email!")
    else:
        print("  ⚠️  Email notifications are disabled in .env")
        print("     Set TQQQ_EMAIL_ENABLED=true to enable")
    print()


def main():
    """Run notification tests."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test notification system with mock signals"
    )
    parser.add_argument(
        "--type",
        choices=["golden", "dead", "both"],
        default="both",
        help="Type of signal to test (default: both)",
    )
    parser.add_argument(
        "--ticker",
        default="TQQQ",
        help="Ticker symbol to use in test (default: TQQQ)",
    )

    args = parser.parse_args()

    if args.type in ["golden", "both"]:
        test_golden_cross(args.ticker)

    if args.type in ["dead", "both"]:
        test_dead_cross("YINN" if args.type == "both" else args.ticker)

    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()
    print("Check your email and logs/crossover_events.log for notifications!")
    print()


if __name__ == "__main__":
    main()
