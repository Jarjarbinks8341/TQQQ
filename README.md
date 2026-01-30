# TQQQ Trading Bot

A trading bot for leveraged ETFs (TQQQ, YINN, etc.) that uses MA5/MA30 crossover signals to detect buy (Golden Cross) and sell (Dead Cross) opportunities. Supports tracking multiple tickers simultaneously with independent signals and per-ticker webhook subscriptions.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Fetch latest data and check for signals
./run.sh

# Check current market status
python scripts/status.py
```

## Running Tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run with coverage
python -m pytest --cov=tqqq
```

## Trading Simulations

Run backtests to compare the MA crossover strategy vs buy-and-hold:

```bash
# Run all trading simulations (with detailed output)
python -m pytest tests/test_integration.py::TestTradingSimulation -v -s

# Run MA crossover strategy simulation only
python -m pytest tests/test_integration.py::TestTradingSimulation::test_trading_simulation_from_jan_2025 -v -s

# Run buy-and-hold simulation only
python -m pytest tests/test_integration.py::TestTradingSimulation::test_buy_and_hold_simulation -v -s
```

### Sample Results (2020-2026)

| Strategy | Initial | Final | Return |
|----------|---------|-------|--------|
| MA Crossover | $10,000 | $50,895 | +408.95% |
| Buy & Hold | $10,000 | $50,058 | +400.58% |

The crossover strategy slightly outperformed buy-and-hold over 6 years by avoiding the 2022 bear market drawdown.

### Bear Market Performance (2022)

| Strategy | Return | Saved |
|----------|--------|-------|
| MA Crossover | -37.75% | +$4,193 |
| Buy & Hold | -79.68% | - |

## Scripts

| Script | Description | Options |
|--------|-------------|---------|
| `scripts/fetch_data.py` | Fetch data and detect signals | `--ticker TQQQ`, `--parallel`, `--full` |
| `scripts/status.py` | Show current MA status | `--ticker TQQQ` |
| `scripts/plot_chart.py` | Generate price/MA chart | `--ticker TQQQ` |
| `scripts/simulate.py` | Run crossover simulation | `--ticker TQQQ`, `--start`, `--end` |
| `scripts/api_server.py` | HTTP API for webhooks & status | `--port 8080` |

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Tickers to track (comma-separated)
TQQQ_TICKERS=TQQQ,YINN

# Email notifications (Gmail)
TQQQ_EMAIL_ENABLED=true
TQQQ_EMAIL_SENDER=your-email@gmail.com
TQQQ_EMAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx
TQQQ_EMAIL_RECIPIENTS=your-email@gmail.com,another@gmail.com

# Webhook (Slack/Discord) - optional legacy single webhook
TQQQ_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
```

### Multi-Ticker Support

The bot supports tracking multiple tickers simultaneously:

- Each ticker has independent price data and signals
- Notifications include the ticker symbol
- Webhooks can subscribe to specific tickers or all tickers
- Use `--ticker` flag to process/view individual tickers

```bash
# Fetch data for all configured tickers
python scripts/fetch_data.py

# Fetch data for a specific ticker only
python scripts/fetch_data.py --ticker YINN

# Parallel fetching for faster execution (multiple tickers)
python scripts/fetch_data.py --parallel

# View status for all tickers
python scripts/status.py

# View status for specific ticker
python scripts/status.py --ticker TQQQ
```

## VM Deployment

Deploy as a service on a Linux VM with daily cron job and webhook API.

### Quick Install

```bash
# Clone repository
git clone https://github.com/yourusername/tqqq.git
cd tqqq

# Run installer (requires root)
sudo ./deploy/install.sh
```

### What Gets Installed

- **API Server** (`systemd`): Runs on port 8080, accepts webhook registrations
- **Cron Job**: Runs daily at 6 PM ET (after market close) to fetch data and send alerts
- **Service User**: `tqqq` user with minimal permissions

### Register Webhook Endpoints

Register notification targets via HTTPS POST:

```bash
# Register a webhook (receives all tickers by default)
curl -X POST http://your-server:8080/webhooks \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app.com/tqqq-alerts", "name": "My App", "type": "generic"}'

# Register webhook for specific tickers only
curl -X POST http://your-server:8080/webhooks \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app.com/tqqq-only", "name": "TQQQ Alerts", "type": "slack", "tickers": ["TQQQ"]}'

# Supported types: generic, slack, discord, teams

# List all webhooks
curl http://your-server:8080/webhooks

# List tracked tickers
curl http://your-server:8080/tickers

# Remove a webhook
curl -X DELETE http://your-server:8080/webhooks \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app.com/tqqq-alerts"}'

# Check trading status (all tickers)
curl http://your-server:8080/status

# Check status for specific ticker
curl http://your-server:8080/status?ticker=TQQQ
```

### Webhook Payload Format

When a crossover signal is detected, registered webhooks receive:

```json
{
  "text": "🟢 TQQQ Golden Cross (BULLISH)\nDate: 2025-01-15\nClose: $55.50\nMA5: $54.00\nMA30: $53.50",
  "ticker": "TQQQ",
  "signal_type": "GOLDEN_CROSS",
  "date": "2025-01-15",
  "close_price": 55.50,
  "ma5": 54.00,
  "ma30": 53.50
}
```

**Note:** Webhooks only receive signals for tickers they're subscribed to (or all tickers if `tickers` field is empty/not specified).

### Service Management

```bash
# Check API server status
systemctl status tqqq-api

# Restart API server
systemctl restart tqqq-api

# View API logs
tail -f /var/log/tqqq/api.log

# View cron logs
tail -f /var/log/tqqq/cron.log

# Manual data fetch
sudo -u tqqq /opt/tqqq/venv/bin/python /opt/tqqq/scripts/fetch_data.py
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhooks` | Register webhook `{url, name?, type?, tickers?}` |
| GET | `/webhooks` | List all webhooks |
| DELETE | `/webhooks` | Remove webhook `{url}` |
| GET | `/status` | Current MA status for all tickers |
| GET | `/status?ticker=TQQQ` | Current MA status for specific ticker |
| GET | `/tickers` | List configured and tracked tickers |
| GET | `/health` | Health check |
