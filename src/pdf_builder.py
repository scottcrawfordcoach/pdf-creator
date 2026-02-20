"""
pdf_builder.py
──────────────
Assembles a branded, fillable PDF from a configuration dict and a BrandTheme.

Layout model
────────────
  • A "cursor" variable ``_y`` tracks the top of the next element to draw,
    measured in ReportLab points from the bottom of the page.
  • Each draw helper subtracts the element's height from ``_y`` so the cursor
    moves downward naturally.
  • ``_ensure_space`` triggers a new page before a section/field if there
    isn't enough room remaining above the footer.

Coordinate system (ReportLab default)
────────────────────────────────────
  (0, 0) is the BOTTOM-LEFT corner of the page.
  Positive Y goes UP.
  All measurements use ``cm`` units imported from reportlab.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as rl_canvas

from .branding import BrandTheme
from .color_extractor import ColorExtractor

# ── Layout constants ───────────────────────────────────────────────────────────
MARGIN        = 1.80 * cm   # Left / right / bottom margin
HEADER_H      = 3.20 * cm   # Full header height (first page)
CONT_HEADER_H = 1.70 * cm   # Compact header on continuation pages
FOOTER_H      = 0.90 * cm   # Footer strip height

SECTION_BAR_H = 0.68 * cm   # Coloured section-title bar
SECTION_GAP   = 0.50 * cm   # Space below section bar before first field
BETWEEN_SECS  = 0.70 * cm   # Space between sections

LABEL_H       = 0.38 * cm   # Height of a field label
LABEL_GAP     = 0.14 * cm   # Gap between label and field box
FIELD_H       = 0.70 * cm   # Single-line field height
TEXTAREA_H    = 2.20 * cm   # Default multi-line field height
CHECKBOX_H    = 0.44 * cm   # Checkbox size (square)
ROW_GAP       = 0.48 * cm   # Vertical gap between field rows

COL_GAP       = 0.55 * cm   # Gap between two columns

# Type aliases
Config     = Dict[str, Any]
FieldCfg   = Dict[str, Any]
SectionCfg = Dict[str, Any]


class PDFBuilder:
    """
    Build a branded, fillable PDF from *config* using *theme* colours.

    Parameters
    ----------
    config : dict
        Parsed JSON configuration (see ``examples/sample_config.json``).
    theme : BrandTheme
        Visual identity derived from the company logo.
    """

    def __init__(self, config: Config, theme: BrandTheme) -> None:
        self.cfg   = config
        self.theme = theme
        page_key   = config.get("page_size", "letter").lower()
        self.page_size = A4 if page_key == "a4" else letter
        self.W, self.H = self.page_size
        self._usable_w = self.W - 2 * MARGIN
        self._c: Optional[rl_canvas.Canvas] = None
        self._y: float = 0.0          # current top-of-next-element cursor

    # ── Public ────────────────────────────────────────────────────────────────

    def build(self, output_path: str) -> None:
        """Render the complete PDF to *output_path*."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self._c = rl_canvas.Canvas(output_path, pagesize=self.page_size)
        self._begin_page(first=True)

        for section in self.cfg.get("sections", []):
            self._draw_section(section)

        self._draw_footer()
        self._c.save()

    # ── Page management ───────────────────────────────────────────────────────

    def _begin_page(self, first: bool = True) -> None:
        if first:
            self._draw_header(first=True)
            self._y = self.H - HEADER_H - MARGIN * 0.65
        else:
            self._draw_header(first=False)
            self._y = self.H - CONT_HEADER_H - MARGIN * 0.55

    def _new_page(self) -> None:
        self._draw_footer()
        self._c.showPage()
        self._begin_page(first=False)

    def _ensure_space(self, needed: float) -> None:
        """Start a new page when fewer than *needed* points remain above footer."""
        if self._y - needed < FOOTER_H + MARGIN:
            self._new_page()

    # ── Header ────────────────────────────────────────────────────────────────

    def _draw_header(self, first: bool) -> None:
        c, t = self._c, self.theme
        hh = HEADER_H if first else CONT_HEADER_H

        # Main coloured background
        c.setFillColor(t.rl_primary)
        c.rect(0, self.H - hh, self.W, hh, fill=1, stroke=0)

        # Thin accent stripe along the bottom edge of the header
        c.setFillColor(t.rl_accent)
        c.rect(0, self.H - hh, self.W, 0.20 * cm, fill=1, stroke=0)

        txt_color = t.header_text()
        c.setFillColor(txt_color)

        if first:
            text_x = MARGIN
            logo_path = self.cfg.get("logo", "")
            if logo_path and os.path.exists(logo_path):
                lw, lh = _logo_dims(logo_path,
                                    max_h=hh - 0.85 * cm,
                                    max_w=5.0 * cm)
                ly = self.H - hh + (hh - lh) / 2.0
                c.drawImage(logo_path, MARGIN, ly,
                            width=lw, height=lh,
                            preserveAspectRatio=True, mask="auto")
                text_x = MARGIN + lw + 0.55 * cm

            company  = self.cfg.get("company_name", "")
            title    = self.cfg.get("document_title", "")
            subtitle = self.cfg.get("document_subtitle", "")

            if company:
                c.setFont(t.font_bold, 15)
                c.drawString(text_x, self.H - hh + 1.95 * cm, company)
            if title:
                c.setFont(t.font, 11)
                c.drawString(text_x, self.H - hh + 1.15 * cm, title)
            if subtitle:
                c.setFillColor(txt_color)
                c.setFillAlpha(0.82)
                c.setFont(t.font_italic, 8.5)
                c.drawString(text_x, self.H - hh + 0.46 * cm, subtitle)
                c.setFillAlpha(1.0)
        else:
            # Compact continuation: single-line identifier
            parts = [p for p in [
                self.cfg.get("company_name"),
                self.cfg.get("document_title"),
            ] if p]
            label = "  \u2013  ".join(parts) if parts else "Document"
            c.setFont(t.font_bold, 10)
            c.drawString(MARGIN, self.H - hh + CONT_HEADER_H * 0.30, label)

    # ── Footer ────────────────────────────────────────────────────────────────

    def _draw_footer(self) -> None:
        c, t = self._c, self.theme
        c.setFillColor(t.rl_primary)
        c.rect(0, 0, self.W, FOOTER_H, fill=1, stroke=0)

        c.setFillColor(t.header_text())
        c.setFont(t.font, 7.5)
        footer_text = self.cfg.get("footer_text", "")
        if footer_text:
            c.drawString(MARGIN, FOOTER_H * 0.30, footer_text)
        c.drawRightString(self.W - MARGIN, FOOTER_H * 0.30,
                          f"Page {c.getPageNumber()}")

    # ── Sections ──────────────────────────────────────────────────────────────

    def _draw_section(self, section: SectionCfg) -> None:
        # Guarantee at least the bar + one field row fits before we commit
        min_needed = SECTION_BAR_H + SECTION_GAP + LABEL_H + FIELD_H + ROW_GAP
        self._ensure_space(min_needed)

        c, t = self._c, self.theme

        # Coloured section bar
        bar_y = self._y - SECTION_BAR_H
        c.setFillColor(t.rl_secondary)
        c.rect(MARGIN, bar_y, self._usable_w, SECTION_BAR_H, fill=1, stroke=0)

        # Left accent tab
        c.setFillColor(t.rl_accent)
        c.rect(MARGIN, bar_y, 0.30 * cm, SECTION_BAR_H, fill=1, stroke=0)

        # Section title text
        c.setFillColor(t.section_text())
        c.setFont(t.font_bold, 9.5)
        c.drawString(MARGIN + 0.55 * cm, bar_y + 0.17 * cm,
                     section.get("title", "Section"))

        self._y = bar_y - SECTION_GAP

        # Optional introductory paragraph
        if intro := section.get("intro"):
            self._draw_intro(intro)

        # Field layout
        fields  = section.get("fields", [])
        columns = int(section.get("columns", 1))
        if columns == 2:
            self._layout_two_col(fields)
        else:
            self._layout_one_col(fields)

        self._y -= BETWEEN_SECS

    def _draw_intro(self, text: str) -> None:
        c, t = self._c, self.theme
        c.setFillColor(t.rl_text_dark)
        c.setFont(t.font_italic, 9)
        c.drawString(MARGIN, self._y - LABEL_H, text)
        self._y -= LABEL_H + 0.38 * cm

    # ── Field layout ──────────────────────────────────────────────────────────

    def _layout_one_col(self, fields: List[FieldCfg]) -> None:
        for fld in fields:
            rh = _row_height(fld)
            self._ensure_space(rh + ROW_GAP)
            self._draw_field(fld, x=MARGIN, w=self._usable_w)
            self._y -= ROW_GAP

    def _layout_two_col(self, fields: List[FieldCfg]) -> None:
        col_w = (self._usable_w - COL_GAP) / 2.0
        i = 0
        while i < len(fields):
            fld_l = fields[i]
            fld_r = fields[i + 1] if i + 1 < len(fields) else None

            # Full-width field breaks the paired layout
            if fld_l.get("full_width"):
                rh = _row_height(fld_l)
                self._ensure_space(rh + ROW_GAP)
                self._draw_field(fld_l, x=MARGIN, w=self._usable_w)
                self._y -= ROW_GAP
                i += 1
                continue

            row_h = max(
                _row_height(fld_l),
                _row_height(fld_r) if fld_r else 0.0,
            )
            self._ensure_space(row_h + ROW_GAP)

            y_save = self._y

            # Draw left column field
            self._draw_field(fld_l, x=MARGIN, w=col_w)
            y_after_l = self._y

            # Reset cursor and draw right column field
            self._y = y_save
            if fld_r and not fld_r.get("full_width"):
                self._draw_field(fld_r, x=MARGIN + col_w + COL_GAP, w=col_w)
                y_after_r = self._y
            else:
                y_after_r = y_save

            # Advance by the height of the taller field
            self._y = min(y_after_l, y_after_r) - ROW_GAP
            i += 2

    # ── Field dispatch ────────────────────────────────────────────────────────

    def _draw_field(self, fld: FieldCfg, x: float, w: float) -> None:
        ft = fld.get("type", "text").lower()
        dispatch = {
            "text":      self._field_text,
            "email":     self._field_text,
            "phone":     self._field_text,
            "number":    self._field_text,
            "date":      self._field_date,
            "textarea":  self._field_textarea,
            "multiline": self._field_textarea,
            "checkbox":  self._field_checkbox,
            "dropdown":  self._field_dropdown,
            "select":    self._field_dropdown,
            "signature": self._field_signature,
        }
        dispatch.get(ft, self._field_text)(fld, x, w)

    # ── Label helper ──────────────────────────────────────────────────────────

    def _draw_label(self, text: str, x: float, y_top: float,
                    required: bool = False) -> None:
        c, t = self._c, self.theme
        c.setFillColor(t.rl_text_dark)
        c.setFont(t.font_bold, 8.5)
        c.drawString(x, y_top - LABEL_H + 0.04 * cm, text)
        if required:
            label_w = c.stringWidth(text, t.font_bold, 8.5)
            c.setFillColor(colors.Color(0.85, 0.10, 0.10))
            c.setFont(t.font_bold, 9.5)
            c.drawString(x + label_w + 0.10 * cm,
                         y_top - LABEL_H + 0.04 * cm, "*")

    # ── Individual field renderers ────────────────────────────────────────────

    def _field_text(self, fld: FieldCfg, x: float, w: float) -> None:
        c, t = self._c, self.theme
        label    = fld.get("label", fld.get("name", ""))
        name     = _safe_name(fld)
        required = fld.get("required", False)

        y_top = self._y
        self._draw_label(label, x, y_top, required)

        fy = y_top - LABEL_H - LABEL_GAP - FIELD_H
        _draw_field_bg(c, t, x, fy, w, FIELD_H)
        c.acroForm.textfield(
            name=name, tooltip=fld.get("tooltip", label),
            x=x, y=fy, width=w, height=FIELD_H,
            borderStyle="solid", borderWidth=0.5,
            borderColor=t.rl_border, fillColor=t.rl_surface,
            textColor=t.rl_text_dark, forceBorder=True,
            value=fld.get("default", ""), fontSize=9, fontName=t.font,
        )
        self._y = fy

    def _field_date(self, fld: FieldCfg, x: float, w: float) -> None:
        """Date field – rendered as a text field with a subtle hint overlay."""
        self._field_text(fld, x, w)
        c, t = self._c, self.theme
        hint = fld.get("placeholder", "DD / MM / YYYY")
        c.setFillColor(colors.Color(0.55, 0.55, 0.55))
        c.setFont(t.font_italic, 7.5)
        c.drawString(x + 0.22 * cm, self._y + 0.18 * cm, hint)

    def _field_textarea(self, fld: FieldCfg, x: float, w: float) -> None:
        c, t = self._c, self.theme
        label    = fld.get("label", fld.get("name", ""))
        name     = _safe_name(fld)
        required = fld.get("required", False)
        ta_h     = float(fld.get("height", 2.2)) * cm

        y_top = self._y
        self._draw_label(label, x, y_top, required)

        fy = y_top - LABEL_H - LABEL_GAP - ta_h
        _draw_field_bg(c, t, x, fy, w, ta_h)
        c.acroForm.textfield(
            name=name, tooltip=fld.get("tooltip", label),
            x=x, y=fy, width=w, height=ta_h,
            borderStyle="solid", borderWidth=0.5,
            borderColor=t.rl_border, fillColor=t.rl_surface,
            textColor=t.rl_text_dark, forceBorder=True,
            fieldFlags="multiline",
            value=fld.get("default", ""), fontSize=9, fontName=t.font,
        )
        self._y = fy

    def _field_checkbox(self, fld: FieldCfg, x: float, w: float) -> None:
        c, t = self._c, self.theme
        name    = _safe_name(fld)
        label   = fld.get("label", name)
        checked = bool(fld.get("default", False))

        cy = self._y - CHECKBOX_H
        c.acroForm.checkbox(
            name=name, tooltip=fld.get("tooltip", label),
            x=x, y=cy, size=CHECKBOX_H,
            borderStyle="solid", borderWidth=0.5,
            borderColor=t.rl_accent, fillColor=t.rl_surface,
            forceBorder=True, checked=checked, buttonStyle="check",
        )
        c.setFillColor(t.rl_text_dark)
        c.setFont(t.font, 9)
        c.drawString(x + CHECKBOX_H + 0.30 * cm,
                     cy + CHECKBOX_H * 0.18, label)
        self._y = cy

    def _field_dropdown(self, fld: FieldCfg, x: float, w: float) -> None:
        c, t = self._c, self.theme
        label    = fld.get("label", fld.get("name", ""))
        name     = _safe_name(fld)
        required = fld.get("required", False)
        options  = list(fld.get("options", [])) or ["-- Select --"]

        y_top = self._y
        self._draw_label(label, x, y_top, required)

        fy = y_top - LABEL_H - LABEL_GAP - FIELD_H
        _draw_field_bg(c, t, x, fy, w, FIELD_H)
        c.acroForm.choice(
            name=name, tooltip=fld.get("tooltip", label),
            x=x, y=fy, width=w, height=FIELD_H,
            options=options,
            value=fld.get("default", options[0]),
            borderStyle="solid", borderWidth=0.5,
            borderColor=t.rl_border, fillColor=t.rl_surface,
            textColor=t.rl_text_dark, forceBorder=True, fontSize=9,
        )
        self._y = fy

    def _field_signature(self, fld: FieldCfg, x: float, w: float) -> None:
        c, t = self._c, self.theme
        label    = fld.get("label", "Signature")
        required = fld.get("required", False)
        sig_h    = float(fld.get("height", 2.0)) * cm

        y_top = self._y
        self._draw_label(label, x, y_top, required)

        fy = y_top - LABEL_H - LABEL_GAP - sig_h

        # Signature box
        c.setFillColor(t.rl_background)
        c.setStrokeColor(t.rl_accent)
        c.setLineWidth(0.75)
        c.roundRect(x, fy, w, sig_h, 3, fill=1, stroke=1)

        # "X" mark
        c.setFillColor(t.rl_text_dark)
        c.setFont(t.font_bold, 14)
        c.drawString(x + 0.35 * cm, fy + 0.38 * cm, "\u00d7")

        # Baseline
        c.setStrokeColor(t.rl_border)
        c.setLineWidth(0.4)
        c.line(x + 1.10 * cm, fy + 0.68 * cm, x + w - 0.50 * cm, fy + 0.68 * cm)

        # Hint text
        c.setFillColor(colors.Color(0.55, 0.55, 0.55))
        c.setFont(t.font_italic, 8)
        c.drawString(x + 1.20 * cm, fy + 0.75 * cm, "Sign here")

        self._y = fy


# ── Module-level helpers ───────────────────────────────────────────────────────

def _safe_name(fld: FieldCfg) -> str:
    """Return a PDF-safe (no spaces) field name, unique by label fallback."""
    raw = fld.get("name") or fld.get("label", "field")
    return raw.lower().replace(" ", "_").replace("/", "_").replace("-", "_")


def _row_height(fld: Optional[FieldCfg]) -> float:
    """Return the total vertical space (including label) consumed by *fld*."""
    if not fld:
        return 0.0
    ft = fld.get("type", "text").lower()
    if ft in ("textarea", "multiline"):
        return LABEL_H + LABEL_GAP + float(fld.get("height", 2.2)) * cm
    if ft == "checkbox":
        return CHECKBOX_H
    if ft == "signature":
        return LABEL_H + LABEL_GAP + float(fld.get("height", 2.0)) * cm
    # text / email / phone / number / date / dropdown
    return LABEL_H + LABEL_GAP + FIELD_H


def _draw_field_bg(c: rl_canvas.Canvas, t: BrandTheme,
                   x: float, y: float, w: float, h: float) -> None:
    """Draw a lightly styled rectangle behind a form widget."""
    c.setFillColor(t.rl_surface)
    c.setStrokeColor(t.rl_border)
    c.setLineWidth(0.4)
    c.roundRect(x, y, w, h, 2, fill=1, stroke=1)


def _logo_dims(path: str, max_h: float, max_w: float) -> Tuple[float, float]:
    """Scale logo dimensions to fit within *max_h* × *max_w*, preserving ratio."""
    try:
        img = PILImage.open(path)
        iw, ih = img.size
        aspect = iw / max(ih, 1)
        h = min(max_h, max_w / max(aspect, 0.01))
        w = h * aspect
        if w > max_w:
            w = max_w
            h = w / max(aspect, 0.01)
        return w, h
    except Exception:
        return max_h * 2.0, max_h
