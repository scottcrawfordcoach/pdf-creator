"""
api/convert_template.py
────────────────────────
Vercel Python serverless function – POST /api/convert-template

Receives a pre-designed PNG form image (base64), uses GPT-4o Vision to detect
every empty input box, and returns a fillable PDF with the original design
preserved as a background and transparent AcroForm fields overlaid at every
detected position.

Request body (JSON):
{
  "image_data":     "data:image/png;base64,…",   // base64 PNG (data-URI ok)
  "document_title": "Client Intake Form"          // optional
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

from src.template_converter import convert_template

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

        image_data     = data.get("file_data") or data.get("image_data", "")
        document_title = data.get("document_title", "Form")

        if not image_data:
            self._json_error(400, "file_data is required")
            return

        # Read API key from environment
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")

        try:
            pdf_bytes, field_count = convert_template(
                file_b64=image_data,
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
