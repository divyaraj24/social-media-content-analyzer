# Known Limitations & Design Trade-offs

These are things the app currently doesn't handle, either because they're
fundamental to the tools it's built on, or because they were deliberately
scoped out. Recorded here so they aren't mistaken for bugs.

## OCR cannot see emoji in images

Tesseract is trained to recognize text glyphs, not pictographs. When an
emoji is rendered inside a screenshot (PNG/JPG), OCR silently drops it — it
doesn't misread it, it just never appears in `extracted_text`. Example:

```
Input image text:  "Loving this! 🎉🔥⭐"
OCR output:         "Loving this"
```

Consequences:
- `analyzer.py`'s emoji detection (`EMOJI_RE`) is correct and covers the
  common Unicode ranges (pictographs, dingbats, flags, `⭐`, `⌚/⏰`, `‼️/⁉️`,
  and variation-selector/ZWJ sequences) — but it can only score emoji that
  actually made it into the extracted text.
- **PDF uploads are unaffected** as long as the source PDF embeds real
  Unicode text with emoji-capable fonts (e.g. a PDF exported from an app or
  "printed" from a webpage) — `pypdf` does direct text extraction, not OCR,
  so emoji come through as normal characters.
- **This is not fixable within the current design.** Making image uploads
  emoji-aware would require a cloud OCR/vision service (Google Cloud Vision,
  Azure Computer Vision, or a multimodal LLM) capable of recognizing
  pictographic glyphs. That would need an API key and external network
  calls, which conflicts with the project's explicit goal (see
  [architecture.md](architecture.md) and the README's "Approach" section) of
  being fully offline, free, and deterministic. Decision: accepted as a
  known limitation rather than compromising that design goal.

## OCR quality depends entirely on image clarity

There's no image preprocessing (deskew, contrast/threshold correction,
denoising) before handing the image to Tesseract. Low-resolution
screenshots, unusual fonts, low contrast, or unusual color rendering (e.g.
color emoji rendered as blocky raster art) can all degrade or garble
extracted text. This directly affects the engagement score, since the
analyzer only ever sees what OCR handed it.

## Rule-based analysis, not sentiment/AI-based

`analyzer.py` is deliberately a fixed set of regex-driven heuristics (word
count range, hashtag density, CTA phrase list, question mark presence, emoji
count, link presence) rather than a call to an LLM or sentiment-analysis
API. This was a conscious trade-off:

- **Pro:** free, offline, deterministic, and every score is explainable —
  each suggestion names exactly which rule fired.
- **Con:** no actual understanding of tone, sentiment, humor, or
  platform-specific norms. A sarcastic or ironic post scores the same as a
  sincere one; the CTA phrase list (`CTA_PHRASES` in `analyzer.py`) is a
  fixed, English-only list and will miss CTAs phrased differently or in
  other languages.

## No platform-specific scoring

The "ideal" word count (40–80 words) and hashtag count (3–8) are generic
averages. They don't distinguish between, say, X/Twitter (where brevity is
rewarded) and LinkedIn or Instagram captions (where longer posts often do
better). A single fixed set of thresholds is applied regardless of the
target platform.

## No persistence or history

Uploaded files are deleted immediately after each request (see
[api.md](api.md)) and no analysis results are stored anywhere. There's no
way to look back at a previous upload's score — every request is
stateless and independent.

## No authentication or rate limiting

`/api/analyze` is open to anyone who can reach the server, with no request
throttling beyond the 10 MB body-size cap. Fine for local/demo use; would
need addressing before any public deployment.

## Untested layers

See [testing.md](testing.md#whats-not-covered) — `app.py` (routes/error
codes) and `extractor.py` (actual PDF/OCR extraction) currently have no
automated test coverage, only the pure-function `analyzer.py` does.
