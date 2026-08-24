# Social Media Content Analyzer

Upload a screenshot or PDF of a social media post. The app extracts the
text (PDF parsing or OCR) and returns an engagement score with concrete,
actionable suggestions for improving the post.

## Live Demo

**[social-media-content-analyzer-ij1j.onrender.com](https://social-media-content-analyzer-ij1j.onrender.com)**

Hosted on Render's free tier — the first request after a period of
inactivity may take 10–30s while the instance spins back up.

## Features

- **Drag-and-drop or file-picker upload** for PDF, PNG, and JPG files.
- **Text extraction**
  - PDFs are parsed directly with `pypdf` (preserves page order/formatting).
  - Images are run through Tesseract OCR via `pytesseract`, optionally
    upgraded to Gemini vision for emoji-aware extraction — see below.
- **Engagement analysis** (rule-based, no external API/key required):
  - Word count vs. the ideal engagement range
  - Hashtag count and density
  - Call-to-action detection
  - Question / conversation-hook detection
  - Emoji usage
  - Link detection
  - An overall 0–100 engagement score
- Clean error handling and loading states in the UI.

## Tech Stack

- **Backend:** Python, Flask
- **PDF parsing:** pypdf
- **OCR:** pytesseract + Tesseract OCR engine
- **Vision (optional):** Gemini Flash via `google-genai`
- **Frontend:** plain HTML/CSS/JS (no build step, no `node_modules`)

## Setup

```bash
# 1. Install Tesseract OCR (system dependency)
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr
# macOS:
brew install tesseract

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Then open **http://localhost:5000** in your browser.

## Optional Enhancement: Gemini Vision for Emoji Detection

Tesseract OCR can't recognize emoji — it's a text-glyph recognizer, so
pictographs are silently dropped from image uploads before analysis ever
sees them. Setting a `GEMINI_API_KEY` env var switches image extraction to
Gemini Flash (vision), which reads emoji correctly alongside the text:

```bash
export GEMINI_API_KEY=AIza...   # free key: aistudio.google.com
```

This is entirely optional — without it, the app works exactly as before
(Tesseract-only, no emoji on images). With it, image uploads get the same
emoji-aware analysis that PDF uploads already have. Google AI Studio's free
tier (~15 requests/min, 1,500/day) covers this app's usage at no cost. Full
rationale in [docs/limitations.md](docs/limitations.md).

## Project Structure

```
.
├── app.py            # Flask routes / API
├── extractor.py       # PDF parsing + OCR logic
├── analyzer.py         # Engagement scoring & suggestions engine
├── templates/index.html
├── static/style.css
├── static/script.js
├── requirements.txt
└── tests/test_analyzer.py
```

## Approach (write-up)

The app is split into three clean layers: `extractor.py` handles turning
any supported upload into raw text (PDF parsing with pypdf, OCR with
Tesseract for images), `analyzer.py` scores that text against well-known
engagement heuristics (ideal length, hashtag density, presence of a
call-to-action, questions, emojis, links), and `app.py` wires both up
behind a single `/api/analyze` endpoint consumed by a lightweight
vanilla-JS frontend. I chose a rule-based analyzer over an external
AI/sentiment API deliberately: it keeps the app fully self-contained,
deterministic, and free to run with zero API keys or rate limits, while
still giving specific, explainable feedback (not just a black-box
score). Error handling covers unsupported file types, empty extraction
results, and oversized uploads, with loading and error states surfaced
clearly in the UI. Given more time, I'd add a pluggable sentiment/tone
model and platform-specific presets (Instagram vs. LinkedIn vs. X).

## Tests

```bash
python -m pytest tests/
```

## Docs

See [docs/](docs/) for architecture, the API reference, full setup/troubleshooting, testing notes, and known limitations.
