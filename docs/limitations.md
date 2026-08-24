# Known Limitations & Design Trade-offs

These are things the app currently doesn't handle, either because they're
fundamental to the tools it's built on, or because they were deliberately
scoped out. Recorded here so they aren't mistaken for bugs.

## OCR cannot see emoji in images — resolved via optional vision fallback

Tesseract is trained to recognize text glyphs, not pictographs. When an
emoji is rendered inside a screenshot (PNG/JPG), OCR silently drops it — it
doesn't misread it, it just never appears in `extracted_text`:

```
Input image text:  "Loving this! 🎉🔥⭐"
Tesseract OCR:      "Loving this"
```

This was originally accepted as a permanent limitation (see git history),
since fixing it meant leaving Tesseract behind for images entirely — no
amount of image preprocessing or better regex helps when the emoji glyphs
never reach `extracted_text` in the first place.

**Fix:** `extract_text_from_image()` in [extractor.py](../extractor.py) now
tries Gemini Flash (vision) first — `gemini-2.5-flash` via the `google-genai`
SDK, `temperature=0` for consistent transcription — and only falls back to
Tesseract OCR if no `GEMINI_API_KEY` is configured or the API call fails for
any reason (network error, invalid key, rate limit, etc.):

```
Input image text:  "Loving this! 🎉🔥⭐"
Vision output:      "Loving this! 🎉🔥⭐"
```

**Why a vision LLM instead of a dedicated OCR API** (Google Cloud Vision,
Azure Computer Vision): those are still fundamentally *text*-OCR services —
built to recognize character glyphs, the same category of tool as
Tesseract, just better-trained. They weren't guaranteed to close the gap on
the actual problem (pictograph recognition). A vision-capable LLM doesn't
"OCR" the image at all — it visually interprets everything in it, text and
pictographs alike, the same way it would describe a photo. Asked to
transcribe the image verbatim (see `_VISION_PROMPT` in `extractor.py`), it
reads emoji as content rather than trying to match them against a character
set, which is exactly the capability Tesseract lacks.

**Why Gemini Flash specifically:** it's natively multimodal (text + vision
in one model, no separate OCR endpoint to wire up), the `google-genai` SDK
call is a few lines, and it's available on Google AI Studio's free tier —
an API key from [aistudio.google.com](https://aistudio.google.com) takes
under a minute to get.

**The free tier's actual daily limit is low, and per-model.** Google no
longer publishes static numbers on its rate-limits page — it points to
your own live usage at
[aistudio.google.com/rate-limit](https://aistudio.google.com/rate-limit),
since limits vary by account and model. In practice, testing this feature
hit the real ceiling for `gemini-2.5-flash` quickly: the API's own error
response reported `limit: 20,
quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier` — 20 requests
*per day* for that model on a free-tier key, not the far higher figure an
earlier version of this doc assumed. Once that's hit, every request gets a
`429 RESOURCE_EXHAUSTED` until the quota resets (daily).

**This is handled, not just documented:**
- The quota is tracked *per model*, not per account — `_extract_text_from_image_vision`
  in [extractor.py](../extractor.py) retries a 429 once (see the retry
  section below), and if that also fails, falls straight back to Tesseract
  OCR exactly like any other failure. A day-exhausted key doesn't break
  image uploads — it just silently loses emoji detection until the quota
  resets.
- Because the limit is per-model, switching models sidesteps an exhausted
  quota without a code change: `GEMINI_MODEL=gemini-flash-lite-latest`
  (or another current model) draws from a separate daily allowance. Verified
  working — including correct emoji transcription, not just plain text —
  as a same-key workaround when `gemini-2.5-flash`'s quota was exhausted.
  Set it in your shell before `python app.py`, or as a Render env var
  alongside `GEMINI_API_KEY`.

**One retry on transient failures (429, 5xx, network/timeout):** a jittered
~2-3s delay (`2s + random.uniform(0, 1)`, not a flat delay, so concurrent
requests don't retry in lockstep), then bail to Tesseract if the retry also
fails. Non-transient errors (bad key, bad request) skip the retry entirely
— it would just fail again identically. Capped at exactly one retry on
purpose: this is an optional enhancement layered on top of a working
offline fallback, not the core path, so a slow/unhappy Gemini shouldn't
make the user wait long for a feature they might not even have configured.

**A note on determinism:** default sampling occasionally dropped emoji
from an otherwise-correct transcription (~1 in 4 in testing). Setting
`temperature=0` on the Gemini request fixed this — verified consistent
across repeated runs on the same image before shipping. For a
transcription task, literal fidelity matters more than variation, so `0` is
the right setting here.

**How it helps in practice:**
- Emoji, hashtags, mentions, and punctuation all come through correctly in
  the transcription, so `analyzer.py`'s existing `EMOJI_RE` heuristic (which
  was already broadened to cover more Unicode ranges — see git history) now
  has real emoji to detect in the first place, instead of text that never
  had it.
- It also tends to produce a cleaner transcription than Tesseract generally
  — no image preprocessing (deskew/contrast) is needed, since the model is
  reading the image holistically rather than glyph-by-glyph.

**Trade-offs of this fix:**
- **Needs network access and an external API call** — no longer strictly
  offline for image uploads the way PDF analysis and the original Tesseract
  path are. In practice it stays free at this app's scale thanks to the
  Google AI Studio free tier, but it's still a third-party dependency the
  original design deliberately avoided (see the "Rule-based analysis"
  section below).
- **Requires `GEMINI_API_KEY`.** Without it configured, the app falls back
  to the original Tesseract-only behavior automatically — no crash, no
  degraded UX beyond emoji being dropped exactly as before. This keeps the
  zero-config/free path fully intact for anyone who doesn't set the key.
- **PDF uploads were never affected** by any of this — `pypdf` does direct
  text extraction (not OCR), so emoji in a PDF's embedded text always came
  through as normal characters, with or without this change.

See [setup.md](setup.md) and [deployment.md](deployment.md) for how to
configure `GEMINI_API_KEY` locally and on Render.

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
