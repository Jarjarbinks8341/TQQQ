"""Notification services for crossover alerts."""

import json
import smtplib
import subprocess
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

from .config import (
    EVENTS_LOG_PATH,
    WEBHOOK_URL,
    EMAIL_ENABLED,
    EMAIL_SENDER,
    EMAIL_PASSWORD,
    EMAIL_RECIPIENTS,
    SMTP_SERVER,
    SMTP_PORT,
)
from .webhook_registry import get_enabled_webhooks


def format_signal_message(signal: Dict) -> tuple:
    """Format signal into message components.

    Returns:
        Tuple of (emoji, signal_name, full_message)
    """
    ticker = signal.get("ticker", "TQQQ")  # Backward compatible
    emoji = "🟢" if signal["signal_type"] == "GOLDEN_CROSS" else "🔴"
    signal_name = (
        "Golden Cross (BULLISH)"
        if signal["signal_type"] == "GOLDEN_CROSS"
        else "Dead Cross (BEARISH)"
    )

    message = (
        f"{emoji} {ticker} {signal_name}\n"
        f"Date: {signal['date']}\n"
        f"Close: ${signal['close_price']:.2f}\n"
        f"MA5: ${signal['ma5']:.2f}\n"
        f"MA30: ${signal['ma30']:.2f}"
    )

    return emoji, signal_name, message


def log_to_console(signal: Dict, timestamp: str) -> None:
    """Print alert to console."""
    _, _, message = format_signal_message(signal)
    print(f"\n[{timestamp}] *** CROSSOVER ALERT ***")
    print(message)


def log_to_file(signal: Dict, timestamp: str) -> None:
    """Log alert to events file."""
    with open(EVENTS_LOG_PATH, "a") as f:
        f.write(f"[{timestamp}] {signal['signal_type']} on {signal['date']}\n")
        f.write(
            f"  Close: ${signal['close_price']:.2f}, "
            f"MA5: ${signal['ma5']:.2f}, "
            f"MA30: ${signal['ma30']:.2f}\n\n"
        )


def send_macos_notification(signal: Dict) -> bool:
    """Send macOS desktop notification."""
    ticker = signal.get("ticker", "TQQQ")  # Backward compatible
    _, signal_name, _ = format_signal_message(signal)

    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{signal_name} on {signal["date"]} - '
                f'Close: ${signal["close_price"]:.2f}" with title "{ticker} Alert"',
            ],
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


def _format_webhook_payload(signal: Dict, webhook_type: str) -> dict:
    """Format payload based on webhook type."""
    ticker = signal.get("ticker", "TQQQ")  # Backward compatible
    _, signal_name, message = format_signal_message(signal)

    if webhook_type == "slack":
        return {"text": message}
    elif webhook_type == "discord":
        return {"content": message}
    elif webhook_type == "teams":
        return {
            "@type": "MessageCard",
            "summary": f"{ticker} Alert: {signal_name}",
            "text": message,
        }
    else:
        # Generic format - include all signal data
        return {
            "text": message,
            "ticker": ticker,
            "signal_type": signal["signal_type"],
            "date": signal["date"],
            "close_price": signal["close_price"],
            "ma5": signal["ma5"],
            "ma30": signal["ma30"],
        }


def send_webhook(signal: Dict, timestamp: str) -> bool:
    """Send webhook notification (Slack/Discord) - legacy single webhook."""
    if not WEBHOOK_URL:
        return False

    _, _, message = format_signal_message(signal)

    try:
        data = json.dumps({"text": message}).encode("utf-8")
        req = urllib.request.Request(
            WEBHOOK_URL, data=data, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"[{timestamp}] Webhook failed: {e}")
        return False


def send_to_registered_webhooks(signal: Dict, timestamp: str) -> int:
    """Send notification to all registered webhooks filtered by ticker subscription.

    Returns:
        Number of successful webhook calls
    """
    ticker = signal.get("ticker", "TQQQ")  # Backward compatible
    webhooks = get_enabled_webhooks(ticker=ticker)
    success_count = 0

    for webhook in webhooks:
        url = webhook["url"]
        webhook_type = webhook.get("type", "generic")
        name = webhook.get("name", url)

        try:
            payload = _format_webhook_payload(signal, webhook_type)
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=10)
            print(f"[{timestamp}] Webhook sent to {name}")
            success_count += 1
        except Exception as e:
            print(f"[{timestamp}] Webhook failed ({name}): {e}")

    return success_count


def send_email(subject: str, body: str, timestamp: str) -> bool:
    """Send email notification via Gmail SMTP to all configured recipients."""
    if not EMAIL_ENABLED:
        return False

    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENTS]):
        print(f"[{timestamp}] Email not configured - missing credentials")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = ", ".join(EMAIL_RECIPIENTS)

        # Plain text version
        text_part = MIMEText(body, "plain")
        msg.attach(text_part)

        # HTML version
        html_body = body.replace("\n", "<br>")
        html_part = MIMEText(
            f"<html><body><p>{html_body}</p></body></html>", "html"
        )
        msg.attach(html_part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENTS, msg.as_string())

        print(f"[{timestamp}] Email sent to {', '.join(EMAIL_RECIPIENTS)}")
        return True

    except Exception as e:
        print(f"[{timestamp}] Email failed: {e}")
        return False


def trigger_all_notifications(signal: Dict, timestamp: str) -> None:
    """Trigger all configured notification channels."""
    ticker = signal.get("ticker", "TQQQ")  # Backward compatible
    _, signal_name, message = format_signal_message(signal)

    # 1. Console
    log_to_console(signal, timestamp)

    # 2. File log
    log_to_file(signal, timestamp)

    # 3. macOS notification (only on macOS)
    send_macos_notification(signal)

    # 4. Legacy single webhook (from env var)
    if WEBHOOK_URL:
        send_webhook(signal, timestamp)

    # 5. Registered webhooks (from API/file) - filtered by ticker
    webhook_count = send_to_registered_webhooks(signal, timestamp)
    if webhook_count > 0:
        print(f"[{timestamp}] Sent to {webhook_count} registered webhook(s)")

    # 6. Email
    if EMAIL_ENABLED:
        subject = f"{ticker} Alert: {signal_name} on {signal['date']}"
        send_email(subject, message, timestamp)
