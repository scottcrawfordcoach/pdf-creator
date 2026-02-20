# PDF Creator

Generate **custom-branded, fillable PDF forms** from a company logo and a plain-language description.

The tool reads your brand images, uses GPT-4o vision to extract colours and style, then builds a professional fillable PDF — header, section bars, form fields, and footer all styled to your brand automatically.

---

## Two ways to use it

| | CLI | Web app |
|---|---|---|
| **How** | `python main.py` | Browser UI |
| **Logo input** | Local file path | Drag & drop |
| **Form structure** | JSON config file | Plain-English brief |
| **AI enhancement** | Optional (`OPENAI_API_KEY`) | Automatic (GPT-4o vision) |
| **Output** | Local file | PDF download |
| **Hosting** | Local | Vercel + Supabase |

---

## Features

| | |
|---|---|
| 🤖 **GPT-4o brand intelligence** | Analyses logo + inspiration images for colours, style and tone |
| 🏗️ **AI form architecture** | Turns a plain-English brief into structured sections and fields |
| 🎨 **Auto colour extraction** | Algorithmic palette analysis with AI colour blending |
| 📝 **Fillable form fields** | Text, multi-line, date, checkbox, dropdown, and signature |
| 📐 **Flexible layout** | One- or two-column sections, full-width fields, multi-page |
| 📄 **A4 or Letter** | Configurable page size |
| ☁️ **Vercel + Supabase** | One-command cloud deployment |

---

## Web app — quick start

### 1 · Supabase setup

1. Create a project at [supabase.com](https://supabase.com)
2. **Storage → Buckets → New bucket** — name it `pdf-creator`, enable **Public**
3. Copy your **Project URL** and **Anon key** from **Settings → API**

### 2 · Environment variables

Fill in `.env.local`:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
OPENAI_API_KEY=sk-...    # also add this in the Vercel dashboard
```

### 3 · Install & run locally

```bash
npm install                   # Node / frontend dependencies
pip install -r requirements.txt  # Python / PDF generation dependencies
npm run dev                   # Start Next.js dev server
```

Open [http://localhost:3000](http://localhost:3000).

### 4 · Deploy to Vercel

```bash
npm i -g vercel
vercel
```

Vercel auto-detects the Next.js frontend **and** the Python serverless function in `api/generate.py`. Add the three environment variables above in the Vercel dashboard.

---

## CLI — quick start

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
# Full config file (recommended)
python main.py --config examples/sample_config.json

# Quick one-liner
python main.py --logo assets/logo.png --company "Acme Corp" --title "Application Form"

# Guided interactive prompts
python main.py
```

Generated PDFs land in the `output/` folder (created automatically).

---

## How the AI works

When `use_ai: true` (default on the web, opt-in via `OPENAI_API_KEY` on CLI):

1. **Vision analysis** — GPT-4o reads your uploaded images and identifies brand colours, style descriptors, and tone.
2. **Form architecture** — The AI interprets your plain-English brief and designs the full form structure: sections, field types, required flags, two-column layouts, dropdowns with options, and so on.
3. **Colour blending** — AI-suggested colours are blended with the algorithmically extracted palette for the most accurate brand match.

You describe the form in natural language; the AI figures out the JSON structure.

---

## Architecture

```
PDF Creator/
│
├── api/
│   └── generate.py         ← Vercel Python serverless function (POST /api/generate)
│
├── app/                    ← Next.js 14 App Router
│   ├── layout.tsx
│   ├── page.tsx            ← Main web UI
│   └── globals.css
│
├── components/
│   └── DropZone.tsx        ← Drag-and-drop brand materials panel
│
├── lib/
│   ├── supabase.ts         ← Supabase client + file upload helper
│   └── types.ts            ← Shared TypeScript types
│
├── src/                    ← Python modules (shared by CLI + API)
│   ├── __init__.py
│   ├── ai_enhancer.py      ← GPT-4o brand analysis + form structuring  ← NEW
│   ├── color_extractor.py  ← Algorithmic palette extraction (Pillow + ColorThief)
│   ├── branding.py         ← BrandTheme data class + colour math
│   ├── pdf_builder.py      ← ReportLab PDF rendering
│   └── utils.py            ← Config loading, validation, minimal-config builder
│
├── examples/
│   └── sample_config.json  ← Ready-to-run CLI example
│
├── main.py                 ← CLI entry point
├── package.json            ← Node dependencies
├── requirements.txt        ← Python dependencies
├── vercel.json             ← Vercel Python runtime config
└── .env.local              ← Local environment variables (not committed)
```

---

## Configuration Reference (CLI / JSON)

The config is a single `.json` file. Example: [`examples/sample_config.json`](examples/sample_config.json).

### Top-level keys

| Key | Type | Description |
|-----|------|-------------|
| `logo` | `string` | Path to the company logo image |
| `company_name` | `string` | Shown in the header (large text) |
| `document_title` | `string` | Shown below the company name |
| `document_subtitle` | `string` | Small instruction line in the header |
| `footer_text` | `string` | Left-aligned text in the footer strip |
| `page_size` | `"a4"` or `"letter"` | Page size (default `"letter"`) |
| `output` | `string` | Output PDF path |
| `sections` | `array` | List of form sections |

### Section object

```jsonc
{
  "title":   "Personal Details",  // Shown in the section bar
  "columns": 2,                   // 1 (default) or 2
  "intro":   "Optional intro text shown below the section bar.",
  "fields":  [ /* see below */ ]
}
```

### Field types

| `type` | Description |
|--------|-------------|
| `text` | Single-line text input |
| `email` | Email address field |
| `phone` | Phone number field |
| `number` | Numeric input |
| `date` | Date field with `DD / MM / YYYY` hint |
| `textarea` / `multiline` | Multi-line text area |
| `checkbox` | Tick box with label |
| `dropdown` / `select` | Drop-down selection list |
| `signature` | Signature box with baseline |

### Common field properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `string` | Internal PDF field name (must be unique) |
| `label` | `string` | Visible label text |
| `required` | `bool` | Appends a red `*` to the label |
| `default` | `string` | Pre-filled value |
| `tooltip` | `string` | Hover tooltip in PDF viewers |
| `full_width` | `bool` | Forces field to span full width in a 2-column section |
| `options` | `string[]` | Options list for `dropdown` type |
| `height` | `number` | Height in **cm** for `textarea` and `signature` (default `2.2` / `2.0`) |
| `placeholder` | `string` | Hint text for `date` fields |

---

## Project Structure

```
PDF Creator/
├── src/
│   ├── __init__.py
│   ├── ai_enhancer.py       # GPT-4o brand analysis + form structuring
│   ├── color_extractor.py   # Extract palette from logo (Pillow + ColorThief)
│   ├── branding.py          # Derive BrandTheme from extracted colours
│   ├── pdf_builder.py       # Render branded fillable PDF (ReportLab)
│   └── utils.py             # Config loading, validation, minimal-config builder
├── api/
│   └── generate.py          # Vercel Python serverless function
├── app/                     # Next.js 14 App Router (web UI)
├── components/              # React components
├── lib/                     # TypeScript utilities
├── examples/
│   └── sample_config.json   # Ready-to-run example
├── output/                  # Generated PDFs land here
├── main.py                  # CLI entry point
├── package.json
└── requirements.txt
```

---

## Dependencies

### Python
| Package | Purpose |
|---------|---------|
| [`reportlab`](https://www.reportlab.com/) | PDF generation and AcroForm fillable fields |
| [`Pillow`](https://python-pillow.org/) | Image loading and transparency handling |
| [`colorthief`](https://github.com/fengsp/color-thief-py) | Colour palette extraction |
| [`openai`](https://github.com/openai/openai-python) | GPT-4o vision brand analysis |
| `requests` | HTTP downloads in the serverless function |
| `python-dotenv` | Load `.env` in CLI mode |

### Node
| Package | Purpose |
|---------|---------|
| `next` | React framework + Vercel deployment |
| `@supabase/supabase-js` | File storage |
| `react-dropzone` | Drag-and-drop file input |
| `lucide-react` | Icons |
| `tailwindcss` | Utility-first CSS |
