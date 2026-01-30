"""Webhook registry for managing notification targets."""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from .config import DATA_DIR

WEBHOOKS_FILE = DATA_DIR / "webhooks.json"


def load_webhooks() -> List[Dict]:
    """Load registered webhooks from file."""
    if not WEBHOOKS_FILE.exists():
        return []

    try:
        with open(WEBHOOKS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_webhooks(webhooks: List[Dict]) -> None:
    """Save webhooks to file."""
    with open(WEBHOOKS_FILE, "w") as f:
        json.dump(webhooks, f, indent=2)


def register_webhook(url: str, name: Optional[str] = None,
                     webhook_type: str = "generic",
                     tickers: Optional[List[str]] = None) -> Dict:
    """Register a new webhook URL.

    Args:
        url: The webhook URL (HTTPS POST endpoint)
        name: Optional friendly name for the webhook
        webhook_type: Type of webhook (generic, slack, discord, teams)
        tickers: Optional list of tickers to subscribe to. Empty list = subscribe to all tickers.

    Returns:
        The registered webhook entry
    """
    webhooks = load_webhooks()

    # Check if URL already exists
    for wh in webhooks:
        if wh["url"] == url:
            # Update existing
            wh["name"] = name or wh.get("name", "")
            wh["type"] = webhook_type
            wh["tickers"] = tickers if tickers is not None else wh.get("tickers", [])
            wh["updated_at"] = datetime.now().isoformat()
            save_webhooks(webhooks)
            return wh

    # Add new webhook
    webhook = {
        "id": len(webhooks) + 1,
        "url": url,
        "name": name or f"Webhook {len(webhooks) + 1}",
        "type": webhook_type,
        "enabled": True,
        "tickers": tickers or [],  # Empty list = subscribe to all tickers
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    webhooks.append(webhook)
    save_webhooks(webhooks)
    return webhook


def unregister_webhook(url: str) -> bool:
    """Remove a webhook by URL.

    Returns:
        True if webhook was found and removed
    """
    webhooks = load_webhooks()
    original_len = len(webhooks)
    webhooks = [wh for wh in webhooks if wh["url"] != url]

    if len(webhooks) < original_len:
        save_webhooks(webhooks)
        return True
    return False


def get_enabled_webhooks(ticker: Optional[str] = None) -> List[Dict]:
    """Get all enabled webhooks, optionally filtered by ticker subscription.

    Args:
        ticker: Optional ticker to filter webhooks. If provided, only returns webhooks
                that either have an empty tickers list (subscribed to all) or include
                this specific ticker in their tickers list.

    Returns:
        List of enabled webhook dictionaries.
    """
    webhooks = load_webhooks()
    enabled = [wh for wh in webhooks if wh.get("enabled", True)]

    if ticker:
        # Filter by ticker subscription: empty tickers list = subscribe to all
        return [
            wh for wh in enabled
            if not wh.get("tickers") or ticker in wh.get("tickers", [])
        ]

    return enabled


def toggle_webhook(url: str, enabled: bool) -> bool:
    """Enable or disable a webhook.

    Returns:
        True if webhook was found and updated
    """
    webhooks = load_webhooks()
    for wh in webhooks:
        if wh["url"] == url:
            wh["enabled"] = enabled
            wh["updated_at"] = datetime.now().isoformat()
            save_webhooks(webhooks)
            return True
    return False


def list_webhooks() -> List[Dict]:
    """List all registered webhooks."""
    return load_webhooks()
