"""Tests for tqqq.config module."""

import os
from pathlib import Path

import pytest


class TestConfig:
    """Tests for configuration settings."""

    def test_root_dir_exists(self):
        """Test that ROOT_DIR points to valid directory."""
        from tqqq.config import ROOT_DIR

        assert ROOT_DIR.exists()
        assert ROOT_DIR.is_dir()

    def test_data_dir_exists(self):
        """Test that DATA_DIR is created."""
        from tqqq.config import DATA_DIR

        assert DATA_DIR.exists()
        assert DATA_DIR.is_dir()

    def test_logs_dir_exists(self):
        """Test that LOGS_DIR is created."""
        from tqqq.config import LOGS_DIR

        assert LOGS_DIR.exists()
        assert LOGS_DIR.is_dir()

    def test_db_path_in_data_dir(self):
        """Test that DB_PATH is inside DATA_DIR."""
        from tqqq.config import DB_PATH, DATA_DIR

        assert DB_PATH.parent == DATA_DIR
        assert DB_PATH.suffix == ".db"

    def test_moving_average_settings(self):
        """Test moving average configuration values."""
        from tqqq.config import MA_SHORT, MA_LONG

        assert MA_SHORT == 5
        assert MA_LONG == 20
        assert MA_SHORT < MA_LONG

    def test_ticker_setting(self):
        """Test ticker symbol configuration."""
        from tqqq.config import TICKER

        assert TICKER == "TQQQ"

    def test_history_days_setting(self):
        """Test history days configuration."""
        from tqqq.config import HISTORY_DAYS

        assert HISTORY_DAYS == 365
        assert HISTORY_DAYS > 0

    def test_smtp_settings(self):
        """Test SMTP configuration values."""
        from tqqq.config import SMTP_SERVER, SMTP_PORT

        assert SMTP_SERVER == "smtp.gmail.com"
        assert SMTP_PORT == 587

    def test_email_disabled_by_default(self):
        """Test that email is disabled by default."""
        # Clear environment variable
        original = os.environ.get("TQQQ_EMAIL_ENABLED")
        os.environ.pop("TQQQ_EMAIL_ENABLED", None)

        # Reimport to get fresh value
        import importlib
        import tqqq.config

        importlib.reload(tqqq.config)

        # Restore original
        if original:
            os.environ["TQQQ_EMAIL_ENABLED"] = original

    def test_email_enabled_from_env(self):
        """Test that email can be enabled via environment."""
        original = os.environ.get("TQQQ_EMAIL_ENABLED")
        os.environ["TQQQ_EMAIL_ENABLED"] = "true"

        import importlib
        import tqqq.config

        importlib.reload(tqqq.config)
        assert tqqq.config.EMAIL_ENABLED is True

        # Restore
        if original:
            os.environ["TQQQ_EMAIL_ENABLED"] = original
        else:
            os.environ.pop("TQQQ_EMAIL_ENABLED", None)

        importlib.reload(tqqq.config)
