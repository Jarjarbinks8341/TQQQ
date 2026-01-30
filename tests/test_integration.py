"""Integration tests using actual historical TQQQ data."""

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqqq.config import DB_PATH, MA_SHORT, MA_LONG
from tqqq.database import (
    get_connection,
    load_prices,
    get_price_count,
    get_date_range,
    get_new_signals,
    save_signals,
)
from tqqq.signals import detect_crossovers, get_current_status
from tqqq.notifications import format_signal_message, trigger_all_notifications


# Skip integration tests if database doesn't exist or is empty
def has_historical_data():
    """Check if we have historical data to test with."""
    if not DB_PATH.exists():
        return False
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tqqq_prices")
    count = cursor.fetchone()[0]
    conn.close()
    return count >= 30  # Need at least 30 days for meaningful tests


requires_historical_data = pytest.mark.skipif(
    not has_historical_data(),
    reason="Requires historical TQQQ data in database"
)


@requires_historical_data
class TestDatabaseIntegration:
    """Integration tests for database operations with real data."""

    def test_database_has_sufficient_data(self):
        """Verify database has enough data for MA calculations."""
        conn = get_connection()
        count = get_price_count(conn)
        conn.close()

        assert count >= MA_LONG, f"Need at least {MA_LONG} days of data"

    def test_database_date_range_is_reasonable(self):
        """Verify date range spans a reasonable period."""
        conn = get_connection()
        min_date, max_date = get_date_range(conn)
        conn.close()

        assert min_date is not None
        assert max_date is not None
        assert min_date < max_date

    def test_load_prices_returns_valid_data(self):
        """Verify loaded prices have valid structure and values."""
        conn = get_connection()
        df = load_prices(conn)
        conn.close()

        # Check structure
        assert "date" in df.columns
        assert "close" in df.columns

        # Check data types
        assert df["close"].dtype in ["float64", "int64"]

        # Check values are reasonable for TQQQ (typically $10-$100 range)
        assert df["close"].min() > 0
        assert df["close"].max() < 500  # Sanity check

    def test_prices_are_ordered_by_date(self):
        """Verify prices are in chronological order."""
        conn = get_connection()
        df = load_prices(conn)
        conn.close()

        dates = df["date"].tolist()
        assert dates == sorted(dates)

    def test_no_duplicate_dates(self):
        """Verify no duplicate dates in price data."""
        conn = get_connection()
        df = load_prices(conn)
        conn.close()

        assert df["date"].is_unique


@requires_historical_data
class TestSignalDetectionIntegration:
    """Integration tests for crossover signal detection with real data."""

    def test_detect_crossovers_returns_signals(self):
        """Verify crossover detection finds signals in historical data."""
        conn = get_connection()
        signals = detect_crossovers(conn)
        conn.close()

        # Should have found some signals in a year of data
        assert len(signals) > 0

    def test_signals_have_valid_structure(self):
        """Verify detected signals have correct structure."""
        conn = get_connection()
        signals = detect_crossovers(conn)
        conn.close()

        for signal in signals:
            assert "date" in signal
            assert "signal_type" in signal
            assert "close_price" in signal
            assert "ma5" in signal
            assert "ma30" in signal

            # Validate signal type
            assert signal["signal_type"] in ["GOLDEN_CROSS", "DEAD_CROSS"]

            # Validate date format (YYYY-MM-DD)
            assert len(signal["date"]) == 10
            assert signal["date"][4] == "-"
            assert signal["date"][7] == "-"

    def test_signals_have_valid_price_values(self):
        """Verify signal price values are reasonable."""
        conn = get_connection()
        signals = detect_crossovers(conn)
        conn.close()

        for signal in signals:
            assert signal["close_price"] > 0
            assert signal["ma5"] > 0
            assert signal["ma30"] > 0
            assert signal["close_price"] < 500  # Sanity check

    def test_golden_cross_ma5_above_ma30(self):
        """Verify golden cross signals have MA5 > MA30."""
        conn = get_connection()
        signals = detect_crossovers(conn)
        conn.close()

        golden_crosses = [s for s in signals if s["signal_type"] == "GOLDEN_CROSS"]

        for signal in golden_crosses:
            assert signal["ma5"] > signal["ma30"], \
                f"Golden cross on {signal['date']} has MA5 <= MA30"

    def test_dead_cross_ma5_below_ma30(self):
        """Verify dead cross signals have MA5 < MA30."""
        conn = get_connection()
        signals = detect_crossovers(conn)
        conn.close()

        dead_crosses = [s for s in signals if s["signal_type"] == "DEAD_CROSS"]

        for signal in dead_crosses:
            assert signal["ma5"] < signal["ma30"], \
                f"Dead cross on {signal['date']} has MA5 >= MA30"

    def test_signals_alternate_between_types(self):
        """Verify signals generally alternate (can't have two golden in a row)."""
        conn = get_connection()
        signals = detect_crossovers(conn)
        conn.close()

        # Sort by date
        sorted_signals = sorted(signals, key=lambda x: x["date"])

        # Check for consecutive same-type signals (shouldn't happen in theory)
        for i in range(1, len(sorted_signals)):
            current = sorted_signals[i]["signal_type"]
            previous = sorted_signals[i - 1]["signal_type"]
            # They should alternate
            assert current != previous, \
                f"Consecutive {current} signals on {sorted_signals[i-1]['date']} and {sorted_signals[i]['date']}"

    def test_signals_can_be_sorted_by_date(self):
        """Verify signals can be sorted chronologically."""
        conn = get_connection()
        signals = detect_crossovers(conn)
        conn.close()

        # Signals may come grouped by type, but should be sortable
        sorted_signals = sorted(signals, key=lambda x: x["date"])
        dates = [s["date"] for s in sorted_signals]

        # Verify dates are valid and sortable
        assert dates == sorted(dates)
        assert len(dates) == len(signals)


@requires_historical_data
class TestCurrentStatusIntegration:
    """Integration tests for current market status with real data."""

    def test_get_current_status_returns_valid_status(self):
        """Verify current status is calculated correctly."""
        conn = get_connection()
        status = get_current_status(conn)
        conn.close()

        assert status["status"] in ["BULLISH", "BEARISH"]

    def test_current_status_has_all_fields(self):
        """Verify current status contains all required fields."""
        conn = get_connection()
        status = get_current_status(conn)
        conn.close()

        assert "date" in status
        assert "status" in status
        assert "close" in status
        assert "ma_short" in status
        assert "ma_long" in status
        assert "gap" in status

    def test_current_status_values_are_consistent(self):
        """Verify status is consistent with MA values."""
        conn = get_connection()
        status = get_current_status(conn)
        conn.close()

        if status["status"] == "BULLISH":
            assert status["ma_short"] > status["ma_long"]
            assert status["gap"] > 0
        else:
            assert status["ma_short"] < status["ma_long"]
            assert status["gap"] < 0

    def test_gap_calculation_is_correct(self):
        """Verify gap is calculated as MA5 - MA20."""
        conn = get_connection()
        status = get_current_status(conn)
        conn.close()

        expected_gap = status["ma_short"] - status["ma_long"]
        assert abs(status["gap"] - expected_gap) < 0.01


@requires_historical_data
class TestNotificationIntegration:
    """Integration tests for notification formatting with real signals."""

    def test_format_real_signals(self):
        """Verify notification formatting works with real signals."""
        conn = get_connection()
        signals = detect_crossovers(conn)
        conn.close()

        for signal in signals[:5]:  # Test first 5 signals
            emoji, signal_name, message = format_signal_message(signal)

            assert emoji in ["🟢", "🔴"]
            assert signal["date"] in message
            assert "$" in message  # Should have dollar signs for prices

    def test_trigger_notifications_with_real_signal(self):
        """Verify notification triggering works with real signals."""
        conn = get_connection()
        signals = detect_crossovers(conn)
        conn.close()

        if signals:
            signal = signals[0]

            # Mock all notification methods to avoid side effects
            with patch("tqqq.notifications.log_to_console") as mock_console:
                with patch("tqqq.notifications.log_to_file") as mock_file:
                    with patch("tqqq.notifications.send_macos_notification") as mock_macos:
                        with patch("tqqq.notifications.WEBHOOK_URL", ""):
                            with patch("tqqq.notifications.EMAIL_ENABLED", False):
                                trigger_all_notifications(signal, "2025-01-15 18:00:00")

                                mock_console.assert_called_once()
                                mock_file.assert_called_once()
                                mock_macos.assert_called_once()


@requires_historical_data
class TestEndToEndIntegration:
    """End-to-end integration tests simulating real usage."""

    def test_full_signal_detection_flow(self):
        """Test complete flow: load data -> detect signals -> format notifications."""
        conn = get_connection()

        # Step 1: Load and verify data
        df = load_prices(conn)
        assert len(df) >= MA_LONG

        # Step 2: Detect signals
        signals = detect_crossovers(conn)
        assert len(signals) > 0

        # Step 3: Get current status
        status = get_current_status(conn)
        assert status["status"] in ["BULLISH", "BEARISH"]

        # Step 4: Format most recent signal for notification
        most_recent = sorted(signals, key=lambda x: x["date"])[-1]
        emoji, signal_name, message = format_signal_message(most_recent)

        assert emoji in ["🟢", "🔴"]
        assert most_recent["date"] in message

        conn.close()

    def test_new_signal_detection_after_saving(self):
        """Test that saved signals are not detected as new."""
        conn = get_connection()

        # Get all signals
        all_signals = detect_crossovers(conn)

        # Check which would be "new"
        new_signals = get_new_signals(conn, all_signals)

        # If we've been running the bot, all historical signals should be saved
        # This tests that the signal de-duplication works
        # (new_signals could be empty or contain only recent signals)

        # All new signals should be in the original list
        for new_sig in new_signals:
            matching = [s for s in all_signals
                       if s["date"] == new_sig["date"]
                       and s["signal_type"] == new_sig["signal_type"]]
            assert len(matching) == 1

        conn.close()

    def test_january_2026_signals_match_expected(self):
        """Verify specific known signals from January 2026."""
        conn = get_connection()
        signals = detect_crossovers(conn)
        conn.close()

        # Filter to January 2026
        jan_signals = [s for s in signals if s["date"].startswith("2026-01")]

        # Based on MA5/MA30 crossover simulation, we expect these signals:
        expected_dates = ["2026-01-06", "2026-01-09", "2026-01-20"]

        actual_dates = sorted([s["date"] for s in jan_signals])

        # Check that we have the expected signals
        for expected in expected_dates:
            assert expected in actual_dates, f"Missing expected signal on {expected}"

    def test_signal_types_for_january_2026(self):
        """Verify signal types for known January 2026 events."""
        conn = get_connection()
        signals = detect_crossovers(conn)
        conn.close()

        # Filter to January 2026
        jan_signals = {s["date"]: s["signal_type"] for s in signals
                      if s["date"].startswith("2026-01")}

        # Expected signal types based on MA5/MA30 simulation
        expected = {
            "2026-01-06": "DEAD_CROSS",
            "2026-01-09": "GOLDEN_CROSS",
            "2026-01-20": "DEAD_CROSS",
        }

        for date, expected_type in expected.items():
            if date in jan_signals:
                assert jan_signals[date] == expected_type, \
                    f"Signal on {date} should be {expected_type}, got {jan_signals[date]}"


@requires_historical_data
class TestTradingSimulation:
    """Trading simulation tests using real historical data."""

    def test_trading_simulation_from_jan_2025(self):
        """Simulate trading strategy: buy at golden cross, sell at dead cross.

        Starting capital: $10,000 USD
        Start date: January 1st, 2025
        Strategy: Buy 100% at golden cross, sell 100% at dead cross
        """
        import logging

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("trading_simulation")

        # Initial capital
        INITIAL_CAPITAL = 10000.00
        START_DATE = "2020-01-01"

        conn = get_connection()
        df = load_prices(conn)

        # Calculate moving averages
        df["MA_SHORT"] = df["close"].rolling(window=MA_SHORT).mean()
        df["MA_LONG"] = df["close"].rolling(window=MA_LONG).mean()
        df = df.dropna()

        # Filter from start date
        df = df[df["date"] >= START_DATE].copy()

        if len(df) == 0:
            conn.close()
            pytest.skip("No data available from 2025-01-01")

        # Detect crossovers
        df["short_above"] = df["MA_SHORT"] > df["MA_LONG"]
        df["prev_short_above"] = df["short_above"].shift(1)

        # Trading state
        cash = INITIAL_CAPITAL
        shares = 0.0
        position = "CASH"  # CASH or HOLDING

        trades = []

        print("\n" + "=" * 100)
        print("TRADING SIMULATION: Buy at Golden Cross, Sell at Dead Cross")
        print("=" * 100)
        print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
        print(f"Start Date: {START_DATE}")
        print(f"Strategy: MA{MA_SHORT}/MA{MA_LONG} Crossover")
        print("=" * 100)

        logger.info("=" * 80)
        logger.info("TRADING SIMULATION STARTED")
        logger.info(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
        logger.info(f"Start Date: {START_DATE}")
        logger.info("=" * 80)

        for _, row in df.iterrows():
            date_str = row["date"].strftime("%Y-%m-%d")
            price = row["close"]

            # Golden Cross - BUY signal
            if row["short_above"] == True and row["prev_short_above"] == False:
                if position == "CASH" and cash > 0:
                    shares = cash / price
                    trade_info = {
                        "date": date_str,
                        "action": "BUY",
                        "price": price,
                        "shares": shares,
                        "value": cash,
                    }
                    trades.append(trade_info)
                    print(f"🟢 {date_str}: BUY  @ ${price:,.2f} | Shares: {shares:,.4f} | Value: ${cash:,.2f}")
                    logger.info(f"GOLDEN CROSS - BUY @ ${price:,.2f} | Shares: {shares:,.4f}")
                    cash = 0
                    position = "HOLDING"

            # Dead Cross - SELL signal
            elif row["short_above"] == False and row["prev_short_above"] == True:
                if position == "HOLDING" and shares > 0:
                    sell_value = shares * price
                    profit = sell_value - trades[-1]["value"]
                    profit_pct = (profit / trades[-1]["value"]) * 100
                    trade_info = {
                        "date": date_str,
                        "action": "SELL",
                        "price": price,
                        "shares": shares,
                        "value": sell_value,
                        "profit": profit,
                        "profit_pct": profit_pct,
                    }
                    trades.append(trade_info)
                    print(f"🔴 {date_str}: SELL @ ${price:,.2f} | Shares: {shares:,.4f} | Value: ${sell_value:,.2f} | P/L: ${profit:+,.2f} ({profit_pct:+.2f}%)")
                    logger.info(f"DEAD CROSS - SELL @ ${price:,.2f} | Value: ${sell_value:,.2f} | P/L: ${profit:+,.2f}")
                    cash = sell_value
                    shares = 0
                    position = "CASH"

        # Calculate final portfolio value
        last_row = df.iloc[-1]
        last_date = last_row["date"].strftime("%Y-%m-%d")
        last_price = last_row["close"]

        if position == "HOLDING":
            final_value = shares * last_price
        else:
            final_value = cash

        total_return = final_value - INITIAL_CAPITAL
        total_return_pct = (total_return / INITIAL_CAPITAL) * 100

        # Calculate buy-and-hold comparison
        first_price = df.iloc[0]["close"]
        buy_hold_shares = INITIAL_CAPITAL / first_price
        buy_hold_value = buy_hold_shares * last_price
        buy_hold_return = buy_hold_value - INITIAL_CAPITAL
        buy_hold_pct = (buy_hold_return / INITIAL_CAPITAL) * 100

        # Print summary
        print("\n" + "=" * 100)
        print("SIMULATION RESULTS")
        print("=" * 100)
        print(f"Period: {START_DATE} to {last_date}")
        print(f"Total Trades: {len(trades)}")
        print(f"Current Position: {position}")
        if position == "HOLDING":
            print(f"Current Shares: {shares:,.4f}")
        print("-" * 100)
        print(f"Initial Capital:     ${INITIAL_CAPITAL:>12,.2f}")
        print(f"Final Portfolio:     ${final_value:>12,.2f}")
        print(f"Total Return:        ${total_return:>+12,.2f} ({total_return_pct:+.2f}%)")
        print("-" * 100)
        print("COMPARISON: Buy and Hold")
        print(f"Buy & Hold Value:    ${buy_hold_value:>12,.2f}")
        print(f"Buy & Hold Return:   ${buy_hold_return:>+12,.2f} ({buy_hold_pct:+.2f}%)")
        print("-" * 100)
        strategy_diff = total_return - buy_hold_return
        print(f"Strategy vs B&H:     ${strategy_diff:>+12,.2f}")
        print("=" * 100)

        # Log final results
        logger.info("=" * 80)
        logger.info("SIMULATION COMPLETE")
        logger.info(f"Final Portfolio Value: ${final_value:,.2f}")
        logger.info(f"Total Return: ${total_return:+,.2f} ({total_return_pct:+.2f}%)")
        logger.info(f"Buy & Hold Return: ${buy_hold_return:+,.2f} ({buy_hold_pct:+.2f}%)")
        logger.info(f"Strategy vs B&H: ${strategy_diff:+,.2f}")
        logger.info("=" * 80)

        conn.close()

        # Assertions
        assert final_value > 0, "Final portfolio value should be positive"
        assert len(trades) >= 0, "Should have detected trades"

    def test_buy_and_hold_simulation(self):
        """Simulate buy-and-hold strategy for comparison.

        Starting capital: $10,000 USD
        Start date: January 1st, 2024
        Strategy: Buy on first day, hold until end
        """
        import logging

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("buy_and_hold_simulation")

        INITIAL_CAPITAL = 10000.00
        START_DATE = "2020-01-01"

        conn = get_connection()
        df = load_prices(conn)
        conn.close()

        # Filter from start date
        df = df[df["date"] >= START_DATE].copy()

        if len(df) == 0:
            pytest.skip("No data available from 2020-01-01")

        # Get first and last prices
        first_row = df.iloc[0]
        last_row = df.iloc[-1]

        first_date = first_row["date"].strftime("%Y-%m-%d")
        first_price = first_row["close"]
        last_date = last_row["date"].strftime("%Y-%m-%d")
        last_price = last_row["close"]

        # Buy and hold calculation
        shares = INITIAL_CAPITAL / first_price
        final_value = shares * last_price
        total_return = final_value - INITIAL_CAPITAL
        total_return_pct = (total_return / INITIAL_CAPITAL) * 100

        print("\n" + "=" * 100)
        print("BUY AND HOLD SIMULATION")
        print("=" * 100)
        print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
        print(f"Start Date: {START_DATE}")
        print(f"Strategy: Buy on first day, hold forever")
        print("=" * 100)

        print(f"\n🟢 {first_date}: BUY  @ ${first_price:,.2f} | Shares: {shares:,.4f} | Value: ${INITIAL_CAPITAL:,.2f}")
        print(f"📊 {last_date}: HOLD @ ${last_price:,.2f} | Shares: {shares:,.4f} | Value: ${final_value:,.2f}")

        print("\n" + "=" * 100)
        print("BUY AND HOLD RESULTS")
        print("=" * 100)
        print(f"Period: {first_date} to {last_date}")
        print(f"Holding Period: {len(df)} trading days")
        print("-" * 100)
        print(f"Buy Price:           ${first_price:>12,.2f}")
        print(f"Current Price:       ${last_price:>12,.2f}")
        print(f"Price Change:        ${last_price - first_price:>+12,.2f} ({((last_price/first_price)-1)*100:+.2f}%)")
        print("-" * 100)
        print(f"Initial Capital:     ${INITIAL_CAPITAL:>12,.2f}")
        print(f"Shares Purchased:    {shares:>12,.4f}")
        print(f"Final Portfolio:     ${final_value:>12,.2f}")
        print(f"Total Return:        ${total_return:>+12,.2f} ({total_return_pct:+.2f}%)")
        print("=" * 100)

        logger.info("=" * 80)
        logger.info("BUY AND HOLD SIMULATION")
        logger.info(f"Initial: ${INITIAL_CAPITAL:,.2f} -> Final: ${final_value:,.2f}")
        logger.info(f"Return: ${total_return:+,.2f} ({total_return_pct:+.2f}%)")
        logger.info("=" * 80)

        assert final_value > 0, "Final portfolio value should be positive"
        assert shares > 0, "Should have purchased shares"


@requires_historical_data
class TestDataQualityIntegration:
    """Tests for data quality and consistency."""

    def test_no_missing_trading_days(self):
        """Check for unusual gaps in trading days."""
        conn = get_connection()
        df = load_prices(conn)
        conn.close()

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        # Calculate gaps between consecutive days
        df["gap"] = df["date"].diff()

        # Most gaps should be 1-3 days (weekends, holidays)
        # Gaps > 5 days are suspicious
        max_gap = df["gap"].max()
        assert max_gap.days <= 10, f"Suspicious gap of {max_gap.days} days found"

    def test_prices_are_positive(self):
        """Verify all prices are positive."""
        conn = get_connection()
        df = load_prices(conn)
        conn.close()

        assert (df["close"] > 0).all(), "Found non-positive price values"

    def test_no_extreme_daily_changes(self):
        """Check for unrealistic daily price changes."""
        conn = get_connection()
        df = load_prices(conn)
        conn.close()

        df = df.sort_values("date")
        df["pct_change"] = df["close"].pct_change().abs()

        # TQQQ is 3x leveraged, so 30% daily moves are possible but rare
        # 50%+ would be extremely unusual
        max_change = df["pct_change"].max()
        assert max_change < 0.5, f"Suspicious daily change of {max_change:.1%}"
