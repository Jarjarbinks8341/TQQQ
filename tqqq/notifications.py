"""Notification services for crossover alerts."""

import json
import smtplib
import subprocess
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict

from .config import (
    EVENTS_LOG_PATH,
    WEBHOOK_URL,
    EMAIL_ENABLED,
    EMAIL_SENDER,
    EMAIL_PASSWORD,
    EMAIL_RECIPIENT,
    SMTP_SERVER,
    SMTP_PORT,
)


def format_signal_message(signal: Dict) -> tuple:
    """Format signal into message components.

    Returns:
        Tuple of (emoji, signal_name, full_message)
    """
    emoji = "🟢" if signal["signal_type"] == "GOLDEN_CROSS" else "🔴"
    signal_name = (
        "Golden Cross (BULLISH)"
        if signal["signal_type"] == "GOLDEN_CROSS"
        else "Dead Cross (BEARISH)"
    )

    message = (
        f"{emoji} TQQQ {signal_name}\n"
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
    _, signal_name, _ = format_signal_message(signal)

    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{signal_name} on {signal["date"]} - '
                f'Close: ${signal["close_price"]:.2f}" with title "TQQQ Alert"',
            ],
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


def send_webhook(signal: Dict, timestamp: str) -> bool:
    """Send webhook notification (Slack/Discord)."""
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


def send_email(subject: str, body: str, timestamp: str) -> bool:
    """Send email notification via Gmail SMTP."""
    if not EMAIL_ENABLED:
        return False

    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        print(f"[{timestamp}] Email not configured - missing credentials")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECIPIENT

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
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())

        print(f"[{timestamp}] Email sent to {EMAIL_RECIPIENT}")
        return True

    except Exception as e:
        print(f"[{timestamp}] Email failed: {e}")
        return False


def trigger_all_notifications(signal: Dict, timestamp: str) -> None:
    """Trigger all configured notification channels."""
    _, signal_name, message = format_signal_message(signal)

    # 1. Console
    log_to_console(signal, timestamp)

    # 2. File log
    log_to_file(signal, timestamp)

    # 3. macOS notification
    send_macos_notification(signal)

    # 4. Webhook
    if WEBHOOK_URL:
        send_webhook(signal, timestamp)

    # 5. Email
    if EMAIL_ENABLED:
        subject = f"TQQQ Alert: {signal_name} on {signal['date']}"
        send_email(subject, message, timestamp)
