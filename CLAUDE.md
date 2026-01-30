# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TQQQ is a trading bot that monitors multiple leveraged ETFs (TQQQ, YINN, etc.) using moving average crossover signals. It detects Golden Cross (bullish) and Dead Cross (bearish) patterns using 5-day and 30-day moving averages, and sends notifications via email, macOS desktop, or webhook (Slack/Discord/Teams). Supports tracking multiple tickers simultaneously with independent signals and per-ticker webhook subscriptions.

## Build and Test Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run tests with coverage
pytest --cov=tqqq

# Run a single test file
pytest tests/test_signals.py

# Run a specific test
pytest tests/test_signals.py::test_function_name
```

## Running the Bot

```bash
# Fetch data and check for signals (loads .env automatically)
./run.sh

# Or directly
python scripts/fetch_data.py                    # Incremental update for all configured tickers
python scripts/fetch_data.py --full             # Full 365-day fetch for all tickers
python scripts/fetch_data.py --parallel         # Parallel fetching (faster for multiple tickers)
python scripts/fetch_data.py --ticker YINN      # Process specific ticker only

# Check current status
python scripts/status.py                        # Show all tickers
python scripts/status.py --ticker TQQQ          # Show specific ticker

# Generate chart
python scripts/plot_chart.py                    # Default ticker (first in TQQQ_TICKERS)
python scripts/plot_chart.py --ticker YINN      # Specific ticker

# Run simulation
python scripts/simulate.py --start 2024-01-01 --end 2024-12-31
python scripts/simulate.py --ticker YINN --start 2024-01-01 --end 2024-12-31

# Start webhook management API server
python scripts/api_server.py --port 8080

# Database migration (if upgrading from single-ticker version)
python scripts/migrate_multi_ticker.py --dry-run  # Preview migration
python scripts/migrate_multi_ticker.py            # Run migration
```

## Deployment (Linux VM)

```bash
sudo ./deploy/install.sh   # Install app, systemd service, and cron job
```

- `deploy/install.sh` — sets up `/opt/tqqq`, venv, systemd service, cron
- `deploy/tqqq-api.service` — systemd unit for the API server (runs as `tqqq` user)
- `deploy/tqqq-cron` — cron job: runs fetch_data.py at 6 PM ET (23:00 UTC) weekdays

## Architecture

```
tqqq/
├── __init__.py         # Package init (version "1.0.0")
├── config.py           # Configuration (paths, MA settings, tickers, env vars)
├── database.py         # SQLite database operations (multi-ticker support)
├── fetcher.py          # Yahoo Finance data fetching (parallel fetching support)
├── signals.py          # MA crossover detection per ticker (Golden/Dead Cross)
├── notifications.py    # Multi-channel notifications (ticker-aware)
├── webhook_registry.py # Webhook CRUD with per-ticker subscriptions
└── fear_greed.py       # CNN Fear & Greed Index fetching

scripts/
├── fetch_data.py           # Main entry point - multi-ticker fetch, signals, notifications
├── status.py               # Display status for all or specific ticker
├── plot_chart.py           # Generate price/MA charts per ticker
├── simulate.py             # Backtest simulation per ticker
├── api_server.py           # HTTP API server for webhooks & status
├── fear_greed.py           # Fetch Fear & Greed Index
└── migrate_multi_ticker.py # Database migration script for multi-ticker upgrade

deploy/
├── install.sh       # Linux VM installation script
├── tqqq-api.service # systemd service unit for the API server
└── tqqq-cron        # Cron job for scheduled daily execution

tests/              # pytest test suite (unit + integration)
data/               # SQLite database (trading_data.db) and webhooks.json
logs/               # Event log (crossover_events.log), migration.log, and cron log
```

## API Server Endpoints

- `POST /webhooks` — Register a webhook (requires HTTPS URL; optional name, type, tickers)
- `GET /webhooks` — List all registered webhooks
- `DELETE /webhooks` — Remove a webhook by URL
- `GET /status` — Current trading status for all tickers
- `GET /status?ticker=TQQQ` — Current trading status for specific ticker
- `GET /tickers` — List configured and tracked tickers
- `GET /health` — Health check

## Key Configuration

- **MA_SHORT**: 5-day moving average
- **MA_LONG**: 30-day moving average
- **Signal types**: `GOLDEN_CROSS` (bullish), `DEAD_CROSS` (bearish)
- **Webhook types**: `generic`, `slack`, `discord`, `teams`
- **Environment variables** (see `.env.example`):
  - `TQQQ_TICKERS`: Comma-separated list of tickers to track (default: "TQQQ")
  - `TQQQ_EMAIL_ENABLED`: Enable email notifications
  - `TQQQ_EMAIL_SENDER`: Gmail sender address
  - `TQQQ_EMAIL_PASSWORD`: Gmail app password
  - `TQQQ_EMAIL_RECIPIENTS`: Comma-separated list of notification recipients
  - `TQQQ_WEBHOOK_URL`: Legacy single Slack/Discord webhook URL (optional)

## Multi-Ticker Features

- **Database Schema**: Composite primary key `(ticker, date)` for price data
- **Independent Signals**: Each ticker has separate crossover detection and signal history
- **Per-Ticker Webhooks**: Webhooks can subscribe to specific tickers or all tickers
  - Empty `tickers` array = subscribe to all tickers
  - Specified tickers array = receive only those ticker signals
- **Parallel Fetching**: Use `--parallel` flag to fetch multiple tickers simultaneously (3 workers max)
- **Backward Compatible**: Single ticker mode still works; defaults to first ticker in `TQQQ_TICKERS`
