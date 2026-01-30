#!/usr/bin/env python3
"""Database migration script to add multi-ticker support.

This script migrates the database schema to support multiple tickers:
- Adds 'ticker' column to tqqq_prices table
- Adds 'ticker' column to crossover_signals table
- Updates primary keys and unique constraints
- Migrates existing data with ticker='TQQQ'

Usage:
    python scripts/migrate_multi_ticker.py --dry-run  # Preview changes
    python scripts/migrate_multi_ticker.py            # Run migration
    python scripts/migrate_multi_ticker.py --rollback # Rollback migration
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqqq.config import DB_PATH, LOGS_DIR


MIGRATION_LOG = LOGS_DIR / "migration.log"


def log(message: str, file=None):
    """Log message to console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    if file:
        file.write(formatted + "\n")
        file.flush()


def backup_database(db_path: Path) -> Path:
    """Create a backup of the database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def get_table_info(conn: sqlite3.Connection, table: str) -> list:
    """Get table schema information."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    return cursor.fetchall()


def check_migration_needed(conn: sqlite3.Connection) -> bool:
    """Check if migration is needed."""
    # Check if ticker column already exists in tqqq_prices
    prices_info = get_table_info(conn, "tqqq_prices")
    prices_columns = [col[1] for col in prices_info]

    if "ticker" in prices_columns:
        return False

    return True


def perform_migration(conn: sqlite3.Connection, dry_run: bool = False, log_file=None):
    """Perform the database migration."""
    cursor = conn.cursor()

    log("Starting migration process...", log_file)

    if not check_migration_needed(conn):
        log("Migration not needed - ticker column already exists", log_file)
        return True

    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    if "tqqq_prices" not in tables and "crossover_signals" not in tables:
        log("No existing tables found - migration not needed", log_file)
        return True

    # Get row counts for verification
    cursor.execute("SELECT COUNT(*) FROM tqqq_prices")
    prices_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM crossover_signals")
    signals_count = cursor.fetchone()[0]

    log(f"Found {prices_count} price records and {signals_count} signal records", log_file)

    if dry_run:
        log("DRY RUN MODE - No changes will be made", log_file)
        log("Would create new schema with ticker column", log_file)
        log(f"Would migrate {prices_count} price records with ticker='TQQQ'", log_file)
        log(f"Would migrate {signals_count} signal records with ticker='TQQQ'", log_file)
        return True

    # Step 1: Create new tables with ticker column
    log("Step 1: Creating new tables with ticker column...", log_file)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tqqq_prices_v2 (
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
        CREATE TABLE IF NOT EXISTS crossover_signals_v2 (
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

    log("New tables created successfully", log_file)

    # Step 2: Migrate data from old tables
    log("Step 2: Migrating data from old tables...", log_file)

    # Migrate prices
    cursor.execute("""
        INSERT INTO tqqq_prices_v2 (ticker, date, open, high, low, close, adj_close, volume)
        SELECT 'TQQQ', date, open, high, low, close, adj_close, volume
        FROM tqqq_prices
    """)
    migrated_prices = cursor.rowcount
    log(f"Migrated {migrated_prices} price records", log_file)

    # Migrate signals (handle both ma20 and ma30 column names for backward compatibility)
    cursor.execute("PRAGMA table_info(crossover_signals)")
    old_columns = {col[1] for col in cursor.fetchall()}

    if "ma30" in old_columns:
        # New schema already has ma30
        cursor.execute("""
            INSERT INTO crossover_signals_v2 (ticker, date, signal_type, close_price, ma5, ma30, created_at)
            SELECT 'TQQQ', date, signal_type, close_price, ma5, ma30, created_at
            FROM crossover_signals
        """)
    elif "ma20" in old_columns:
        # Old schema has ma20, map it to ma30
        cursor.execute("""
            INSERT INTO crossover_signals_v2 (ticker, date, signal_type, close_price, ma5, ma30, created_at)
            SELECT 'TQQQ', date, signal_type, close_price, ma5, ma20, created_at
            FROM crossover_signals
        """)
    else:
        # Handle case with no MA column
        cursor.execute("""
            INSERT INTO crossover_signals_v2 (ticker, date, signal_type, close_price, created_at)
            SELECT 'TQQQ', date, signal_type, close_price, created_at
            FROM crossover_signals
        """)

    migrated_signals = cursor.rowcount
    log(f"Migrated {migrated_signals} signal records", log_file)

    # Step 3: Verify migration
    log("Step 3: Verifying migration...", log_file)

    cursor.execute("SELECT COUNT(*) FROM tqqq_prices_v2")
    new_prices_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM crossover_signals_v2")
    new_signals_count = cursor.fetchone()[0]

    if new_prices_count != prices_count:
        log(f"ERROR: Price count mismatch! Old: {prices_count}, New: {new_prices_count}", log_file)
        return False

    if new_signals_count != signals_count:
        log(f"ERROR: Signal count mismatch! Old: {signals_count}, New: {new_signals_count}", log_file)
        return False

    log("Verification passed - record counts match", log_file)

    # Step 4: Backup old tables and rename new ones
    log("Step 4: Renaming tables...", log_file)

    cursor.execute("ALTER TABLE tqqq_prices RENAME TO tqqq_prices_backup")
    cursor.execute("ALTER TABLE crossover_signals RENAME TO crossover_signals_backup")
    cursor.execute("ALTER TABLE tqqq_prices_v2 RENAME TO tqqq_prices")
    cursor.execute("ALTER TABLE crossover_signals_v2 RENAME TO crossover_signals")

    log("Tables renamed successfully", log_file)

    # Commit all changes
    conn.commit()

    log("Migration completed successfully!", log_file)
    log("Old tables preserved as *_backup for safety", log_file)
    log("You can drop backup tables after verifying the migration", log_file)

    return True


def rollback_migration(conn: sqlite3.Connection, log_file=None):
    """Rollback the migration by restoring backup tables."""
    cursor = conn.cursor()

    log("Starting rollback process...", log_file)

    # Check if backup tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    if "tqqq_prices_backup" not in tables or "crossover_signals_backup" not in tables:
        log("ERROR: Backup tables not found. Cannot rollback.", log_file)
        return False

    # Drop current tables
    log("Dropping current tables...", log_file)
    cursor.execute("DROP TABLE IF EXISTS tqqq_prices")
    cursor.execute("DROP TABLE IF EXISTS crossover_signals")

    # Restore backup tables
    log("Restoring backup tables...", log_file)
    cursor.execute("ALTER TABLE tqqq_prices_backup RENAME TO tqqq_prices")
    cursor.execute("ALTER TABLE crossover_signals_backup RENAME TO crossover_signals")

    conn.commit()

    log("Rollback completed successfully!", log_file)
    return True


def main():
    """Main migration script."""
    parser = argparse.ArgumentParser(description="Migrate database to support multiple tickers")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    parser.add_argument("--rollback", action="store_true", help="Rollback migration to previous state")
    args = parser.parse_args()

    # Ensure logs directory exists
    LOGS_DIR.mkdir(exist_ok=True)

    # Open log file
    with open(MIGRATION_LOG, "a") as log_file:
        log("="*60, log_file)
        log("Database Migration Script", log_file)
        log("="*60, log_file)

        # Check if database exists
        if not DB_PATH.exists():
            log(f"Database not found at {DB_PATH}", log_file)
            log("No migration needed - new database will use new schema", log_file)
            return 0

        # Create backup before migration
        if not args.dry_run and not args.rollback:
            log(f"Creating backup of database...", log_file)
            backup_path = backup_database(DB_PATH)
            log(f"Backup created: {backup_path}", log_file)

        # Connect to database
        conn = sqlite3.connect(str(DB_PATH))

        try:
            if args.rollback:
                success = rollback_migration(conn, log_file)
            else:
                success = perform_migration(conn, dry_run=args.dry_run, log_file=log_file)

            if success:
                log("Operation completed successfully", log_file)
                return 0
            else:
                log("Operation failed", log_file)
                return 1

        except Exception as e:
            log(f"ERROR: {str(e)}", log_file)
            import traceback
            log(traceback.format_exc(), log_file)
            return 1
        finally:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
