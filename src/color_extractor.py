"""
color_extractor.py
──────────────────
Extracts dominant brand colours from a logo image.

Handles transparency by compositing onto white before analysis, so logos
with transparent backgrounds don't skew the palette toward white/grey.
"""

from __future__ import annotations

import colorsys
import io
from pathlib import Path
from typing import List, Tuple

from PIL import Image
from colorthief import ColorThief

# Convenience type alias
RGBColor = Tuple[int, int, int]


class ColorExtractor:
    """Extract brand colours from any raster logo image."""

    def __init__(self, logo_path: str | Path) -> None:
        self.logo_path = Path(logo_path)
        if not self.logo_path.exists():
            raise FileNotFoundError(f"Logo not found: {self.logo_path}")
        self._thief: ColorThief = self._build_thief()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _build_thief(self) -> ColorThief:
        """Load the image, flatten transparency, and prepare ColorThief."""
        img = Image.open(self.logo_path).convert("RGBA")

        # Composite onto white so transparent pixels don't pollute the palette
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        flat = bg.convert("RGB")

        # ColorThief can accept a file-like object
        buf = io.BytesIO()
        flat.save(buf, format="PNG")
        buf.seek(0)
        return ColorThief(buf)

    # ── Public API ────────────────────────────────────────────────────────────

    def dominant(self) -> RGBColor:
        """Return the single most dominant colour."""
        return self._thief.get_color(quality=1)

    def palette(self, count: int = 8) -> List[RGBColor]:
        """Return up to *count* colours representing the logo's palette."""
        return self._thief.get_palette(color_count=max(count, 2), quality=1)

    # ── Static colour-math helpers ────────────────────────────────────────────

    @staticmethod
    def rgb_to_hex(rgb: RGBColor) -> str:
        """Convert an RGB tuple to an uppercase hex string, e.g. ``#1A2B3C``."""
        return "#{:02X}{:02X}{:02X}".format(*rgb)

    @staticmethod
    def luminance(rgb: RGBColor) -> float:
        """
        WCAG 2.1 relative luminance (0 = absolute black, 1 = absolute white).
        Used to decide whether to overlay dark or light text.
        """
        def _lin(c: int) -> float:
            v = c / 255.0
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

        r, g, b = (_lin(c) for c in rgb)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    @staticmethod
    def is_dark(rgb: RGBColor) -> bool:
        """Return True if the colour is perceptually dark (use light text on it)."""
        return ColorExtractor.luminance(rgb) < 0.40

    @staticmethod
    def lighten(rgb: RGBColor, amount: float = 0.25) -> RGBColor:
        """Increase lightness by *amount* (0–1) in HLS space."""
        h, l, s = colorsys.rgb_to_hls(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
        l = min(1.0, l + amount)
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return (int(r * 255), int(g * 255), int(b * 255))

    @staticmethod
    def darken(rgb: RGBColor, amount: float = 0.25) -> RGBColor:
        """Decrease lightness by *amount* (0–1) in HLS space."""
        h, l, s = colorsys.rgb_to_hls(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
        l = max(0.0, l - amount)
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return (int(r * 255), int(g * 255), int(b * 255))

    @staticmethod
    def saturate(rgb: RGBColor, amount: float = 0.15) -> RGBColor:
        """Boost saturation by *amount* (0–1) in HLS space."""
        h, l, s = colorsys.rgb_to_hls(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
        s = min(1.0, s + amount)
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return (int(r * 255), int(g * 255), int(b * 255))

    @staticmethod
    def hls_saturation(rgb: RGBColor) -> float:
        """Return the HLS saturation (0–1) of a colour."""
        _, _, s = colorsys.rgb_to_hls(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
        return s
