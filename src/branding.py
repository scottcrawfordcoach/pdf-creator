"""
branding.py
───────────
Derives a complete visual identity (BrandTheme) from logo colours.

BrandTheme holds all colour and typography tokens used by PDFBuilder.
The ``theme_from_logo`` function does the heavy lifting: it picks the most
vibrant colours from the palette and derives safe contrast pairs for text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

from reportlab.lib.colors import HexColor

from .color_extractor import ColorExtractor, RGBColor


# ── Brand theme data class ─────────────────────────────────────────────────────

@dataclass
class BrandTheme:
    """All colour and typography tokens for a single brand."""

    # Core palette – set by the factory function
    primary:   RGBColor                          # Header bars, key accents
    secondary: RGBColor                          # Section bars, highlights
    accent:    RGBColor                          # Borders, focus rings, tabs

    # Derived / default tokens
    background: RGBColor = field(default=(255, 255, 255))
    surface:    RGBColor = field(default=(248, 249, 250))  # Field fill
    text_dark:  RGBColor = field(default=(28, 28, 30))
    text_light: RGBColor = field(default=(255, 255, 255))
    border:     RGBColor = field(default=(210, 212, 216))

    # Typography (standard PDF fonts – no embedding needed)
    font:        str = "Helvetica"
    font_bold:   str = "Helvetica-Bold"
    font_italic: str = "Helvetica-Oblique"

    # ── ReportLab colour helpers ───────────────────────────────────────────────

    @staticmethod
    def _rl(rgb: RGBColor) -> HexColor:
        return HexColor(ColorExtractor.rgb_to_hex(rgb))

    @property
    def rl_primary(self)    -> HexColor: return self._rl(self.primary)
    @property
    def rl_secondary(self)  -> HexColor: return self._rl(self.secondary)
    @property
    def rl_accent(self)     -> HexColor: return self._rl(self.accent)
    @property
    def rl_background(self) -> HexColor: return self._rl(self.background)
    @property
    def rl_surface(self)    -> HexColor: return self._rl(self.surface)
    @property
    def rl_text_dark(self)  -> HexColor: return self._rl(self.text_dark)
    @property
    def rl_text_light(self) -> HexColor: return self._rl(self.text_light)
    @property
    def rl_border(self)     -> HexColor: return self._rl(self.border)

    def header_text(self) -> HexColor:
        """Highest-contrast text colour to place on the primary header."""
        return self.rl_text_light if ColorExtractor.is_dark(self.primary) else self.rl_text_dark

    def section_text(self) -> HexColor:
        """Highest-contrast text colour to place on the secondary section bar."""
        return self.rl_text_light if ColorExtractor.is_dark(self.secondary) else self.rl_text_dark


# ── Factory ────────────────────────────────────────────────────────────────────

def theme_from_logo(logo_path: str | Path) -> BrandTheme:
    """
    Extract colours from *logo_path* and build a ``BrandTheme``.

    Strategy
    --------
    1. Pull an 8-colour palette from the logo.
    2. Filter out near-white and near-black candidates (bad for headers).
    3. Sort remaining colours by HLS saturation – most vibrant first.
    4. Assign the top three as primary / secondary / accent.
    5. Derive surface and border as tints of those colours.
    """
    ex = ColorExtractor(logo_path)
    palette = ex.palette(count=8)

    # Remove near-white / near-black for primary / secondary candidates
    candidates = [
        c for c in palette
        if 0.05 < ColorExtractor.luminance(c) < 0.90
    ]
    if not candidates:
        candidates = list(palette)          # fallback: use everything

    # Most vibrant first
    candidates.sort(key=ColorExtractor.hls_saturation, reverse=True)

    primary   = candidates[0]
    secondary = candidates[1] if len(candidates) > 1 else ColorExtractor.lighten(primary, 0.14)
    accent    = candidates[2] if len(candidates) > 2 else ColorExtractor.darken(primary, 0.14)

    # Surface: very light tint of primary – fall back to near-white if too dark
    surface = ColorExtractor.lighten(primary, 0.44)
    if ColorExtractor.luminance(surface) < 0.88:
        surface = (248, 249, 250)

    # Border: slightly darkened secondary tint
    border = ColorExtractor.lighten(secondary, 0.16)
    if ColorExtractor.luminance(border) < 0.65:
        border = (210, 212, 216)

    return BrandTheme(
        primary=primary,
        secondary=secondary,
        accent=accent,
        surface=surface,
        border=border,
    )


# ── Built-in fallback themes ───────────────────────────────────────────────────

def default_theme() -> BrandTheme:
    """A clean professional blue theme used when no logo is supplied."""
    return BrandTheme(
        primary=(31, 78, 151),
        secondary=(52, 109, 189),
        accent=(255, 160, 0),
        surface=(245, 248, 255),
        border=(189, 205, 230),
    )
