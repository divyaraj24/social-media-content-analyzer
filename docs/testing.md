# Testing

## Running the suite

```bash
source .venv/bin/activate
pip install pytest   # not in requirements.txt — dev-only dependency
python -m pytest tests/ -v
```

## What's covered

[tests/test_analyzer.py](../tests/test_analyzer.py) unit-tests
`analyzer.analyze_content()` directly (no Flask, no file I/O, no OCR — it's a
pure function, so tests just pass strings in and assert on the returned
dict):

| Test | Asserts |
|---|---|
| `test_detects_hashtags` | Hashtag count matches the number of `#tag` tokens in the text. |
| `test_detects_call_to_action` | A known CTA phrase (e.g. "comment below") sets `has_call_to_action`. |
| `test_detects_question` | A `?` in the text sets `has_question`. |
| `test_score_within_bounds` | `engagement_score` always stays within `[0, 100]`. |
| `test_no_hashtags_flagged` | Text with zero hashtags produces a `"Hashtags"` suggestion. |

## What's not covered

There is currently no automated coverage for:

- **`app.py`** — the Flask routes (file validation, error status codes,
  upload cleanup). Would need Flask's test client (`app.test_client()`).
- **`extractor.py`** — PDF/OCR extraction itself. Would need fixture files
  (a sample PDF, a sample image) checked into the repo, or generated at test
  time (e.g. with `reportlab` for a PDF, `Pillow.ImageDraw` for an image —
  see manual verification approach below).
- Extraction failure modes (corrupt file, unreadable PDF, blank image).

## Adding a new heuristic to `analyzer.py`

1. Add the detection logic and score adjustment inside `analyze_content()`.
2. Add a corresponding `suggestions.append({...})` entry with a `category`,
   `severity`, and `message`.
3. Add a test in `tests/test_analyzer.py` asserting on `stats` or
   `suggestions` for representative input — follow the existing pattern of
   one focused assertion per test.
4. Re-run `python -m pytest tests/ -v`.

## Manually verifying extraction (PDF/OCR)

Since there's no fixture-based test for `extractor.py` yet, verify by hand
after any change to `extractor.py` or the emoji/text regexes in
`analyzer.py`:

```bash
# Image (OCR) path
python3 -c "
from PIL import Image, ImageDraw
img = Image.new('RGB', (600, 100), color='white')
ImageDraw.Draw(img).text((10, 10), 'Check this out! #test', fill='black')
img.save('/tmp/sample.png')
"
python3 -c "from extractor import extract_text_from_image; print(extract_text_from_image('/tmp/sample.png'))"

# End-to-end via the running app
curl -s -X POST -F "file=@/tmp/sample.png" http://localhost:5000/api/analyze | python3 -m json.tool
```
