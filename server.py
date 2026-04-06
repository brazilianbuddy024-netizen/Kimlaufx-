"""
All-in-one Python HTTP server for the Telegram Signal Bot Dashboard.
Serves static HTML/CSS/JS from the Next.js static export AND handles all API routes
by calling telethon_helper.py directly — no Node.js needed.

This replaces the Next.js dev server entirely. One Python process does everything.
"""

import json
import sys
import os
import asyncio
import subprocess
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ─── Paths ───
PROJECT_DIR = Path("/home/z/my-project")
STATIC_DIR = PROJECT_DIR / "out"
TELETHON_HELPER = PROJECT_DIR / "src/lib/telethon_helper.py"
PYTHON_BIN = sys.executable  # Use the same Python that runs this server

# Ensure telethon_helper is importable
sys.path.insert(0, str(PROJECT_DIR / "src/lib"))


# ═══════════════════════════════════════════════════════════════
#  Telethon helper runner (subprocess — isolated, no import issues)
# ═══════════════════════════════════════════════════════════════

def run_telethon(action: str, params: dict = None) -> dict:
    """Run telethon_helper.py as subprocess (same pattern as Next.js API routes)."""
    if params is None:
        params = {}
    try:
        result = subprocess.run(
            [PYTHON_BIN, str(TELETHON_HELPER), action, json.dumps(params)],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        if result.stderr:
            print(f"[Telethon stderr] {result.stderr[:500]}", flush=True)
        if result.stdout.strip():
            return json.loads(result.stdout.strip())
        return {"success": False, "error": "No output from telethon helper"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Telethon operation timed out (120s)"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON from telethon helper: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
#  API Route Handlers
# ═══════════════════════════════════════════════════════════════

def handle_api_telegram_sessions(method: str, body: dict = None) -> tuple:
    """GET: list sessions, POST: logout session."""
    if method == "GET":
        result = run_telethon("list_sessions")
        return (200, result)
    elif method == "POST":
        if not body or not body.get("client_id"):
            return (400, {"success": False, "error": "Missing required field: client_id"})
        result = run_telethon("logout", {"client_id": body["client_id"]})
        return (200, result)
    return (405, {"error": "Method not allowed"})


def handle_api_telegram_send_code(body: dict) -> tuple:
    """POST: send verification code."""
    if not body.get("api_id") or not body.get("api_hash") or not body.get("phone_number"):
        return (400, {"success": False, "error": "Missing required fields: api_id, api_hash, phone_number"})
    result = run_telethon("send_code", {
        "api_id": body["api_id"],
        "api_hash": body["api_hash"],
        "phone_number": body["phone_number"],
    })
    status = 200 if result.get("success") else 400
    return (status, result)


def handle_api_telethon_verify_code(body: dict) -> tuple:
    """POST: verify code."""
    if not body.get("client_id") or not body.get("code"):
        return (400, {"success": False, "error": "Missing required fields: client_id, code"})
    result = run_telethon("verify_code", {"client_id": body["client_id"], "code": body["code"]})
    status = 200 if result.get("success") or result.get("need_password") else 400
    return (status, result)


def handle_api_telethon_verify_password(body: dict) -> tuple:
    """POST: verify 2FA password."""
    if not body.get("client_id") or not body.get("password"):
        return (400, {"success": False, "error": "Missing required fields: client_id, password"})
    result = run_telethon("verify_password", {"client_id": body["client_id"], "password": body["password"]})
    status = 200 if result.get("success") else 400
    return (status, result)


def handle_api_telethon_disconnect(body: dict) -> tuple:
    """POST: disconnect session."""
    if not body.get("client_id"):
        return (400, {"success": False, "error": "Missing required field: client_id"})
    result = run_telethon("disconnect", {"client_id": body["client_id"]})
    return (200, result)


def handle_api_channels_messages(body: dict) -> tuple:
    """POST: fetch channel messages, detect signals, post to webhook."""
    if not body.get("client_id"):
        return (400, {"success": False, "error": "Missing required field: client_id"})
    if not body.get("channels") or not isinstance(body.get("channels"), list):
        return (400, {"success": False, "error": "Missing required field: channels (array)"})
    result = run_telethon("fetch_channel_messages", {
        "client_id": body["client_id"],
        "channels": body["channels"],
        "settings": body.get("settings", {}),
    })
    status = 200 if result.get("success") else 500
    return (status, result)


def handle_api_channels_listener(method: str, body: dict = None) -> tuple:
    """WebSocket listener management (disabled in this mode)."""
    return (200, {
        "success": True,
        "running": False,
        "ws_url": "ws://127.0.0.1:8765",
        "port": 8765,
        "message": "WebSocket listener not available in Python server mode. HTTP polling is used instead.",
    })


def handle_api_webhook_send(body: dict) -> tuple:
    """POST: forward payload to external webhook URL."""
    if not body.get("url"):
        return (400, {"success": False, "error": "Missing webhook URL"})
    if not body.get("payload"):
        return (400, {"success": False, "error": "Missing webhook payload"})

    url = body["url"]
    payload = body["payload"]

    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8", errors="replace")
            return (200, {"success": True, "status": resp.status, "statusText": resp.reason, "body": resp_body})
    except HTTPError as e:
        resp_body = ""
        try:
            resp_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return (200, {"success": False, "status": e.code, "statusText": e.reason, "body": resp_body})
    except (URLError, Exception) as e:
        return (200, {"success": False, "status": 0, "statusText": "Error", "body": str(e)})


# ═══════════════════════════════════════════════════════════════
#  Route Dispatcher
# ═══════════════════════════════════════════════════════════════

def dispatch_api(path: str, method: str, body: dict = None) -> tuple:
    """Route API requests to the appropriate handler."""
    # /api/telegram/sessions
    if path == "/api/telegram/sessions":
        return handle_api_telegram_sessions(method, body)
    # /api/telegram/send-code
    if path == "/api/telegram/send-code":
        if method != "POST":
            return (405, {"error": "Method not allowed"})
        return handle_api_telegram_send_code(body)
    # /api/telegram/verify-code
    if path == "/api/telegram/verify-code":
        if method != "POST":
            return (405, {"error": "Method not allowed"})
        return handle_api_telethon_verify_code(body)
    # /api/telegram/verify-password
    if path == "/api/telegram/verify-password":
        if method != "POST":
            return (405, {"error": "Method not allowed"})
        return handle_api_telethon_verify_password(body)
    # /api/telegram/disconnect
    if path == "/api/telegram/disconnect":
        if method != "POST":
            return (405, {"error": "Method not allowed"})
        return handle_api_telethon_disconnect(body)
    # /api/channels/messages
    if path == "/api/channels/messages":
        if method != "POST":
            return (405, {"error": "Method not allowed"})
        return handle_api_channels_messages(body)
    # /api/channels/listener
    if path == "/api/channels/listener":
        return handle_api_channels_listener(method, body)
    # /api/webhook/send
    if path == "/api/webhook/send":
        if method != "POST":
            return (405, {"error": "Method not allowed"})
        return handle_api_webhook_send(body)

    return (404, {"success": False, "error": f"Unknown API route: {path}"})


# ═══════════════════════════════════════════════════════════════
#  HTTP Request Handler
# ═══════════════════════════════════════════════════════════════

class DashboardHandler(BaseHTTPRequestHandler):
    """Handles all HTTP requests — static files and API routes."""

    def log_message(self, format, *args):
        """Quiet logging — only show API calls and errors."""
        msg = format % args
        if "/api/" in msg or "error" in msg.lower() or "404" in msg:
            print(f"[HTTP] {msg}", flush=True)

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath: Path):
        """Serve a static file."""
        if not filepath.exists() or not filepath.is_file():
            self._send_file(STATIC_DIR / "index.html")
            return

        content_type, _ = mimetypes.guess_type(str(filepath))
        if content_type is None:
            content_type = "application/octet-stream"

        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Error reading file: {e}".encode())

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API routes
        if path.startswith("/api/"):
            status, data = dispatch_api(path, "GET")
            self._send_json(status, data)
            return

        # Static files
        if path == "/":
            self._send_file(STATIC_DIR / "index.html")
            return

        filepath = STATIC_DIR / path.lstrip("/")
        self._send_file(filepath)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except json.JSONDecodeError:
            body = {}

        # API routes
        if path.startswith("/api/"):
            status, data = dispatch_api(path, "POST", body)
            self._send_json(status, data)
            return

        # Non-API POST → serve index.html (SPA fallback)
        self._send_file(STATIC_DIR / "index.html")


# ═══════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════

def main():
    port = int(os.environ.get("PORT", 3000))
    host = "0.0.0.0"

    print(f"╔══════════════════════════════════════════════════╗", flush=True)
    print(f"║  Telegram Signal Bot — Python Server             ║", flush=True)
    print(f"║  Static files: {str(STATIC_DIR):<30s}║", flush=True)
    print(f"║  API handler:  Telethon (direct)                 ║", flush=True)
    print(f"║  Listening on: http://{host}:{port}                     ║", flush=True)
    print(f"╚══════════════════════════════════════════════════╝", flush=True)

    server = HTTPServer((host, port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
