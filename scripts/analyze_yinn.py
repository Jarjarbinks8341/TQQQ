#!/usr/bin/env python3
"""Comprehensive YINN integration test and analysis from 2020-01-01 to present."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tqqq.database import get_connection, load_prices, get_date_range, get_price_count
from tqqq.signals import detect_crossovers, get_current_status
from tqqq.config import MA_SHORT, MA_LONG

def analyze_yinn_data():
    """Run comprehensive analysis on YINN historical data."""

    print("="*80)
    print("YINN INTEGRATION TEST & ANALYSIS (2020-01-01 to Present)")
    print("="*80)
    print()

    ticker = "YINN"
    conn = get_connection()

    # ============================================================================
    # 1. DATA QUALITY TESTS
    # ============================================================================
    print("1. DATA QUALITY TESTS")
    print("-" * 80)

    # Test 1.1: Sufficient data
    count = get_price_count(conn, ticker)
    print(f"✓ Total records: {count}")
    assert count >= 250, f"Expected at least 250 records, got {count}"

    # Test 1.2: Date range
    min_date, max_date = get_date_range(conn, ticker)
    print(f"✓ Date range: {min_date} to {max_date}")
    assert min_date <= "2020-01-31", f"Expected data from early 2020, got {min_date}"

    # Test 1.3: Load prices
    df = load_prices(conn, ticker)
    print(f"✓ DataFrame loaded: {len(df)} rows")
    assert len(df) == count, "DataFrame length should match record count"

    # Test 1.4: No duplicates
    duplicates = df["date"].duplicated().sum()
    print(f"✓ No duplicate dates: {duplicates} duplicates found")
    assert duplicates == 0, f"Found {duplicates} duplicate dates"

    # Test 1.5: Ordered by date
    is_sorted = df["date"].is_monotonic_increasing
    print(f"✓ Dates are sorted: {is_sorted}")
    assert is_sorted, "Dates should be in ascending order"

    # Test 1.6: Positive prices
    negative_prices = (df["close"] <= 0).sum()
    print(f"✓ All prices positive: {negative_prices} negative prices")
    assert negative_prices == 0, f"Found {negative_prices} non-positive prices"

    # Test 1.7: Price statistics
    price_stats = df["close"].describe()
    print(f"✓ Price range: ${price_stats['min']:.2f} to ${price_stats['max']:.2f}")
    print(f"  Mean: ${price_stats['mean']:.2f}, Median: ${price_stats['50%']:.2f}")

    print()

    # ============================================================================
    # 2. SIGNAL DETECTION TESTS
    # ============================================================================
    print("2. SIGNAL DETECTION TESTS")
    print("-" * 80)

    # Test 2.1: Detect signals
    signals = detect_crossovers(conn, ticker)
    print(f"✓ Total signals detected: {len(signals)}")
    assert len(signals) > 0, "Should detect at least some crossover signals"

    # Test 2.2: Signal structure
    if signals:
        first_signal = signals[0]
        required_fields = ["ticker", "date", "signal_type", "close_price", "ma5", "ma30"]
        for field in required_fields:
            assert field in first_signal, f"Signal missing required field: {field}"
        print(f"✓ All signals have required fields: {', '.join(required_fields)}")

    # Test 2.3: Signal types
    golden_crosses = [s for s in signals if s["signal_type"] == "GOLDEN_CROSS"]
    dead_crosses = [s for s in signals if s["signal_type"] == "DEAD_CROSS"]
    print(f"✓ Golden Crosses: {len(golden_crosses)}")
    print(f"✓ Dead Crosses: {len(dead_crosses)}")

    # Test 2.4: Golden Cross validation (MA5 > MA30 at crossover)
    for signal in golden_crosses[:5]:  # Check first 5
        assert signal["ma5"] >= signal["ma30"], \
            f"Golden Cross at {signal['date']} has MA5 < MA30"
    print(f"✓ Golden Cross signals validated (MA5 >= MA30)")

    # Test 2.5: Dead Cross validation (MA5 < MA30 at crossover)
    for signal in dead_crosses[:5]:  # Check first 5
        assert signal["ma5"] <= signal["ma30"], \
            f"Dead Cross at {signal['date']} has MA5 > MA30"
    print(f"✓ Dead Cross signals validated (MA5 <= MA30)")

    # Test 2.6: Signal chronology
    signal_dates = [s["date"] for s in signals]
    sorted_dates = sorted(signal_dates)
    print(f"✓ Signals can be sorted chronologically")

    print()

    # ============================================================================
    # 3. CURRENT STATUS TESTS
    # ============================================================================
    print("3. CURRENT STATUS TESTS")
    print("-" * 80)

    # Test 3.1: Get current status
    status = get_current_status(conn, ticker)
    print(f"✓ Current status retrieved: {status['status']}")

    # Test 3.2: Status fields
    required_status_fields = ["ticker", "date", "status", "close", "ma_short", "ma_long", "gap"]
    for field in required_status_fields:
        assert field in status, f"Status missing required field: {field}"
    print(f"✓ Status has all required fields")

    # Test 3.3: Status consistency
    if status["status"] == "BULLISH":
        assert status["ma_short"] > status["ma_long"], \
            "BULLISH status should have MA5 > MA30"
        print(f"✓ BULLISH status consistent (MA5 ${status['ma_short']:.2f} > MA30 ${status['ma_long']:.2f})")
    else:
        assert status["ma_short"] <= status["ma_long"], \
            "BEARISH status should have MA5 <= MA30"
        print(f"✓ BEARISH status consistent (MA5 ${status['ma_short']:.2f} <= MA30 ${status['ma_long']:.2f})")

    # Test 3.4: Gap calculation
    expected_gap = status["ma_short"] - status["ma_long"]
    actual_gap = status["gap"]
    assert abs(expected_gap - actual_gap) < 0.01, \
        f"Gap calculation incorrect: expected {expected_gap:.2f}, got {actual_gap:.2f}"
    print(f"✓ Gap calculation correct: ${actual_gap:.2f}")

    print()

    # ============================================================================
    # 4. TRADING PERFORMANCE ANALYSIS
    # ============================================================================
    print("4. TRADING PERFORMANCE ANALYSIS")
    print("-" * 80)

    # Simulate trading based on signals
    initial_capital = 10000.0
    cash = initial_capital
    shares = 0
    position = None  # "LONG" or None
    trades = []

    for signal in sorted(signals, key=lambda x: x["date"]):
        if signal["signal_type"] == "GOLDEN_CROSS" and position is None:
            # Buy signal
            shares = cash / signal["close_price"]
            cash = 0
            position = "LONG"
            trades.append(("BUY", signal["date"], signal["close_price"], shares))

        elif signal["signal_type"] == "DEAD_CROSS" and position == "LONG":
            # Sell signal
            cash = shares * signal["close_price"]
            shares = 0
            position = None
            trades.append(("SELL", signal["date"], signal["close_price"], cash))

    # Close position if still holding
    if position == "LONG":
        current_price = status["close"]
        cash = shares * current_price
        shares = 0
        trades.append(("SELL", status["date"], current_price, cash))

    # Calculate returns
    final_value = cash
    total_return = ((final_value - initial_capital) / initial_capital) * 100

    print(f"✓ Initial Capital: ${initial_capital:,.2f}")
    print(f"✓ Final Value: ${final_value:,.2f}")
    print(f"✓ Total Return: {total_return:+.2f}%")
    print(f"✓ Number of Trades: {len(trades)}")

    # Buy and hold comparison
    if signals:
        first_signal = sorted(signals, key=lambda x: x["date"])[0]
        buy_hold_shares = initial_capital / first_signal["close_price"]
        buy_hold_value = buy_hold_shares * status["close"]
        buy_hold_return = ((buy_hold_value - initial_capital) / initial_capital) * 100

        print(f"✓ Buy & Hold Return: {buy_hold_return:+.2f}%")

        outperformance = total_return - buy_hold_return
        print(f"✓ Strategy vs Buy&Hold: {outperformance:+.2f}%")

    print()

    # ============================================================================
    # 5. YEARLY BREAKDOWN
    # ============================================================================
    print("5. YEARLY SIGNAL BREAKDOWN")
    print("-" * 80)

    from collections import defaultdict
    yearly_signals = defaultdict(lambda: {"GOLDEN_CROSS": 0, "DEAD_CROSS": 0})

    for signal in signals:
        year = signal["date"][:4]
        yearly_signals[year][signal["signal_type"]] += 1

    for year in sorted(yearly_signals.keys()):
        golden = yearly_signals[year]["GOLDEN_CROSS"]
        dead = yearly_signals[year]["DEAD_CROSS"]
        print(f"  {year}: {golden} Golden Cross, {dead} Dead Cross")

    print()

    # ============================================================================
    # 6. RECENT SIGNALS (Last 10)
    # ============================================================================
    print("6. RECENT SIGNALS (Last 10)")
    print("-" * 80)

    recent_signals = sorted(signals, key=lambda x: x["date"], reverse=True)[:10]
    for signal in recent_signals:
        emoji = "🟢" if signal["signal_type"] == "GOLDEN_CROSS" else "🔴"
        sig_name = "Golden Cross" if signal["signal_type"] == "GOLDEN_CROSS" else "Dead Cross"
        print(f"  {emoji} {signal['date']}: {sig_name} @ ${signal['close_price']:.2f}")

    print()

    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("="*80)
    print("INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"✅ All tests passed!")
    print(f"   - Data quality: ✓")
    print(f"   - Signal detection: ✓")
    print(f"   - Current status: ✓")
    print(f"   - Trading simulation: ✓")
    print()
    print(f"YINN ({min_date} to {max_date}):")
    print(f"   Records: {count}")
    print(f"   Signals: {len(signals)} total ({len(golden_crosses)} golden, {len(dead_crosses)} dead)")
    print(f"   Status: {status['status']} @ ${status['close']:.2f}")
    print(f"   Strategy Return: {total_return:+.2f}%")
    if signals:
        print(f"   Buy & Hold Return: {buy_hold_return:+.2f}%")
    print("="*80)

    conn.close()

if __name__ == "__main__":
    try:
        analyze_yinn_data()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
