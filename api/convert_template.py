"""
api/convert_template.py
────────────────────────
Vercel Python serverless function – POST /api/convert_template

The browser uploads the template file directly to Supabase Storage and sends
only a small JSON body containing the public URL. This sidesteps Vercel's
4.5 MB serverless body limit for any file size.

Request body (JSON):
{
  "file_url":       "https://….supabase.co/storage/v1/object/public/…",
  "document_title": "Client Intake Form"   // optional
}

Response: application/pdf binary
Response headers include:
  X-Field-Count  – number of form fields detected and embedded
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# ── Make project root importable ───────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import requests as req_lib

from src.template_converter import convert_template_from_bytes

# ── CORS headers ───────────────────────────────────────────────────────────────
_CORS = {
    "Access-Control-Allow-Origin":   "*",
    "Access-Control-Allow-Methods":  "POST, OPTIONS",
    "Access-Control-Allow-Headers":  "Content-Type",
    "Access-Control-Expose-Headers": "X-Field-Count",
}


# ── Vercel handler ─────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # silence default access-log noise
        pass

    # ── CORS preflight ─────────────────────────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in _CORS.items():
            self.send_header(k, v)
        self.end_headers()

    # ── Main POST ──────────────────────────────────────────────────────────────
    def do_POST(self):
        # Parse request body
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)
        except Exception as exc:
            self._json_error(400, f"Invalid request body: {exc}")
            return

        file_url       = data.get("file_url", "")
        document_title = data.get("document_title", "Form")

        if not file_url:
            self._json_error(400, "file_url is required")
            return

        # Download the template from Supabase Storage
        # Strip any stray whitespace / URL-encoded newlines introduced by env-var storage
        file_url = file_url.strip().replace('\r', '').replace('\n', '')
        try:
            dl = req_lib.get(file_url, timeout=60)
            dl.raise_for_status()
            file_bytes = dl.content
            mime = dl.headers.get("Content-Type", "").split(";")[0].strip()
        except Exception as exc:
            self._json_error(502, f"Could not download template: {exc}")
            return

        # Read API key from environment
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")

        try:
            pdf_bytes, field_count = convert_template_from_bytes(
                file_bytes=file_bytes,
                mime=mime,
                document_title=document_title,
                openai_api_key=openai_api_key,
            )
        except Exception as exc:
            self._json_error(500, str(exc))
            return

        # Build a safe filename
        filename = (document_title or "form").lower().replace(" ", "_") + ".pdf"

        self.send_response(200)
        for k, v in _CORS.items():
            self.send_header(k, v)
        self.send_header("Content-Type",        "application/pdf")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length",      str(len(pdf_bytes)))
        self.send_header("X-Field-Count",       str(field_count))
        self.end_headers()
        self.wfile.write(pdf_bytes)

    # ── Error helper ───────────────────────────────────────────────────────────
    def _json_error(self, code: int, message: str) -> None:
        body = json.dumps({"error": message}).encode()
        self.send_response(code)
        for k, v in _CORS.items():
            self.send_header(k, v)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
