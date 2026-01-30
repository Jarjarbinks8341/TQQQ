"""Tests for tqqq.signals module."""

import sqlite3

import pandas as pd
import pytest

from tqqq.database import save_prices
from tqqq.signals import detect_crossovers, get_current_status


class TestDetectCrossovers:
    """Tests for detect_crossovers function."""

    def test_returns_empty_for_insufficient_data(self, temp_db):
        """Test returns empty list when not enough data."""
        conn, _ = temp_db

        # Add only 10 days of data (need at least 30 for MA30)
        dates = pd.date_range(start="2025-01-01", periods=10, freq="B")
        df = pd.DataFrame(
            {
                "Open": [50] * 10,
                "High": [51] * 10,
                "Low": [49] * 10,
                "Close": [50] * 10,
                "Volume": [1000000] * 10,
            },
            index=dates,
        )
        save_prices(conn, "TQQQ", df)

        signals = detect_crossovers(conn, "TQQQ")
        assert signals == []

    def test_detects_golden_cross(self, temp_db, sample_price_data_with_crossover):
        """Test detection of golden cross signal."""
        conn, _ = temp_db
        save_prices(conn, "TQQQ", sample_price_data_with_crossover)

        signals = detect_crossovers(conn, "TQQQ")

        golden_crosses = [s for s in signals if s["signal_type"] == "GOLDEN_CROSS"]
        assert len(golden_crosses) >= 1

    def test_detects_dead_cross(self, temp_db):
        """Test detection of dead cross signal."""
        conn, _ = temp_db

        # Create data with dead cross: rally then sharp decline
        dates = pd.date_range(start="2025-01-01", periods=40, freq="B")
        prices = (
            [20, 22, 24, 26, 28]  # Days 1-5: rally
            + [30, 32, 34, 36, 38]  # Days 6-10: rally
            + [40, 42, 44, 46, 48]  # Days 11-15: rally
            + [50, 52, 54, 56, 58]  # Days 16-20: rally
            + [60, 62, 64, 66, 68]  # Days 21-25: rally
            + [70, 72, 74, 76, 78]  # Days 26-30: rally (MA30 starts)
            + [80, 82, 84, 86, 88]  # Days 31-35: peak
            + [70, 50, 35, 20, 10]  # Days 36-40: crash to trigger dead cross
        )

        df = pd.DataFrame(
            {
                "Open": [float(p) for p in prices],
                "High": [float(p + 1) for p in prices],
                "Low": [float(p - 1) for p in prices],
                "Close": [float(p) for p in prices],
                "Volume": [1000000] * 40,
            },
            index=dates,
        )
        save_prices(conn, "TQQQ", df)

        signals = detect_crossovers(conn, "TQQQ")
        dead_crosses = [s for s in signals if s["signal_type"] == "DEAD_CROSS"]
        assert len(dead_crosses) >= 1

    def test_signal_contains_required_fields(self, temp_db, sample_price_data_with_crossover):
        """Test that signals contain all required fields."""
        conn, _ = temp_db
        save_prices(conn, "TQQQ", sample_price_data_with_crossover)

        signals = detect_crossovers(conn, "TQQQ")

        if signals:
            signal = signals[0]
            assert "ticker" in signal
            assert "date" in signal
            assert "signal_type" in signal
            assert "close_price" in signal
            assert "ma5" in signal
            assert "ma30" in signal

    def test_signal_date_format(self, temp_db, sample_price_data_with_crossover):
        """Test that signal dates are in correct format."""
        conn, _ = temp_db
        save_prices(conn, "TQQQ", sample_price_data_with_crossover)

        signals = detect_crossovers(conn, "TQQQ")

        for signal in signals:
            # Should be YYYY-MM-DD format
            assert len(signal["date"]) == 10
            assert signal["date"][4] == "-"
            assert signal["date"][7] == "-"

    def test_no_signals_in_flat_market(self, temp_db):
        """Test no crossovers detected in flat market."""
        conn, _ = temp_db

        # Create flat price data
        dates = pd.date_range(start="2025-01-01", periods=40, freq="B")
        df = pd.DataFrame(
            {
                "Open": [50] * 40,
                "High": [51] * 40,
                "Low": [49] * 40,
                "Close": [50] * 40,
                "Volume": [1000000] * 40,
            },
            index=dates,
        )
        save_prices(conn, "TQQQ", df)

        signals = detect_crossovers(conn, "TQQQ")
        assert signals == []


class TestGetCurrentStatus:
    """Tests for get_current_status function."""

    def test_returns_insufficient_data(self, temp_db):
        """Test returns insufficient data status when not enough data."""
        conn, _ = temp_db

        # Add only 10 days
        dates = pd.date_range(start="2025-01-01", periods=10, freq="B")
        df = pd.DataFrame(
            {
                "Open": [50] * 10,
                "High": [51] * 10,
                "Low": [49] * 10,
                "Close": [50] * 10,
                "Volume": [1000000] * 10,
            },
            index=dates,
        )
        save_prices(conn, "TQQQ", df)

        status = get_current_status(conn, "TQQQ")
        assert status["status"] == "INSUFFICIENT_DATA"
        assert status["ticker"] == "TQQQ"

    def test_returns_bullish_status(self, temp_db):
        """Test returns bullish status when MA5 > MA30."""
        conn, _ = temp_db

        # Create strongly uptrending data - MA5 will be above MA30
        dates = pd.date_range(start="2025-01-01", periods=40, freq="B")
        prices = [float(40 + i * 2) for i in range(40)]  # Strong uptrend: 40 to 118

        df = pd.DataFrame(
            {
                "Open": prices,
                "High": [p + 1 for p in prices],
                "Low": [p - 1 for p in prices],
                "Close": prices,
                "Volume": [1000000] * 40,
            },
            index=dates,
        )
        save_prices(conn, "TQQQ", df)

        status = get_current_status(conn, "TQQQ")
        # In an uptrend, MA5 (recent avg) should be higher than MA30 (longer avg)
        assert status["status"] == "BULLISH"
        assert status["ticker"] == "TQQQ"
        assert status["ma_short"] > status["ma_long"]

    def test_returns_bearish_status(self, temp_db):
        """Test returns bearish status when MA5 < MA30."""
        conn, _ = temp_db

        # Create downtrending data
        dates = pd.date_range(start="2025-01-01", periods=40, freq="B")
        prices = [120 - i * 2 for i in range(40)]  # Strong downtrend

        df = pd.DataFrame(
            {
                "Open": prices,
                "High": [p + 1 for p in prices],
                "Low": [p - 1 for p in prices],
                "Close": prices,
                "Volume": [1000000] * 40,
            },
            index=dates,
        )
        save_prices(conn, "TQQQ", df)

        status = get_current_status(conn, "TQQQ")
        assert status["status"] == "BEARISH"
        assert status["ticker"] == "TQQQ"

    def test_status_contains_required_fields(self, temp_db, sample_price_data):
        """Test that status contains all required fields."""
        conn, _ = temp_db
        save_prices(conn, "TQQQ", sample_price_data)

        status = get_current_status(conn, "TQQQ")

        assert "ticker" in status
        assert "date" in status
        assert "status" in status
        assert "close" in status
        assert "ma_short" in status
        assert "ma_long" in status
        assert "gap" in status

    def test_gap_calculation(self, temp_db, sample_price_data):
        """Test that gap is calculated correctly."""
        conn, _ = temp_db
        save_prices(conn, "TQQQ", sample_price_data)

        status = get_current_status(conn, "TQQQ")

        expected_gap = status["ma_short"] - status["ma_long"]
        assert abs(status["gap"] - expected_gap) < 0.01
