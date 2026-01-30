"""Data fetching from Yahoo Finance."""

import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
import yfinance as yf

from .config import HISTORY_DAYS


def fetch_prices(ticker: str, start_date: datetime = None, days: int = HISTORY_DAYS) -> pd.DataFrame:
    """Fetch price data from Yahoo Finance for a specific ticker.

    Args:
        ticker: Stock ticker symbol (e.g., "TQQQ", "YINN").
        start_date: Start date for fetching. If None, fetches last `days` days.
        days: Number of days to fetch if start_date is None.

    Returns:
        DataFrame with OHLCV data.
    """
    end_date = datetime.now()

    if start_date is None:
        start_date = end_date - timedelta(days=days)

    ticker_obj = yf.Ticker(ticker)
    df = ticker_obj.history(start=start_date, end=end_date)

    return df


def fetch_all_tickers_parallel(tickers: List[str], start_date: datetime = None, days: int = HISTORY_DAYS) -> Dict[str, pd.DataFrame]:
    """Fetch multiple tickers in parallel using ThreadPoolExecutor.

    Args:
        tickers: List of ticker symbols to fetch.
        start_date: Start date for fetching. If None, fetches last `days` days.
        days: Number of days to fetch if start_date is None.

    Returns:
        Dictionary mapping ticker symbols to DataFrames with OHLCV data.
        Failed fetches are omitted from results with a warning printed.
    """
    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_ticker = {
            executor.submit(fetch_prices, ticker, start_date, days): ticker
            for ticker in tickers
        }

        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                results[ticker] = future.result()
            except Exception as e:
                print(f"Warning: Failed to fetch {ticker}: {e}")

    return results
