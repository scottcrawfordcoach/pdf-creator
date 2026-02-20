"""
utils.py
────────
Configuration loading, validation, and convenience helpers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


Config = Dict[str, Any]


# ── Config I/O ────────────────────────────────────────────────────────────────

def load_config(path: str | Path) -> Config:
    """
    Load a JSON configuration file and return the parsed dict.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file is not valid JSON or fails basic schema checks.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    if p.suffix.lower() != ".json":
        raise ValueError(f"Config file must be a .json file, got: {p.suffix}")

    with p.open("r", encoding="utf-8") as fh:
        try:
            cfg = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in config file: {exc}") from exc

    _validate_config(cfg)
    return cfg


def _validate_config(cfg: Config) -> None:
    if not isinstance(cfg, dict):
        raise ValueError("Config root must be a JSON object.")
    if not cfg.get("document_title") and not cfg.get("company_name"):
        raise ValueError(
            "Config must contain at least 'document_title' or 'company_name'."
        )
    for i, section in enumerate(cfg.get("sections", [])):
        if not isinstance(section, dict):
            raise ValueError(f"Section {i} must be a JSON object.")
        for j, fld in enumerate(section.get("fields", [])):
            if not isinstance(fld, dict):
                raise ValueError(
                    f"Field {j} in section '{section.get('title', i)}' "
                    "must be a JSON object."
                )
            if not fld.get("name") and not fld.get("label"):
                raise ValueError(
                    f"Field {j} in section '{section.get('title', i)}' "
                    "must have a 'name' or 'label'."
                )


# ── Minimal config builder ────────────────────────────────────────────────────

def build_minimal_config(
    logo: str,
    company: str,
    title: str,
    output: str,
) -> Config:
    """
    Return a sensible default config when the user only provides the
    high-level details (logo path, company name, document title).
    """
    slug = title.lower().replace(" ", "_").replace("/", "_")
    return {
        "logo":               logo,
        "company_name":       company,
        "document_title":     title,
        "document_subtitle":  "Please complete all sections. Fields marked * are required.",
        "footer_text":        f"{company}  |  Confidential" if company else "",
        "page_size":          "a4",
        "output":             output or f"output/{slug}.pdf",
        "sections": [
            {
                "title":   "Contact Information",
                "columns": 2,
                "fields": [
                    {"type": "text",  "label": "First Name",    "name": "first_name",  "required": True},
                    {"type": "text",  "label": "Last Name",     "name": "last_name",   "required": True},
                    {"type": "email", "label": "Email Address", "name": "email",       "required": True},
                    {"type": "phone", "label": "Phone Number",  "name": "phone"},
                    {"type": "date",  "label": "Date of Birth", "name": "dob"},
                    {"type": "text",  "label": "Job Title",     "name": "job_title"},
                ],
            },
            {
                "title":   "Address",
                "columns": 1,
                "fields": [
                    {"type": "text", "label": "Street Address", "name": "address",  "required": True},
                    {"type": "text", "label": "City / Town",    "name": "city"},
                    {"type": "text", "label": "Postcode",       "name": "postcode"},
                ],
            },
            {
                "title":   "Additional Information",
                "columns": 1,
                "fields": [
                    {"type": "textarea", "label": "Notes / Comments", "name": "notes"},
                    {"type": "checkbox", "label": "I agree to the Terms & Conditions", "name": "terms_agreed", "required": True},
                ],
            },
            {
                "title":   "Authorisation",
                "columns": 2,
                "fields": [
                    {"type": "text",      "label": "Printed Name", "name": "printed_name", "required": True},
                    {"type": "date",      "label": "Date",         "name": "auth_date",    "required": True},
                    {"type": "signature", "label": "Signature",    "name": "signature",    "required": True, "full_width": True},
                ],
            },
        ],
    }
