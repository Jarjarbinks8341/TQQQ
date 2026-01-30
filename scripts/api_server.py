#!/usr/bin/env python3
"""Simple HTTP API server for webhook registration.

Endpoints:
    POST /webhooks          - Register a new webhook
    GET  /webhooks          - List all webhooks
    DELETE /webhooks        - Remove a webhook
    GET  /status            - Get current trading status
    GET  /health            - Health check
"""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tqqq.webhook_registry import (
    register_webhook,
    unregister_webhook,
    list_webhooks,
    toggle_webhook,
)
from tqqq.database import get_connection, get_all_tickers
from tqqq.signals import get_current_status
from tqqq.config import TICKERS


class WebhookAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhook API."""

    def _send_json_response(self, data: dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _read_json_body(self) -> dict:
        """Read and parse JSON body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode())

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)

        if path == "/health":
            self._send_json_response({"status": "ok"})

        elif path == "/webhooks":
            webhooks = list_webhooks()
            self._send_json_response({"webhooks": webhooks})

        elif path == "/tickers":
            try:
                conn = get_connection()
                db_tickers = get_all_tickers(conn)
                conn.close()
                self._send_json_response({
                    "configured_tickers": TICKERS,
                    "tracked_tickers": db_tickers
                })
            except Exception as e:
                self._send_json_response({"error": str(e)}, 500)

        elif path == "/status":
            try:
                conn = get_connection()

                # Check if specific ticker requested
                ticker_param = query_params.get("ticker", [None])[0]

                if ticker_param:
                    # Single ticker status
                    status = get_current_status(conn, ticker_param.upper())
                    conn.close()
                    self._send_json_response(status)
                else:
                    # All tickers status
                    db_tickers = get_all_tickers(conn)
                    if not db_tickers:
                        # Fallback to configured tickers if no data in DB yet
                        db_tickers = TICKERS

                    statuses = {}
                    for ticker in db_tickers:
                        try:
                            statuses[ticker] = get_current_status(conn, ticker)
                        except Exception as e:
                            statuses[ticker] = {"error": str(e)}

                    conn.close()
                    self._send_json_response({"tickers": statuses})

            except Exception as e:
                self._send_json_response({"error": str(e)}, 500)

        else:
            self._send_json_response({"error": "Not found"}, 404)

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/webhooks":
            try:
                body = self._read_json_body()
                url = body.get("url")

                if not url:
                    self._send_json_response(
                        {"error": "Missing 'url' in request body"}, 400
                    )
                    return

                if not url.startswith("https://"):
                    self._send_json_response(
                        {"error": "URL must use HTTPS"}, 400
                    )
                    return

                # Parse tickers parameter
                tickers = body.get("tickers")
                if tickers is not None and not isinstance(tickers, list):
                    self._send_json_response(
                        {"error": "'tickers' must be a list of strings"}, 400
                    )
                    return

                webhook = register_webhook(
                    url=url,
                    name=body.get("name"),
                    webhook_type=body.get("type", "generic"),
                    tickers=tickers,
                )
                self._send_json_response(
                    {"message": "Webhook registered", "webhook": webhook}, 201
                )

            except json.JSONDecodeError:
                self._send_json_response({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self._send_json_response({"error": str(e)}, 500)

        else:
            self._send_json_response({"error": "Not found"}, 404)

    def do_DELETE(self):
        """Handle DELETE requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/webhooks":
            try:
                body = self._read_json_body()
                url = body.get("url")

                if not url:
                    self._send_json_response(
                        {"error": "Missing 'url' in request body"}, 400
                    )
                    return

                if unregister_webhook(url):
                    self._send_json_response({"message": "Webhook removed"})
                else:
                    self._send_json_response({"error": "Webhook not found"}, 404)

            except json.JSONDecodeError:
                self._send_json_response({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self._send_json_response({"error": str(e)}, 500)

        else:
            self._send_json_response({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        """Log HTTP requests."""
        print(f"[API] {self.address_string()} - {format % args}")


def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the API server."""
    server = HTTPServer((host, port), WebhookAPIHandler)
    print(f"Starting TQQQ API server on http://{host}:{port}")
    print("Endpoints:")
    print("  POST   /webhooks           - Register webhook (body: {url, name?, type?, tickers?})")
    print("  GET    /webhooks           - List all webhooks")
    print("  DELETE /webhooks           - Remove webhook (body: {url})")
    print("  GET    /status             - All tickers' status")
    print("  GET    /status?ticker=TQQQ - Specific ticker status")
    print("  GET    /tickers            - List tracked tickers")
    print("  GET    /health             - Health check")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TQQQ Webhook API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    args = parser.parse_args()

    run_server(args.host, args.port)
