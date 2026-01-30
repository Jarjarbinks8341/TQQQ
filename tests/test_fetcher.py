"""Tests for tqqq.fetcher module."""

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from tqqq.fetcher import fetch_prices, fetch_all_tickers_parallel


class TestFetchPrices:
    """Tests for fetch_prices function."""

    def test_fetch_with_days_parameter(self):
        """Test fetching with days parameter."""
        # Mock yfinance to avoid real API calls in tests
        mock_df = pd.DataFrame(
            {
                "Open": [50, 51, 52],
                "High": [51, 52, 53],
                "Low": [49, 50, 51],
                "Close": [50.5, 51.5, 52.5],
                "Volume": [1000000, 1100000, 1200000],
            },
            index=pd.date_range(start="2025-01-01", periods=3),
        )

        with patch("tqqq.fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = mock_df
            df = fetch_prices("TQQQ", days=7)

            assert isinstance(df, pd.DataFrame)
            mock_ticker.return_value.history.assert_called_once()

    def test_fetch_with_start_date(self):
        """Test fetching with start_date parameter."""
        mock_df = pd.DataFrame(
            {
                "Open": [50],
                "High": [51],
                "Low": [49],
                "Close": [50.5],
                "Volume": [1000000],
            },
            index=pd.date_range(start="2025-01-15", periods=1),
        )

        with patch("tqqq.fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = mock_df
            start = datetime(2025, 1, 15)
            df = fetch_prices("TQQQ", start_date=start)

            assert isinstance(df, pd.DataFrame)
            call_kwargs = mock_ticker.return_value.history.call_args[1]
            assert call_kwargs["start"] == start

    def test_returns_dataframe(self):
        """Test that function returns a DataFrame."""
        mock_df = pd.DataFrame(
            {
                "Open": [50],
                "High": [51],
                "Low": [49],
                "Close": [50.5],
                "Volume": [1000000],
            },
            index=pd.date_range(start="2025-01-01", periods=1),
        )

        with patch("tqqq.fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = mock_df
            df = fetch_prices("TQQQ", days=1)
            assert isinstance(df, pd.DataFrame)

    def test_uses_correct_ticker(self):
        """Test that correct ticker is used."""
        with patch("tqqq.fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = pd.DataFrame()
            fetch_prices("YINN", days=1)
            mock_ticker.assert_called_with("YINN")

    def test_default_days_parameter(self):
        """Test default days parameter from config."""
        from tqqq.config import HISTORY_DAYS

        with patch("tqqq.fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = pd.DataFrame()
            fetch_prices("TQQQ")

            call_kwargs = mock_ticker.return_value.history.call_args[1]
            start_date = call_kwargs["start"]
            expected_start = datetime.now() - timedelta(days=HISTORY_DAYS)

            # Allow 1 day tolerance for test timing
            assert abs((start_date - expected_start).days) <= 1

    def test_empty_result_handling(self):
        """Test handling of empty result from API."""
        with patch("tqqq.fetcher.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = pd.DataFrame()
            df = fetch_prices("TQQQ", days=1)
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 0


class TestFetchAllTickersParallel:
    """Tests for fetch_all_tickers_parallel function."""

    def test_fetches_multiple_tickers(self):
        """Test fetching multiple tickers in parallel."""
        mock_df1 = pd.DataFrame(
            {"Open": [50], "High": [51], "Low": [49], "Close": [50.5], "Volume": [1000000]},
            index=pd.date_range(start="2025-01-01", periods=1),
        )
        mock_df2 = pd.DataFrame(
            {"Open": [30], "High": [31], "Low": [29], "Close": [30.5], "Volume": [500000]},
            index=pd.date_range(start="2025-01-01", periods=1),
        )

        with patch("tqqq.fetcher.yf.Ticker") as mock_ticker:
            def side_effect(ticker):
                mock = MagicMock()
                if ticker == "TQQQ":
                    mock.history.return_value = mock_df1
                elif ticker == "YINN":
                    mock.history.return_value = mock_df2
                return mock

            mock_ticker.side_effect = side_effect
            results = fetch_all_tickers_parallel(["TQQQ", "YINN"], days=7)

            assert len(results) == 2
            assert "TQQQ" in results
            assert "YINN" in results
            assert isinstance(results["TQQQ"], pd.DataFrame)
            assert isinstance(results["YINN"], pd.DataFrame)

    def test_handles_failures_gracefully(self):
        """Test that failures don't stop other tickers from being fetched."""
        mock_df = pd.DataFrame(
            {"Open": [50], "High": [51], "Low": [49], "Close": [50.5], "Volume": [1000000]},
            index=pd.date_range(start="2025-01-01", periods=1),
        )

        with patch("tqqq.fetcher.yf.Ticker") as mock_ticker:
            def side_effect(ticker):
                mock = MagicMock()
                if ticker == "TQQQ":
                    mock.history.return_value = mock_df
                elif ticker == "INVALID":
                    mock.history.side_effect = Exception("API Error")
                return mock

            mock_ticker.side_effect = side_effect
            results = fetch_all_tickers_parallel(["TQQQ", "INVALID"], days=7)

            # Should have TQQQ but not INVALID
            assert "TQQQ" in results
            assert "INVALID" not in results
