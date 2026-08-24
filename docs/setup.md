# Setup & Local Development

## Prerequisites

- Python 3.9+ (developed/tested against Python 3.14)
- Tesseract OCR (system binary — fallback for image uploads, not installed via pip)
- A `GEMINI_API_KEY` (optional but recommended — see step 1b)

## 1. Install Tesseract

The `pytesseract` Python package is just a wrapper — it shells out to a
`tesseract` binary that must be installed separately.

```bash
# macOS
brew install tesseract

# Ubuntu / Debian
sudo apt-get install tesseract-ocr

# Windows
# https://github.com/UB-Mannheim/tesseract/wiki
```

Verify it's on your `PATH`:

```bash
tesseract --version
```

If PDF-only usage is all you need, Tesseract isn't strictly required —
`extract_text_from_pdf` doesn't touch it. For image uploads, Tesseract is
the fallback path (see step 1b) — without it *and* without a Gemini key,
image uploads will fail.

## 1b. (Optional) Set `GEMINI_API_KEY` for emoji-aware image extraction

Image uploads are transcribed by Gemini Flash (vision) when this key is
set, which — unlike Tesseract — correctly reads emoji, not just text (see
[limitations.md](limitations.md) for why this exists). Without it, image
uploads silently fall back to Tesseract OCR exactly as before: no crash,
just no emoji.

Get a free key at [aistudio.google.com](https://aistudio.google.com) (takes
under a minute — no billing setup required for the free tier):

```bash
export GEMINI_API_KEY=AIza...
```

The free tier's daily limit is low and per-model — testing this feature
hit `gemini-2.5-flash`'s actual ceiling at 20 requests/day on a free key
(check your own current limits at
[aistudio.google.com/rate-limit](https://aistudio.google.com/rate-limit)).
Once hit, the app falls back to Tesseract automatically — same as leaving
the key unset. To keep emoji detection working past that point without
waiting for the daily reset, point at a different model (separate quota
per model):

```bash
export GEMINI_MODEL=gemini-flash-lite-latest
```

See [limitations.md](limitations.md) for the full explanation. Leave
`GEMINI_API_KEY` unset entirely to keep the original Tesseract-only
behavior (also free, just without emoji).

## 2. Create a virtualenv and install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` pins: Flask, pypdf, pytesseract, Pillow, gunicorn, google-genai.

For running tests, also install pytest (not in `requirements.txt`, since it's
dev-only):

```bash
pip install pytest
```

## 3. Run the app

```bash
python app.py
```

Serves on **http://localhost:5000** (`debug=True`, so it auto-reloads on
code changes). Uploaded files are temporarily written to `uploads/` and
deleted right after each request.

## 4. Run the tests

```bash
python -m pytest tests/
```

See [testing.md](testing.md) for details.

## Troubleshooting

- **`TesseractNotFoundError` / OCR fails on images**: only matters if
  `GEMINI_API_KEY` is unset (or the vision call failed and it fell back).
  Tesseract isn't installed or isn't on `PATH`. Re-check step 1.
- **Emoji missing from image analysis**: `GEMINI_API_KEY` isn't set, so
  the app is using the Tesseract fallback, which can't see emoji at all —
  see step 1b and [limitations.md](limitations.md). Not a bug.
- **`ModuleNotFoundError` for `flask`/`pypdf`/etc.**: virtualenv isn't
  activated, or `pip install -r requirements.txt` wasn't run.
- **Port 5000 already in use**: on macOS this is often AirPlay Receiver —
  either disable it in System Settings, or change the port in the
  `app.run(...)` call at the bottom of `app.py`.
- **Uploads directory missing**: `app.py` creates `uploads/` automatically
  on startup (`os.makedirs(..., exist_ok=True)`) — you shouldn't need to
  create it by hand.
