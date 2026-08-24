# Setup & Local Development

## Prerequisites

- Python 3.9+ (developed/tested against Python 3.14)
- Tesseract OCR (system binary — required for image uploads, not installed via pip)

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
`extract_text_from_pdf` doesn't touch it — but image uploads will fail
without it.

## 2. Create a virtualenv and install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` pins: Flask, pypdf, pytesseract, Pillow.

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

- **`TesseractNotFoundError` / OCR fails on images**: Tesseract isn't
  installed or isn't on `PATH`. Re-check step 1.
- **`ModuleNotFoundError` for `flask`/`pypdf`/etc.**: virtualenv isn't
  activated, or `pip install -r requirements.txt` wasn't run.
- **Port 5000 already in use**: on macOS this is often AirPlay Receiver —
  either disable it in System Settings, or change the port in the
  `app.run(...)` call at the bottom of `app.py`.
- **Uploads directory missing**: `app.py` creates `uploads/` automatically
  on startup (`os.makedirs(..., exist_ok=True)`) — you shouldn't need to
  create it by hand.
