#!/usr/bin/env python3
"""
main.py
───────
PDF Creator – command-line entry point.

Usage examples
──────────────
  # Full config file (recommended)
  python main.py --config examples/sample_config.json

  # Quick one-liner with a logo
  python main.py --logo assets/logo.png --company "Acme Corp" --title "Application Form"

  # Guided interactive mode (no arguments)
  python main.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.branding import theme_from_logo, default_theme
from src.pdf_builder import PDFBuilder
from src.utils import load_config, build_minimal_config


# ── CLI definition ─────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pdf-creator",
        description=(
            "Generate a custom-branded, fillable PDF from a company logo "
            "and a JSON configuration file."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--config", "-c",
        metavar="PATH",
        help="Path to a JSON config file (see examples/sample_config.json).",
    )
    p.add_argument(
        "--logo", "-l",
        metavar="PATH",
        help="Path to the company logo image (PNG, JPG, …).",
    )
    p.add_argument(
        "--company",
        metavar="NAME",
        help="Company name shown in the PDF header.",
    )
    p.add_argument(
        "--title", "-t",
        metavar="TEXT",
        help="Document title shown in the PDF header.",
    )
    p.add_argument(
        "--output", "-o",
        metavar="PATH",
        default="",
        help="Output PDF file path (default: output/<title>.pdf).",
    )
    return p


# ── Interactive mode ───────────────────────────────────────────────────────────

def _interactive() -> dict:
    print()
    print("╔══════════════════════════════════════╗")
    print("║         PDF Creator  –  Setup        ║")
    print("╚══════════════════════════════════════╝")
    print()
    print("Answer the prompts below, or press Enter to accept the default.\n")

    logo    = input("  Logo path         (Enter to skip)  : ").strip()
    company = input("  Company name      (Enter to skip)  : ").strip()
    title   = input("  Document title    [Untitled Form]  : ").strip() or "Untitled Form"

    slug    = title.lower().replace(" ", "_")
    default_out = f"output/{slug}.pdf"
    output  = input(f"  Output PDF path   [{default_out}] : ").strip() or default_out

    print()
    return build_minimal_config(
        logo=logo,
        company=company,
        title=title,
        output=output,
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = _build_parser()
    args   = parser.parse_args()

    # ── Resolve config ──────────────────────────────────────────────────────
    if args.config:
        try:
            cfg = load_config(args.config)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[error] {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.logo or args.title or args.company:
        cfg = build_minimal_config(
            logo=args.logo or "",
            company=args.company or "",
            title=args.title or "Document",
            output=args.output,
        )
    else:
        cfg = _interactive()

    # CLI --output flag overrides config (if explicitly provided)
    if args.output:
        cfg["output"] = args.output

    output_path = cfg.get("output") or "output/document.pdf"

    # ── Build theme from logo ───────────────────────────────────────────────
    logo_path = cfg.get("logo", "")
    if logo_path and Path(logo_path).exists():
        print(f"\n  Extracting brand colours from: {logo_path}")
        try:
            theme = theme_from_logo(logo_path)
            print(
                f"  Primary   #{'{:02X}{:02X}{:02X}'.format(*theme.primary)}"
                f"  |  Secondary #{'{:02X}{:02X}{:02X}'.format(*theme.secondary)}"
                f"  |  Accent #{'{:02X}{:02X}{:02X}'.format(*theme.accent)}"
            )
        except Exception as exc:                         # pragma: no cover
            print(f"  [warning] Could not extract colours ({exc}). "
                  "Using default blue theme.")
            theme = default_theme()
    else:
        if logo_path:
            print(f"\n  [warning] Logo not found at '{logo_path}'. "
                  "Using default blue theme.")
        else:
            print("\n  No logo supplied – using default blue theme.")
        theme = default_theme()

    # ── Generate PDF ────────────────────────────────────────────────────────
    print(f"\n  Building PDF → {output_path}")
    try:
        builder = PDFBuilder(cfg, theme)
        builder.build(output_path)
    except Exception as exc:
        print(f"\n[error] PDF generation failed: {exc}", file=sys.stderr)
        raise

    print(f"  ✓ Done!\n")


if __name__ == "__main__":
    main()
