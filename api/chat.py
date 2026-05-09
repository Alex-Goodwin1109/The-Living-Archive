"""
Vercel serverless function — proxies chat requests to Groq.
GROQ_API_KEY is read from Vercel environment variables, never exposed to the client.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            payload = json.loads(body)

            groq_key = os.environ.get("GROQ_API_KEY", "")
            if not groq_key:
                self._send(500, {"error": "GROQ_API_KEY not configured on server."})
                return

            # Forward request to Groq
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {groq_key}",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            self._send(200, data)

        except urllib.error.HTTPError as e:
            err_body = e.read().decode()
            try:
                err_json = json.loads(err_body)
            except Exception:
                err_json = {"error": err_body}
            self._send(e.code, err_json)

        except Exception as e:
            self._send(500, {"error": str(e)})

    def do_OPTIONS(self):
        self._cors()
        self.send_response(200)
        self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, status: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass  # suppress default access log noise
