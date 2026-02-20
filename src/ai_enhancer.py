"""
ai_enhancer.py
──────────────
Uses OpenAI GPT-4o (vision) to analyse brand images and free-form copy text,
then returns a BrandEnhancement containing:

  • A fully-structured PDF config (sections + fields) derived from the user's
    plain-English description of what the form should capture.
  • AI-suggested brand colours inferred from the visual materials.
  • Style / tone notes used as meta-context for the PDF header subtitle.

This means users never have to hand-craft JSON – they just describe their form
in natural language and the AI does the architecture work.
"""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openai


# ── Result data class ──────────────────────────────────────────────────────────

@dataclass
class BrandEnhancement:
    document_title:    str
    document_subtitle: str
    footer_text:       str
    style_notes:       str
    sections:          List[Dict[str, Any]]
    ai_primary_hex:    Optional[str] = None
    ai_secondary_hex:  Optional[str] = None
    ai_accent_hex:     Optional[str] = None


# ── Prompts ────────────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a professional graphic designer and document architect with deep "
    "expertise in corporate branding and form UX. Your role is to analyse brand "
    "materials (logo, inspiration images) together with a client's copy brief, "
    "and design a complete, well-structured, fillable PDF form.\n\n"
    "Always respond with valid JSON only – no markdown fences, no explanation, "
    "just the raw JSON object as specified."
)

_USER_TEMPLATE = """\
Analyse the provided brand materials and design a fillable PDF form based on \
the brief below.

Company: {company_name}
Requested document title: {document_title}

Client's brief – what the form should capture:
{copy_text}

Return a single JSON object with EXACTLY this structure (omit optional keys \
when not needed):

{{
  "document_title":    "polished title (refine if needed)",
  "document_subtitle": "one-line instruction for the person completing the form",
  "footer_text":       "concise footer: company · document type · {year}",
  "style_notes":       "2–3 adjectives describing brand tone e.g. professional, modern, approachable",
  "brand_colors": {{
    "primary_hex":   "#XXXXXX",
    "secondary_hex": "#XXXXXX",
    "accent_hex":    "#XXXXXX"
  }},
  "sections": [
    {{
      "title":   "Section Name",
      "columns": 1,
      "intro":   "optional single sentence shown above fields (omit if unnecessary)",
      "fields": [
        {{
          "type":       "text|email|phone|number|date|textarea|checkbox|dropdown|signature",
          "label":      "Field Label",
          "name":       "snake_case_name",
          "required":   true,
          "options":    ["Option A", "Option B"],
          "height":     2.5,
          "full_width": false,
          "tooltip":    "helpful hover hint"
        }}
      ]
    }}
  ]
}}

Field type rules:
  text      – short single-line (names, reference numbers, job titles)
  email     – email addresses
  phone     – phone numbers
  number    – numeric-only values
  date      – any date (shows DD/MM/YYYY hint)
  textarea  – multi-line answers (descriptions, notes, comments); default height 2.5
  checkbox  – boolean agreement / confirmation
  dropdown  – mutually exclusive choice (include options array)
  signature – handwritten signature box; always full_width: true

Layout rules:
  • columns: 2 for sections with many short paired fields (First/Last Name, Date/Phone etc.)
  • columns: 1 for sections with textareas or single fields
  • ALWAYS end with an "Authorisation" section containing:
      - printed_name (text, required)
      - auth_date (date, required)
      - signature (signature, required, full_width: true)
  • Brand colours should match the visual materials; if no images supplied, choose
    tasteful professional colours that suit the company name and tone.
  • Only include "intro", "options", "height", "full_width", "tooltip" when genuinely useful.
"""


# ── Main function ──────────────────────────────────────────────────────────────

def enhance_brand(
    image_paths:    List[str | Path],
    copy_text:      str,
    company_name:   str = "",
    document_title: str = "",
    api_key:        Optional[str] = None,
) -> BrandEnhancement:
    """
    Call OpenAI GPT-4o vision with brand images + copy brief.

    Parameters
    ----------
    image_paths    : Local paths to logo / inspiration images (up to 4 used).
    copy_text      : Free-form description of what the form should capture.
    company_name   : Company name for prompt context.
    document_title : Desired document title (can be empty; AI will suggest one).
    api_key        : OpenAI API key; falls back to OPENAI_API_KEY env var.
    """
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")

    client = openai.OpenAI(api_key=key)

    content: List[Dict[str, Any]] = []

    # Attach up to 4 images as base64 (low-detail is sufficient for colour / style)
    for path in image_paths[:4]:
        b64 = _encode_image(path)
        if b64:
            mime = _mime_type(path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url":    f"data:{mime};base64,{b64}",
                    "detail": "low",
                },
            })

    from datetime import date
    content.append({
        "type": "text",
        "text": _USER_TEMPLATE.format(
            company_name=company_name or "Not specified",
            document_title=document_title or "Not specified",
            copy_text=copy_text or "Create a professional general-purpose intake form.",
            year=date.today().year,
        ),
    })

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": content},
        ],
        response_format={"type": "json_object"},
        max_tokens=2500,
        temperature=0.35,
    )

    raw = response.choices[0].message.content or "{}"
    return _parse_response(raw)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _encode_image(path: str | Path) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def _mime_type(path: str | Path) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png",  ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/png")


def _parse_response(raw: str) -> BrandEnhancement:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"AI returned non-JSON: {raw[:300]}")

    colors = data.get("brand_colors", {})
    return BrandEnhancement(
        document_title    = data.get("document_title", "Form"),
        document_subtitle = data.get("document_subtitle", "Please complete all required fields."),
        footer_text       = data.get("footer_text", ""),
        style_notes       = data.get("style_notes", ""),
        sections          = data.get("sections", []),
        ai_primary_hex    = colors.get("primary_hex"),
        ai_secondary_hex  = colors.get("secondary_hex"),
        ai_accent_hex     = colors.get("accent_hex"),
    )


def hex_to_rgb(hex_color: str) -> Optional[Tuple[int, int, int]]:
    """Convert '#1A2B3C' to (26, 43, 60). Returns None if invalid."""
    if not hex_color:
        return None
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return None
    try:
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )
    except ValueError:
        return None
