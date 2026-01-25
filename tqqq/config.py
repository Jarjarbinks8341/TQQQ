"""Configuration settings for TQQQ trading bot."""

import os
from pathlib import Path

# Base paths
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Database
DB_PATH = DATA_DIR / "tqqq_data.db"

# Logs
EVENTS_LOG_PATH = LOGS_DIR / "crossover_events.log"
CRON_LOG_PATH = LOGS_DIR / "cron.log"

# Moving average settings
MA_SHORT = 5
MA_LONG = 30

# Webhook (Slack/Discord)
WEBHOOK_URL = os.environ.get("TQQQ_WEBHOOK_URL", "")

# Email configuration (Gmail)
EMAIL_ENABLED = os.environ.get("TQQQ_EMAIL_ENABLED", "false").lower() == "true"
EMAIL_SENDER = os.environ.get("TQQQ_EMAIL_SENDER", "")
EMAIL_PASSWORD = os.environ.get("TQQQ_EMAIL_PASSWORD", "")
EMAIL_RECIPIENT = os.environ.get("TQQQ_EMAIL_RECIPIENT", "")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Stock settings
TICKER = "TQQQ"
HISTORY_DAYS = 365
