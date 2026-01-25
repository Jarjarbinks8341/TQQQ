"""Tests for tqqq.notifications module."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from tqqq.notifications import (
    format_signal_message,
    log_to_console,
    log_to_file,
    send_macos_notification,
    send_webhook,
    send_email,
    trigger_all_notifications,
)


class TestFormatSignalMessage:
    """Tests for format_signal_message function."""

    def test_golden_cross_formatting(self, sample_signal):
        """Test formatting of golden cross signal."""
        emoji, signal_name, message = format_signal_message(sample_signal)

        assert emoji == "🟢"
        assert "Golden Cross" in signal_name
        assert "BULLISH" in signal_name
        assert sample_signal["date"] in message
        assert f"${sample_signal['close_price']:.2f}" in message

    def test_dead_cross_formatting(self, sample_dead_cross_signal):
        """Test formatting of dead cross signal."""
        emoji, signal_name, message = format_signal_message(sample_dead_cross_signal)

        assert emoji == "🔴"
        assert "Dead Cross" in signal_name
        assert "BEARISH" in signal_name

    def test_message_contains_all_values(self, sample_signal):
        """Test that message contains all signal values."""
        _, _, message = format_signal_message(sample_signal)

        assert sample_signal["date"] in message
        assert f"${sample_signal['close_price']:.2f}" in message
        assert f"${sample_signal['ma5']:.2f}" in message
        assert f"${sample_signal['ma30']:.2f}" in message


class TestLogToConsole:
    """Tests for log_to_console function."""

    def test_prints_alert(self, sample_signal, capsys):
        """Test that alert is printed to console."""
        log_to_console(sample_signal, "2025-01-15 18:00:00")

        captured = capsys.readouterr()
        assert "CROSSOVER ALERT" in captured.out
        assert sample_signal["date"] in captured.out

    def test_prints_timestamp(self, sample_signal, capsys):
        """Test that timestamp is included."""
        timestamp = "2025-01-15 18:00:00"
        log_to_console(sample_signal, timestamp)

        captured = capsys.readouterr()
        assert timestamp in captured.out


class TestLogToFile:
    """Tests for log_to_file function."""

    def test_writes_to_file(self, sample_signal):
        """Test that signal is written to log file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            temp_path = f.name

        try:
            with patch("tqqq.notifications.EVENTS_LOG_PATH", temp_path):
                log_to_file(sample_signal, "2025-01-15 18:00:00")

            with open(temp_path) as f:
                content = f.read()

            assert sample_signal["signal_type"] in content
            assert sample_signal["date"] in content
        finally:
            os.unlink(temp_path)

    def test_appends_to_existing_file(self, sample_signal, sample_dead_cross_signal):
        """Test that logs are appended, not overwritten."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            temp_path = f.name

        try:
            with patch("tqqq.notifications.EVENTS_LOG_PATH", temp_path):
                log_to_file(sample_signal, "2025-01-15 18:00:00")
                log_to_file(sample_dead_cross_signal, "2025-01-20 18:00:00")

            with open(temp_path) as f:
                content = f.read()

            assert "GOLDEN_CROSS" in content
            assert "DEAD_CROSS" in content
        finally:
            os.unlink(temp_path)


class TestSendMacosNotification:
    """Tests for send_macos_notification function."""

    def test_calls_osascript(self, sample_signal):
        """Test that osascript is called."""
        with patch("tqqq.notifications.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            result = send_macos_notification(sample_signal)

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "osascript"

    def test_returns_true_on_success(self, sample_signal):
        """Test returns True on successful notification."""
        with patch("tqqq.notifications.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            result = send_macos_notification(sample_signal)
            assert result is True

    def test_returns_false_on_failure(self, sample_signal):
        """Test returns False on failure."""
        with patch("tqqq.notifications.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Command failed")
            result = send_macos_notification(sample_signal)
            assert result is False


class TestSendWebhook:
    """Tests for send_webhook function."""

    def test_returns_false_when_not_configured(self, sample_signal):
        """Test returns False when webhook URL not configured."""
        with patch("tqqq.notifications.WEBHOOK_URL", ""):
            result = send_webhook(sample_signal, "2025-01-15 18:00:00")
            assert result is False

    def test_sends_request_when_configured(self, sample_signal):
        """Test sends HTTP request when webhook is configured."""
        with patch("tqqq.notifications.WEBHOOK_URL", "https://example.com/webhook"):
            with patch("tqqq.notifications.urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value = MagicMock()
                result = send_webhook(sample_signal, "2025-01-15 18:00:00")
                assert result is True
                mock_urlopen.assert_called_once()

    def test_returns_false_on_request_failure(self, sample_signal):
        """Test returns False when request fails."""
        with patch("tqqq.notifications.WEBHOOK_URL", "https://example.com/webhook"):
            with patch("tqqq.notifications.urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = Exception("Request failed")
                result = send_webhook(sample_signal, "2025-01-15 18:00:00")
                assert result is False


class TestSendEmail:
    """Tests for send_email function."""

    def test_returns_false_when_disabled(self):
        """Test returns False when email is disabled."""
        with patch("tqqq.notifications.EMAIL_ENABLED", False):
            result = send_email("Test", "Body", "2025-01-15 18:00:00")
            assert result is False

    def test_returns_false_when_credentials_missing(self):
        """Test returns False when credentials are missing."""
        with patch("tqqq.notifications.EMAIL_ENABLED", True):
            with patch("tqqq.notifications.EMAIL_SENDER", ""):
                result = send_email("Test", "Body", "2025-01-15 18:00:00")
                assert result is False

    def test_sends_email_when_configured(self):
        """Test sends email when properly configured."""
        with patch("tqqq.notifications.EMAIL_ENABLED", True):
            with patch("tqqq.notifications.EMAIL_SENDER", "sender@test.com"):
                with patch("tqqq.notifications.EMAIL_PASSWORD", "password"):
                    with patch("tqqq.notifications.EMAIL_RECIPIENT", "recipient@test.com"):
                        with patch("tqqq.notifications.smtplib.SMTP") as mock_smtp:
                            mock_server = MagicMock()
                            mock_smtp.return_value.__enter__.return_value = mock_server

                            result = send_email("Test Subject", "Test Body", "2025-01-15 18:00:00")

                            assert result is True
                            mock_server.starttls.assert_called_once()
                            mock_server.login.assert_called_once()
                            mock_server.sendmail.assert_called_once()

    def test_returns_false_on_smtp_failure(self):
        """Test returns False when SMTP fails."""
        with patch("tqqq.notifications.EMAIL_ENABLED", True):
            with patch("tqqq.notifications.EMAIL_SENDER", "sender@test.com"):
                with patch("tqqq.notifications.EMAIL_PASSWORD", "password"):
                    with patch("tqqq.notifications.EMAIL_RECIPIENT", "recipient@test.com"):
                        with patch("tqqq.notifications.smtplib.SMTP") as mock_smtp:
                            mock_smtp.return_value.__enter__.side_effect = Exception("SMTP Error")

                            result = send_email("Test", "Body", "2025-01-15 18:00:00")
                            assert result is False


class TestTriggerAllNotifications:
    """Tests for trigger_all_notifications function."""

    def test_calls_all_notification_methods(self, sample_signal):
        """Test that all notification methods are called."""
        with patch("tqqq.notifications.log_to_console") as mock_console:
            with patch("tqqq.notifications.log_to_file") as mock_file:
                with patch("tqqq.notifications.send_macos_notification") as mock_macos:
                    with patch("tqqq.notifications.WEBHOOK_URL", ""):
                        with patch("tqqq.notifications.EMAIL_ENABLED", False):
                            trigger_all_notifications(sample_signal, "2025-01-15 18:00:00")

                            mock_console.assert_called_once()
                            mock_file.assert_called_once()
                            mock_macos.assert_called_once()

    def test_sends_webhook_when_configured(self, sample_signal):
        """Test webhook is sent when configured."""
        with patch("tqqq.notifications.log_to_console"):
            with patch("tqqq.notifications.log_to_file"):
                with patch("tqqq.notifications.send_macos_notification"):
                    with patch("tqqq.notifications.WEBHOOK_URL", "https://example.com"):
                        with patch("tqqq.notifications.send_webhook") as mock_webhook:
                            with patch("tqqq.notifications.EMAIL_ENABLED", False):
                                trigger_all_notifications(sample_signal, "2025-01-15 18:00:00")
                                mock_webhook.assert_called_once()

    def test_sends_email_when_enabled(self, sample_signal):
        """Test email is sent when enabled."""
        with patch("tqqq.notifications.log_to_console"):
            with patch("tqqq.notifications.log_to_file"):
                with patch("tqqq.notifications.send_macos_notification"):
                    with patch("tqqq.notifications.WEBHOOK_URL", ""):
                        with patch("tqqq.notifications.EMAIL_ENABLED", True):
                            with patch("tqqq.notifications.send_email") as mock_email:
                                trigger_all_notifications(sample_signal, "2025-01-15 18:00:00")
                                mock_email.assert_called_once()
