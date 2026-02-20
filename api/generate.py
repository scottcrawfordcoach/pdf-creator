"""
api/generate.py
───────────────
Vercel Python serverless function – POST /api/generate

Receives a JSON body, downloads brand image files from Supabase public URLs,
runs GPT-4o brand analysis (optional), builds a branded fillable PDF using the
existing src/ modules, and returns the PDF as a binary response.

Request body (JSON):
{
  "company_name":   "Acme Corp",
  "document_title": "Client Intake Form",
  "copy_text":      "We need a form that captures contact details, project scope, timeline and a signature.",
  "page_size":      "a4",          // or "letter"
  "footer_text":    "Acme · Confidential · 2026",
  "file_urls":      ["https://…/logo.png", "https://…/inspiration.jpg"],
  "use_ai":         true
}

Response: application/pdf binary
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import base64
import binascii
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import List

# ── Make project root importable so we can use src.* ──────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.branding import BrandTheme, default_theme, theme_from_logo
from src.pdf_builder import PDFBuilder
from src.utils import build_minimal_config

try:
    from src.ai_enhancer import BrandEnhancement, enhance_brand, hex_to_rgb
    _AI_AVAILABLE = True
except ImportError:
    _AI_AVAILABLE = False

# ── CORS headers sent with every response ─────────────────────────────────────
_CORS = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


# ── Vercel handler class ───────────────────────────────────────────────────────

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

        # Generate PDF
        try:
            pdf_bytes = _run(data)
        except Exception as exc:
            self._json_error(500, str(exc))
            return

        # Build a safe filename from the document title
        raw_title = data.get("document_title") or data.get("company_name") or "document"
        filename  = raw_title.lower().replace(" ", "_") + ".pdf"

        self.send_response(200)
        for k, v in _CORS.items():
            self.send_header(k, v)
        self.send_header("Content-Type",        "application/pdf")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length",      str(len(pdf_bytes)))
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


# ── Core generation logic (runs inside a temp directory) ──────────────────────

def _run(data: dict) -> bytes:
    company_name   = data.get("company_name", "")
    document_title = data.get("document_title", "Document")
    copy_text      = data.get("copy_text", "")
    page_size      = data.get("page_size", "letter")
    footer_text    = data.get("footer_text", "")
    # Changed from file_urls to file_data (base64 strings)
    file_data      = data.get("file_data", [])
    use_ai         = bool(data.get("use_ai", True)) and _AI_AVAILABLE

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path    = os.path.join(tmpdir, "output.pdf")
        
        # Save base64 images to temp files
        local_files = _save_base64_files(file_data, tmpdir)
        logo_path   = local_files[0] if local_files else ""

        # ── AI path ────────────────────────────────────────────────────────────
        if use_ai and (copy_text or local_files):
            enhancement: BrandEnhancement = enhance_brand(
                image_paths=local_files,
                copy_text=copy_text,
                company_name=company_name,
                document_title=document_title,
            )
            cfg = {
                "logo":              logo_path,
                "company_name":      company_name,
                "document_title":    enhancement.document_title,
                "document_subtitle": enhancement.document_subtitle,
                "footer_text":       enhancement.footer_text or footer_text,
                "page_size":         page_size,
                "output":            out_path,
                "sections":          enhancement.sections,
            }
        else:
            # ── Fallback: build a sensible default config ──────────────────────
            cfg = build_minimal_config(
                logo=logo_path,
                company=company_name,
                title=document_title,
                output=out_path,
            )
            if footer_text:
                cfg["footer_text"] = footer_text
            cfg["page_size"] = page_size
            enhancement = None  # type: ignore[assignment]

        # ── Build colour theme ─────────────────────────────────────────────────
        if logo_path and os.path.exists(logo_path):
            theme = theme_from_logo(logo_path)
            # Let the AI colour suggestions refine the algorithmically-derived theme
            if use_ai and enhancement is not None:
                _apply_ai_colors(theme, enhancement)
        else:
            theme = default_theme()
            if use_ai and enhancement is not None:
                _apply_ai_colors(theme, enhancement)

        # ── Render ─────────────────────────────────────────────────────────────
        PDFBuilder(cfg, theme).build(out_path)

        with open(out_path, "rb") as fh:
            return fh.read()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _save_base64_files(b64_list: List[str], dest: str) -> List[str]:
    """Decode base64 strings and save them to *dest*. Returns local file paths."""
    paths: List[str] = []
    for i, b64_str in enumerate(b64_list):
        if not b64_str:
            continue
            
        # Handle data URI scheme if present (e.g. "data:image/png;base64,.....")
        if "," in b64_str:
            header, b64_str = b64_str.split(",", 1)
            # Try to guess extension from header
            ext = ".png" # default
            if "image/jpeg" in header: ext = ".jpg"
            elif "image/png" in header: ext = ".png"
        else:
            ext = ".png"

        try:
            file_data = base64.b64decode(b64_str)
            local_path = os.path.join(dest, f"upload_{i}{ext}")
            with open(local_path, "wb") as f:
                f.write(file_data)
            paths.append(local_path)
        except (binascii.Error, ValueError):
            pass # Skip invalid base64
            
    return paths


def _apply_ai_colors(theme: BrandTheme, enhancement: "BrandEnhancement") -> None:
    """Overlay AI colour suggestions onto an existing BrandTheme (in-place)."""
    for attr, hex_val in [
        ("primary",   enhancement.ai_primary_hex),
        ("secondary", enhancement.ai_secondary_hex),
        ("accent",    enhancement.ai_accent_hex),
    ]:
        rgb = hex_to_rgb(hex_val or "")
        if rgb:
            setattr(theme, attr, rgb)
