# Architecture

## Overview

The app is a single Flask process with three clean layers and a vanilla-JS
frontend. There's no database, no background jobs, no external API calls —
everything happens synchronously within one request.

```
Browser (templates/index.html + static/script.js)
        │  POST /api/analyze  (multipart/form-data, field "file")
        ▼
app.py            — Flask route, file validation, save/cleanup, error shaping
        │
        ▼
extractor.py      — turns the uploaded file into raw text
        │             • PDF  → pypdf (direct text extraction)
        │             • image → pytesseract (Tesseract OCR)
        ▼
analyzer.py       — turns raw text into an engagement score + suggestions
        │             (pure function, no I/O, fully deterministic)
        ▼
JSON response ──► Browser renders score, stats, extracted text, suggestions
```

## Module responsibilities

### `app.py`
- Single Flask app, single route: `POST /api/analyze`, plus `GET /` to serve the page.
- Validates presence of a file, filename, and extension (`pdf`, `png`, `jpg`, `jpeg`).
- Enforces a 10 MB upload cap (`MAX_CONTENT_LENGTH`).
- Saves the upload to `uploads/` under its `secure_filename`, always deletes it
  again in a `finally` block — nothing persists across requests.
- Catches any extraction/analysis exception and returns it as a clean `500`
  JSON error rather than a stack trace.

### `extractor.py`
- `extract_text(filepath)` dispatches on file extension:
  - `.pdf` → `extract_text_from_pdf`: reads every page with `pypdf.PdfReader`,
    joins non-empty pages with a blank line.
  - `.png/.jpg/.jpeg` → `extract_text_from_image`: opens with Pillow, converts
    to RGB if needed, runs `pytesseract.image_to_string`.
- No caching, no preprocessing (no deskew/threshold/contrast correction) —
  OCR quality is whatever Tesseract produces from the raw image.

### `analyzer.py`
- `analyze_content(text) -> dict` is a pure function: given text in, a dict
  out, no side effects. This is what makes it trivially unit-testable
  ([tests/test_analyzer.py](../tests/test_analyzer.py)).
- Runs a fixed set of regex-based heuristics (see below) and produces:
  - `engagement_score`: starts at 100, deducted per heuristic, clamped to `[0, 100]`.
  - `stats`: raw counts (words, hashtags, mentions, urls, emojis, has_question, has_call_to_action).
  - `suggestions`: list of `{category, severity, message}` — `severity` is one
    of `good | low | medium | high`, used by the frontend to color each item.
- Deliberately rule-based rather than calling an LLM/sentiment API — keeps the
  app free, offline-capable, deterministic, and every score is explainable
  (see [limitations.md](limitations.md) for the trade-off this implies).

### Frontend (`templates/index.html`, `static/script.js`, `static/style.css`)
- No build step, no framework, no `node_modules` — plain HTML/CSS/JS served
  directly by Flask's `render_template` / static file handling.
- `script.js` owns all app state as DOM manipulation: drag-and-drop + file
  picker → `POST /api/analyze` via `fetch` → render score circle, stat tiles,
  extracted text, and the suggestions list, or show an error box.
- No client-side validation duplicated from the backend — the server is the
  single source of truth for what's a valid upload.

## Data flow for one request

1. User drops/selects a file → `handleFile()` in `script.js` builds a
   `FormData` and POSTs it.
2. `app.py` validates the request, saves the file to `uploads/`.
3. `extractor.extract_text()` returns raw text (or raises/returns empty).
4. If extraction yields no usable text, `app.py` returns a `422` immediately
   — `analyzer.py` never runs on empty input.
5. `analyzer.analyze_content()` scores the text and returns the suggestions dict.
6. `app.py` responds with `{filename, extracted_text, analysis}` and deletes
   the uploaded file regardless of outcome.
7. Frontend renders the response or shows the error message inline.

## Why this shape

Splitting extraction from analysis means each layer can be tested and
reasoned about independently: `analyzer.py` has no idea whether its input
came from OCR or a PDF, and `extractor.py` has no idea what will be done with
the text it returns. The tradeoff is that any extraction noise (OCR
misreads, dropped characters) flows straight into the analyzer with no
correction step — see [limitations.md](limitations.md).
