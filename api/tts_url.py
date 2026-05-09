"""
Vercel serverless — returns TTS server URL to the frontend.
Set TTS_SERVER_URL in Vercel environment variables dashboard.
"""
from http.server import BaseHTTPRequestHandler
import json
import os


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = os.environ.get("TTS_SERVER_URL", "http://localhost:8000")
        self._send(200, {"tts_server_url": url})

    def do_OPTIONS(self):
        self._cors()
        self.send_response(200)
        self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass
