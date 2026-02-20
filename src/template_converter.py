"""
src/template_converter.py
─────────────────────────
Converts a pre-designed form template (PNG or PDF) into a fillable PDF.

Workflow — PNG input
────────────────────
  1. Decode the base64 PNG and derive page dimensions from the image AR.
  2. Call GPT-4o Vision to detect every input area (boxed OR implied).
  3. Render the PNG as a full-page background in ReportLab and overlay
     transparent AcroForm fields at the detected positions.
     Unboxed-but-implied fields get a very subtle border so they
     remain discoverable without clashing with the original design.

Workflow — PDF input
────────────────────
  1. Decode and save the PDF.
  2. For each page, render a 150-dpi PNG via PyMuPDF for AI analysis.
  3. Call GPT-4o Vision on the rendered image.
  4. Add AcroForm widgets directly to the source page in the open fitz
     Document — this preserves all vector graphics and text at full quality.
  5. Save as a new PDF.
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image as PILImage
from reportlab.lib import colors as rl_colors
from reportlab.pdfgen import canvas as rl_canvas

try:
    import fitz  # PyMuPDF
    _FITZ_AVAILABLE = True
except ImportError:
    _FITZ_AVAILABLE = False

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

# ── Constants ──────────────────────────────────────────────────────────────────

_PAGE_WIDTH_PTS  = 612.0   # US Letter width; height derived from image AR
_FONT            = "Helvetica"
_FONT_SIZE       = 9
_RENDER_DPI      = 150     # DPI for PDF → PNG rendering (sent to GPT-4o)

# ── Detection prompt ───────────────────────────────────────────────────────────

_DETECTION_PROMPT = """\
You are analysing a form template image to identify every area where a user \
should enter information. This image may have been exported from Canva, \
a word processor, or a PDF editor.

Identify and return EVERY input area, including:

1. EXPLICIT fields — rectangular boxes, bordered cells, underlined blank \
   lines, or dashed areas clearly designed to receive typed content, tick \
   marks, or signatures.

2. IMPLIED fields — blank space directly beneath or beside a label or heading \
   that clearly invites a response, even with NO visible border. Examples: \
   a blank area under "Full Name:", "Date:", "Signature:", "Notes:", \
   "Description:", "Comments:", or any field-label/colon pattern. \
   Also include blank lines made of underscores ( ___ ) used as writing lines. \
   Infer a sensible bounding rectangle that fills the available whitespace \
   associated with that label.

For EACH area return a JSON object in a top-level "fields" array with:
  name       – snake_case identifier inferred from the nearest label
  label      – human-readable label nearest to the widget
  type       – one of: text | multiline | checkbox | signature
  has_border – true if there is already a visible border/box; false if implied
  x_pct      – left edge as percentage of image width  (0–100, float)
  y_pct      – top  edge as percentage of image height (0–100, float)
  w_pct      – field width  as percentage of image width
  h_pct      – field height as percentage of image height

Rules:
- Be precise with coordinates.
- Do NOT include decorative lines, headers, logos, or static body text.
- Use type "multiline" for large text areas (Comments, Notes, Address blocks).
- Use type "signature" for signature lines/boxes.
- Respond with ONLY a raw JSON object — no markdown fences, no commentary.
"""


# ── Public API ─────────────────────────────────────────────────────────────────

def convert_template_from_bytes(
    file_bytes:     bytes,
    mime:           str = "",
    document_title: str = "",
    openai_api_key: str = "",
) -> Tuple[bytes, int]:
    """
    Convert raw PNG or PDF bytes to a fillable PDF.
    Preferred entry point when the caller already has the file in memory
    (e.g. downloaded from a URL), avoiding a redundant b64 round-trip.

    Parameters
    ----------
    file_bytes : bytes
        Raw file content.
    mime : str
        MIME type hint (e.g. 'application/pdf' or 'image/png').
        Falls back to magic-byte detection when empty.
    document_title : str
        Optional PDF document title embedded in metadata.
    openai_api_key : str
        OpenAI API key for GPT-4o field detection.

    Returns
    -------
    (pdf_bytes, total_field_count)
    """
    if not mime:
        mime = _sniff_mime(file_bytes)

    if mime == "application/pdf":
        if not _FITZ_AVAILABLE:
            raise RuntimeError(
                "PyMuPDF is required for PDF templates. "
                "Install it with: pip install PyMuPDF"
            )
        return _convert_pdf(file_bytes, document_title, openai_api_key)
    else:
        # Build a data-URI so _convert_image can forward it to GPT-4o
        b64      = base64.b64encode(file_bytes).decode()
        file_b64 = f"data:image/png;base64,{b64}"
        return _convert_image(file_b64, file_bytes, document_title, openai_api_key)


def convert_template(
    file_b64:       str,
    document_title: str = "",
    openai_api_key: str = "",
) -> Tuple[bytes, int]:
    """
    Convert a base64-encoded PNG or PDF template to a fillable PDF.
    Kept for backwards-compatibility; prefer convert_template_from_bytes.
    """
    file_bytes = _decode_b64(file_b64)
    mime       = _sniff_mime(file_bytes, file_b64)
    return convert_template_from_bytes(file_bytes, mime, document_title, openai_api_key)


# ── PNG / image path ───────────────────────────────────────────────────────────

def _convert_image(
    file_b64:       str,
    file_bytes:     bytes,
    document_title: str,
    openai_api_key: str,
) -> Tuple[bytes, int]:
    """Render image as PDF background and overlay AcroForm fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = os.path.join(tmpdir, "template.png")
        with open(img_path, "wb") as fh:
            fh.write(file_bytes)

        with PILImage.open(img_path) as img:
            img_w, img_h = img.size

        page_w = _PAGE_WIDTH_PTS
        page_h = page_w * (img_h / img_w)

        b64_for_ai = file_b64 if file_b64.startswith("data:") \
                     else f"data:image/png;base64,{file_b64}"

        fields: List[Dict[str, Any]] = []
        if _OPENAI_AVAILABLE and openai_api_key:
            fields = _detect_fields(b64_for_ai, openai_api_key)

        out_path = os.path.join(tmpdir, "output.pdf")
        _build_pdf_from_image(img_path, page_w, page_h, fields, document_title, out_path)

        with open(out_path, "rb") as fh:
            return fh.read(), len(fields)


# ── PDF path ───────────────────────────────────────────────────────────────────

def _convert_pdf(
    file_bytes:     bytes,
    document_title: str,
    openai_api_key: str,
) -> Tuple[bytes, int]:
    """Add AcroForm widgets directly to a source PDF via PyMuPDF."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "source.pdf")
        with open(src_path, "wb") as fh:
            fh.write(file_bytes)

        doc          = fitz.open(src_path)
        total_fields = 0

        for page_num, page in enumerate(doc):
            page_w = page.rect.width
            page_h = page.rect.height

            # Render the page to PNG for GPT-4o analysis
            mat       = fitz.Matrix(_RENDER_DPI / 72, _RENDER_DPI / 72)
            pix       = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            b64_for_ai = (
                "data:image/png;base64,"
                + base64.b64encode(png_bytes).decode()
            )

            fields: List[Dict[str, Any]] = []
            if _OPENAI_AVAILABLE and openai_api_key:
                fields = _detect_fields(b64_for_ai, openai_api_key)

            for i, field in enumerate(fields):
                _add_fitz_widget(page, field, page_w, page_h,
                                 index=page_num * 10_000 + i)

            total_fields += len(fields)

        if document_title:
            doc.set_metadata({"title": document_title})

        out_path = os.path.join(tmpdir, "output.pdf")
        doc.save(out_path, garbage=4, deflate=True)
        doc.close()

        with open(out_path, "rb") as fh:
            return fh.read(), total_fields


# ── Shared field-detection ─────────────────────────────────────────────────────

def _detect_fields(image_b64_data_uri: str, api_key: str) -> List[Dict[str, Any]]:
    """
    Call GPT-4o with vision to detect form field bounding boxes.
    Always returns a list (possibly empty) — never raises.
    """
    try:
        client   = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _DETECTION_PROMPT},
                        {
                            "type":      "image_url",
                            "image_url": {
                                "url":    image_b64_data_uri,
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        # Strip any accidental markdown code fences
        raw = raw.strip("` \n")
        if raw.startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
        return data.get("fields", [])
    except Exception:
        return []


# ── ReportLab PDF builder (PNG path) ──────────────────────────────────────────

def _build_pdf_from_image(
    img_path:       str,
    page_w:         float,
    page_h:         float,
    fields:         List[Dict[str, Any]],
    document_title: str,
    out_path:       str,
) -> None:
    """Render the image as a full-page background and overlay AcroForm fields."""
    c = rl_canvas.Canvas(out_path, pagesize=(page_w, page_h))
    if document_title:
        c.setTitle(document_title)

    c.drawImage(
        img_path, 0, 0,
        width=page_w, height=page_h,
        preserveAspectRatio=False, mask="auto",
    )

    form        = c.acroForm
    transparent = rl_colors.Color(1, 1, 1, alpha=0)

    for i, field in enumerate(fields):
        try:
            x_pct      = float(field.get("x_pct", 0))
            y_pct      = float(field.get("y_pct", 0))
            w_pct      = float(field.get("w_pct", 10))
            h_pct      = float(field.get("h_pct", 3))
            ftype      = str(field.get("type", "text")).lower()
            has_border = bool(field.get("has_border", True))
            name       = _safe_name(field.get("name", f"field_{i + 1}"), i)
            label      = str(field.get("label", name.replace("_", " ").title()))

            x     = (x_pct / 100.0) * page_w
            y_top = (y_pct / 100.0) * page_h
            w     = (w_pct / 100.0) * page_w
            h     = (h_pct / 100.0) * page_h
            # ReportLab y = distance from BOTTOM
            y = page_h - y_top - h

            # Implied (unboxed) fields get a subtle hint border
            if has_border:
                bw, bc = 0, None
            else:
                bw = 0.5
                bc = rl_colors.Color(0.6, 0.6, 0.6, alpha=0.6)

            if ftype == "checkbox":
                size = min(w, h)
                form.checkbox(
                    name=name, tooltip=label,
                    x=x, y=y, size=size,
                    borderWidth=bw, borderColor=bc,
                    fillColor=transparent, forceBorder=not has_border,
                )
            else:
                form.textfield(
                    name=name, tooltip=label,
                    x=x, y=y, width=w, height=h,
                    borderWidth=bw, borderColor=bc,
                    fillColor=transparent,
                    textColor=rl_colors.black,
                    fontName=_FONT, fontSize=_FONT_SIZE,
                    multiline=(ftype in ("multiline", "signature")),
                    forceBorder=not has_border,
                )
        except Exception:
            continue

    c.save()


# ── PyMuPDF widget builder (PDF path) ─────────────────────────────────────────

def _add_fitz_widget(
    page:   "fitz.Page",
    field:  Dict[str, Any],
    page_w: float,
    page_h: float,
    index:  int,
) -> None:
    """Create and insert an AcroForm widget onto a fitz Page."""
    try:
        x_pct      = float(field.get("x_pct", 0))
        y_pct      = float(field.get("y_pct", 0))
        w_pct      = float(field.get("w_pct", 10))
        h_pct      = float(field.get("h_pct", 3))
        ftype      = str(field.get("type", "text")).lower()
        has_border = bool(field.get("has_border", True))
        name       = _safe_name(field.get("name", f"field_{index}"), index)
        label      = str(field.get("label", name.replace("_", " ").title()))

        # fitz uses top-left origin, y increases downward
        x0 = (x_pct / 100.0) * page_w
        y0 = (y_pct / 100.0) * page_h
        x1 = x0 + (w_pct / 100.0) * page_w
        y1 = y0 + (h_pct / 100.0) * page_h
        rect = fitz.Rect(x0, y0, x1, y1)

        widget = fitz.Widget()
        widget.field_name    = name
        widget.field_label   = label
        widget.rect          = rect
        widget.text_color    = (0, 0, 0)
        widget.text_font     = "Helv"
        widget.text_fontsize = _FONT_SIZE

        if has_border:
            widget.border_width = 0
            widget.border_color = None
            widget.fill_color   = None
        else:
            widget.border_width = 0.5
            widget.border_color = (0.6, 0.6, 0.6)
            widget.fill_color   = None

        if ftype == "checkbox":
            widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
        else:
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            if ftype in ("multiline", "signature"):
                widget.field_flags = fitz.PDF_TX_FIELD_IS_MULTILINE

        page.add_widget(widget)
    except Exception:
        pass  # Never let a single bad field crash the whole conversion


# ── Utility helpers ────────────────────────────────────────────────────────────

def _decode_b64(b64_str: str) -> bytes:
    """Strip an optional data-URI header and base64-decode."""
    if "," in b64_str:
        _, b64_str = b64_str.split(",", 1)
    b64_str += "=" * (-len(b64_str) % 4)
    return base64.b64decode(b64_str)


def _sniff_mime(file_bytes: bytes, b64_str: str = "") -> str:
    """Detect whether the file is a PDF or an image."""
    if file_bytes[:4] == b"%PDF":
        return "application/pdf"
    if b64_str.startswith("data:application/pdf"):
        return "application/pdf"
    return "image/png"


def _safe_name(raw: Optional[Any], index: int) -> str:
    """Return a safe, unique AcroForm field name."""
    name = str(raw or f"field_{index}")
    name = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    return f"{name}_{index}"
