"""Data fetching from Yahoo Finance."""

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from .config import TICKER, HISTORY_DAYS


def fetch_prices(start_date: datetime = None, days: int = HISTORY_DAYS) -> pd.DataFrame:
    """Fetch TQQQ price data from Yahoo Finance.

    Args:
        start_date: Start date for fetching. If None, fetches last `days` days.
        days: Number of days to fetch if start_date is None.

    Returns:
        DataFrame with OHLCV data.
    """
    end_date = datetime.now()

    if start_date is None:
        start_date = end_date - timedelta(days=days)

    ticker = yf.Ticker(TICKER)
    df = ticker.history(start=start_date, end=end_date)

    return df
