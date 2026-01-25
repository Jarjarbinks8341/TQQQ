"""Tests for tqqq.database module."""

import sqlite3
from datetime import datetime

import pandas as pd
import pytest

from tqqq.database import (
    get_connection,
    get_last_date,
    save_prices,
    load_prices,
    get_new_signals,
    save_signals,
    get_price_count,
    get_date_range,
)


class TestGetConnection:
    """Tests for get_connection function."""

    def test_returns_connection(self):
        """Test that get_connection returns a valid connection."""
        conn = get_connection()
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_creates_tables(self):
        """Test that tables are created on connection."""
        conn = get_connection()
        cursor = conn.cursor()

        # Check tqqq_prices table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tqqq_prices'"
        )
        assert cursor.fetchone() is not None

        # Check crossover_signals table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='crossover_signals'"
        )
        assert cursor.fetchone() is not None

        conn.close()


class TestGetLastDate:
    """Tests for get_last_date function."""

    def test_returns_none_for_empty_db(self, temp_db):
        """Test returns None when database is empty."""
        conn, _ = temp_db
        result = get_last_date(conn)
        assert result is None

    def test_returns_max_date(self, populated_db):
        """Test returns the most recent date."""
        conn, _ = populated_db
        result = get_last_date(conn)
        assert result is not None
        # Should be the last business day in our 40-day sample
        assert result == "2025-02-25"


class TestSavePrices:
    """Tests for save_prices function."""

    def test_saves_prices(self, temp_db, sample_price_data):
        """Test that prices are saved correctly."""
        conn, _ = temp_db
        rows = save_prices(conn, sample_price_data)
        assert rows == 40

    def test_updates_existing_prices(self, temp_db, sample_price_data):
        """Test that existing prices are updated."""
        conn, _ = temp_db

        # Save initial data
        save_prices(conn, sample_price_data)

        # Modify and save again
        modified_data = sample_price_data.copy()
        modified_data["Close"] = modified_data["Close"] + 10
        rows = save_prices(conn, modified_data)

        assert rows == 40

        # Verify data was updated
        cursor = conn.cursor()
        cursor.execute("SELECT close FROM tqqq_prices WHERE date = '2025-01-01'")
        result = cursor.fetchone()[0]
        assert result == 60.0  # Original 50.0 + 10

    def test_returns_correct_count(self, temp_db, sample_price_data):
        """Test that correct row count is returned."""
        conn, _ = temp_db
        rows = save_prices(conn, sample_price_data)
        assert rows == len(sample_price_data)


class TestLoadPrices:
    """Tests for load_prices function."""

    def test_loads_prices(self, populated_db):
        """Test that prices are loaded correctly."""
        conn, _ = populated_db
        df = load_prices(conn)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 40
        assert "date" in df.columns
        assert "close" in df.columns

    def test_returns_empty_for_empty_db(self, temp_db):
        """Test returns empty DataFrame for empty database."""
        conn, _ = temp_db
        df = load_prices(conn)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_ordered_by_date(self, populated_db):
        """Test that results are ordered by date."""
        conn, _ = populated_db
        df = load_prices(conn)

        dates = df["date"].tolist()
        assert dates == sorted(dates)


class TestGetNewSignals:
    """Tests for get_new_signals function."""

    def test_returns_all_for_empty_db(self, temp_db, sample_signal):
        """Test all signals are new when database is empty."""
        conn, _ = temp_db
        signals = [sample_signal]
        new_signals = get_new_signals(conn, signals)
        assert len(new_signals) == 1

    def test_filters_existing_signals(self, temp_db, sample_signal):
        """Test that existing signals are filtered out."""
        conn, _ = temp_db

        # Save the signal first
        save_signals(conn, [sample_signal])

        # Try to get new signals
        new_signals = get_new_signals(conn, [sample_signal])
        assert len(new_signals) == 0

    def test_returns_only_new_signals(self, temp_db, sample_signal, sample_dead_cross_signal):
        """Test returns only signals not in database."""
        conn, _ = temp_db

        # Save one signal
        save_signals(conn, [sample_signal])

        # Check both signals
        signals = [sample_signal, sample_dead_cross_signal]
        new_signals = get_new_signals(conn, signals)

        assert len(new_signals) == 1
        assert new_signals[0]["signal_type"] == "DEAD_CROSS"


class TestSaveSignals:
    """Tests for save_signals function."""

    def test_saves_signal(self, temp_db, sample_signal):
        """Test that signal is saved correctly."""
        conn, _ = temp_db
        saved = save_signals(conn, [sample_signal])
        assert saved == 1

    def test_ignores_duplicates(self, temp_db, sample_signal):
        """Test that duplicate signals are ignored."""
        conn, _ = temp_db

        save_signals(conn, [sample_signal])
        saved = save_signals(conn, [sample_signal])

        assert saved == 0

    def test_saves_multiple_signals(self, temp_db, sample_signal, sample_dead_cross_signal):
        """Test saving multiple signals."""
        conn, _ = temp_db
        signals = [sample_signal, sample_dead_cross_signal]
        saved = save_signals(conn, signals)
        assert saved == 2


class TestGetPriceCount:
    """Tests for get_price_count function."""

    def test_returns_zero_for_empty_db(self, temp_db):
        """Test returns 0 for empty database."""
        conn, _ = temp_db
        count = get_price_count(conn)
        assert count == 0

    def test_returns_correct_count(self, populated_db):
        """Test returns correct count."""
        conn, _ = populated_db
        count = get_price_count(conn)
        assert count == 40


class TestGetDateRange:
    """Tests for get_date_range function."""

    def test_returns_none_for_empty_db(self, temp_db):
        """Test returns None for empty database."""
        conn, _ = temp_db
        min_date, max_date = get_date_range(conn)
        assert min_date is None
        assert max_date is None

    def test_returns_correct_range(self, populated_db):
        """Test returns correct date range."""
        conn, _ = populated_db
        min_date, max_date = get_date_range(conn)
        assert min_date == "2025-01-01"
        assert max_date == "2025-02-25"
