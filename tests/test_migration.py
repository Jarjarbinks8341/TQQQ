"""Tests for database migration script."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.migrate_multi_ticker import (
    check_migration_needed,
    perform_migration,
    rollback_migration,
)


@pytest.fixture
def old_schema_db():
    """Create a database with the old single-ticker schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Old schema without ticker column
    cursor.execute("""
        CREATE TABLE tqqq_prices (
            date TEXT PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE crossover_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            close_price REAL,
            ma5 REAL,
            ma30 REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, signal_type)
        )
    """)

    # Add some sample data
    dates = pd.date_range(start="2025-01-01", periods=10, freq="B")
    for i, date in enumerate(dates):
        cursor.execute("""
            INSERT INTO tqqq_prices (date, open, high, low, close, adj_close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            date.strftime("%Y-%m-%d"),
            float(50 + i),
            float(51 + i),
            float(49 + i),
            float(50 + i),
            float(50 + i),
            1000000,
        ))

    # Add a sample signal
    cursor.execute("""
        INSERT INTO crossover_signals (date, signal_type, close_price, ma5, ma30)
        VALUES (?, ?, ?, ?, ?)
    """, ("2025-01-15", "GOLDEN_CROSS", 55.0, 54.0, 53.0))

    conn.commit()

    yield conn, path

    conn.close()
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def new_schema_db():
    """Create a database with the new multi-ticker schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # New schema with ticker column
    cursor.execute("""
        CREATE TABLE tqqq_prices (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    """)

    cursor.execute("""
        CREATE TABLE crossover_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            close_price REAL,
            ma5 REAL,
            ma30 REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, date, signal_type)
        )
    """)

    # Add some sample data
    dates = pd.date_range(start="2025-01-01", periods=10, freq="B")
    for i, date in enumerate(dates):
        cursor.execute("""
            INSERT INTO tqqq_prices (ticker, date, open, high, low, close, adj_close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "TQQQ",
            date.strftime("%Y-%m-%d"),
            float(50 + i),
            float(51 + i),
            float(49 + i),
            float(50 + i),
            float(50 + i),
            1000000,
        ))

    # Add a sample signal
    cursor.execute("""
        INSERT INTO crossover_signals (ticker, date, signal_type, close_price, ma5, ma30)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("TQQQ", "2025-01-15", "GOLDEN_CROSS", 55.0, 54.0, 53.0))

    conn.commit()

    yield conn, path

    conn.close()
    if os.path.exists(path):
        os.unlink(path)


class TestCheckMigrationNeeded:
    """Tests for check_migration_needed function."""

    def test_old_schema_needs_migration(self, old_schema_db):
        """Test that old schema is detected as needing migration."""
        conn, _ = old_schema_db
        assert check_migration_needed(conn) is True

    def test_new_schema_no_migration(self, new_schema_db):
        """Test that new schema doesn't need migration."""
        conn, _ = new_schema_db
        assert check_migration_needed(conn) is False


class TestPerformMigration:
    """Tests for perform_migration function."""

    def test_migration_creates_new_schema(self, old_schema_db):
        """Test that migration creates the new schema."""
        conn, _ = old_schema_db

        # Perform migration
        result = perform_migration(conn, dry_run=False, log_file=None)
        assert result is True

        # Verify new schema exists
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tqqq_prices)")
        columns = {col[1] for col in cursor.fetchall()}
        assert "ticker" in columns
        assert "date" in columns

    def test_migration_preserves_data(self, old_schema_db):
        """Test that migration preserves all existing data."""
        conn, _ = old_schema_db

        # Count records before migration
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tqqq_prices")
        old_price_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM crossover_signals")
        old_signal_count = cursor.fetchone()[0]

        # Perform migration
        perform_migration(conn, dry_run=False, log_file=None)

        # Count records after migration
        cursor.execute("SELECT COUNT(*) FROM tqqq_prices")
        new_price_count = cursor.fetchone()[0]
        assert new_price_count == old_price_count

        cursor.execute("SELECT COUNT(*) FROM crossover_signals")
        new_signal_count = cursor.fetchone()[0]
        assert new_signal_count == old_signal_count

    def test_migration_adds_ticker_column(self, old_schema_db):
        """Test that migration adds ticker='TQQQ' to all records."""
        conn, _ = old_schema_db

        perform_migration(conn, dry_run=False, log_file=None)

        # Verify all records have ticker='TQQQ'
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT ticker FROM tqqq_prices")
        tickers = [row[0] for row in cursor.fetchall()]
        assert tickers == ["TQQQ"]

        cursor.execute("SELECT DISTINCT ticker FROM crossover_signals")
        signal_tickers = [row[0] for row in cursor.fetchall()]
        assert signal_tickers == ["TQQQ"]

    def test_migration_creates_backup_tables(self, old_schema_db):
        """Test that migration creates backup tables."""
        conn, _ = old_schema_db

        perform_migration(conn, dry_run=False, log_file=None)

        # Verify backup tables exist
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "tqqq_prices_backup" in tables
        assert "crossover_signals_backup" in tables

    def test_dry_run_doesnt_modify(self, old_schema_db):
        """Test that dry-run mode doesn't modify the database."""
        conn, _ = old_schema_db

        # Get table info before dry run
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tqqq_prices)")
        columns_before = {col[1] for col in cursor.fetchall()}

        # Run migration in dry-run mode
        result = perform_migration(conn, dry_run=True, log_file=None)
        assert result is True

        # Verify schema unchanged
        cursor.execute("PRAGMA table_info(tqqq_prices)")
        columns_after = {col[1] for col in cursor.fetchall()}
        assert columns_before == columns_after
        assert "ticker" not in columns_after

    def test_migration_data_integrity(self, old_schema_db):
        """Test that migration preserves data integrity."""
        conn, _ = old_schema_db

        # Get sample data before migration
        cursor = conn.cursor()
        cursor.execute("SELECT date, close FROM tqqq_prices WHERE date = '2025-01-01'")
        old_data = cursor.fetchone()

        # Perform migration
        perform_migration(conn, dry_run=False, log_file=None)

        # Verify data preserved
        cursor.execute("SELECT date, close FROM tqqq_prices WHERE ticker = 'TQQQ' AND date = '2025-01-01'")
        new_data = cursor.fetchone()

        assert old_data[0] == new_data[0]  # date
        assert old_data[1] == new_data[1]  # close


class TestRollbackMigration:
    """Tests for rollback_migration function."""

    def test_rollback_restores_old_schema(self, old_schema_db):
        """Test that rollback restores the original schema."""
        conn, _ = old_schema_db

        # Perform migration
        perform_migration(conn, dry_run=False, log_file=None)

        # Verify new schema
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tqqq_prices)")
        columns_after = {col[1] for col in cursor.fetchall()}
        assert "ticker" in columns_after

        # Rollback
        result = rollback_migration(conn, log_file=None)
        assert result is True

        # Verify old schema restored
        cursor.execute("PRAGMA table_info(tqqq_prices)")
        columns_restored = {col[1] for col in cursor.fetchall()}
        assert "ticker" not in columns_restored
        assert "date" in columns_restored

    def test_rollback_without_backup_fails(self, old_schema_db):
        """Test that rollback fails if backup tables don't exist."""
        conn, _ = old_schema_db

        # Try rollback without running migration first
        result = rollback_migration(conn, log_file=None)
        assert result is False

    def test_rollback_preserves_data(self, old_schema_db):
        """Test that rollback preserves all data."""
        conn, _ = old_schema_db

        # Count records before migration
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tqqq_prices")
        original_count = cursor.fetchone()[0]

        # Perform migration
        perform_migration(conn, dry_run=False, log_file=None)

        # Rollback
        rollback_migration(conn, log_file=None)

        # Verify count unchanged
        cursor.execute("SELECT COUNT(*) FROM tqqq_prices")
        final_count = cursor.fetchone()[0]
        assert final_count == original_count


class TestMigrationEdgeCases:
    """Tests for edge cases in migration."""

    def test_empty_database_migration(self):
        """Test migration on empty database."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()

            # Create empty old schema
            cursor.execute("""
                CREATE TABLE tqqq_prices (
                    date TEXT PRIMARY KEY,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    adj_close REAL,
                    volume INTEGER
                )
            """)

            cursor.execute("""
                CREATE TABLE crossover_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    close_price REAL,
                    ma5 REAL,
                    ma30 REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, signal_type)
                )
            """)
            conn.commit()

            # Migration should succeed even with no data
            result = perform_migration(conn, dry_run=False, log_file=None)
            assert result is True

            # Verify schema updated
            cursor.execute("PRAGMA table_info(tqqq_prices)")
            columns = {col[1] for col in cursor.fetchall()}
            assert "ticker" in columns

            conn.close()
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_migration_idempotent(self, old_schema_db):
        """Test that running migration twice doesn't cause errors."""
        conn, _ = old_schema_db

        # First migration
        result1 = perform_migration(conn, dry_run=False, log_file=None)
        assert result1 is True

        # Second migration should detect it's not needed
        result2 = perform_migration(conn, dry_run=False, log_file=None)
        assert result2 is True

        # Data should still be intact
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tqqq_prices")
        count = cursor.fetchone()[0]
        assert count == 10  # Original 10 records
