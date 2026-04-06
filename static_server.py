#!/usr/bin/env python3
"""
Lightweight static file server for the Telegram Signal Bot dashboard.
Serves pre-built Next.js static files so the app loads even when Node.js is down.
API routes return 503 (server unavailable) — the client handles this gracefully.
"""
import http.server
import json
import os
import sys

PORT = 3000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEXT_STATIC = os.path.join(BASE_DIR, '.next', 'static')
NEXT_SERVER_APP = os.path.join(BASE_DIR, '.next', 'server', 'app')
PUBLIC_DIR = os.path.join(BASE_DIR, 'public')

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        path = self.path.split('?')[0]

        # Serve Next.js static chunks
        if path.startswith('/_next/static/'):
            rel = path[len('/_next/static/'):]
            file_path = os.path.join(NEXT_STATIC, rel)
            if os.path.isfile(file_path):
                self.send_file(file_path, 'application/javascript')
                return
            # Try media subfolder
            file_path = os.path.join(NEXT_STATIC, 'media', rel)
            if os.path.isfile(file_path):
                self.send_file(file_path, 'font/woff2')
                return

        # Serve root page (pre-rendered HTML)
        if path == '/' or path == '':
            index_html = os.path.join(NEXT_SERVER_APP, 'index.html')
            if os.path.isfile(index_html):
                self.send_file(index_html, 'text/html')
                return

        # Serve public files (favicon, etc.)
        file_path = os.path.join(PUBLIC_DIR, path.lstrip('/'))
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            ct = {
                '.svg': 'image/svg+xml',
                '.png': 'image/png',
                '.ico': 'image/x-icon',
                '.json': 'application/json',
                '.txt': 'text/plain',
            }.get(ext, 'application/octet-stream')
            self.send_file(file_path, ct)
            return

        # API routes — return 503 (server unavailable)
        if path.startswith('/api/'):
            self.send_json_response(503, {
                'success': False,
                'error': 'Server is starting up. Please retry in a few seconds.'
            })
            return

        # 404
        self.send_error(404, 'Not Found')

    def do_POST(self):
        path = self.path.split('?')[0]
        # API routes — return 503 (server unavailable)
        if path.startswith('/api/'):
            self.send_json_response(503, {
                'success': False,
                'error': 'Server is starting up. Please retry in a few seconds.'
            })
            return
        self.send_error(404, 'Not Found')

    def send_file(self, file_path, content_type):
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'public, max-age=31536000, immutable')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))

    def send_json_response(self, code, data):
        body = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Quiet logging — only show errors
        if '200' not in str(args):
            sys.stderr.write(f"[Server] {args[0]} {args[1]} {args[2]}\n")


if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), DashboardHandler)
    print(f"Dashboard server running on http://0.0.0.0:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
