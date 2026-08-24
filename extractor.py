"""
Text extraction utilities.

- PDFs: parsed with pypdf, preserving page-by-page text.
- Images: transcribed by Gemini Flash (vision) when GEMINI_API_KEY is set
  (this is what lets emoji survive — Tesseract OCR is text-glyph-only and
  drops pictographs entirely, see docs/limitations.md), falling back to
  Tesseract OCR via pytesseract otherwise.
"""
import os
import random
import time

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pypdf import PdfReader
from PIL import Image
import pytesseract

_VISION_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
_VISION_TIMEOUT_MS = 20_000
_VISION_RETRY_BASE_DELAY_SECONDS = 2.0
_VISION_RETRY_JITTER_SECONDS = 1.0
_VISION_PROMPT = (
    "Transcribe every piece of text visible in this image exactly as it "
    "appears, including all emoji, hashtags, @mentions, and punctuation. "
    "Output ONLY the raw transcription with no commentary, preamble, or "
    "markdown formatting."
)


def extract_text_from_pdf(filepath: str) -> str:
    reader = PdfReader(filepath)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text.strip())
    return "\n\n".join(t for t in pages_text if t)


def _is_retryable(exc: Exception) -> bool:
    """5xx (model overloaded, etc.), 429 (rate limit), and network/timeout
    errors are worth one retry. Other 4xx (bad API key, bad request) are
    not - the retry would just fail again identically."""
    if isinstance(exc, (genai_errors.ServerError, httpx.TransportError)):
        return True
    if isinstance(exc, genai_errors.ClientError) and exc.code == 429:
        return True
    return False


def _call_gemini_vision(client: "genai.Client", image: Image.Image):
    return client.models.generate_content(
        model=_VISION_MODEL,
        contents=[_VISION_PROMPT, image],
        config=types.GenerateContentConfig(
            temperature=0,
            http_options=types.HttpOptions(timeout=_VISION_TIMEOUT_MS),
        ),
    )


def _extract_text_from_image_vision(filepath: str) -> str | None:
    """Transcribe an image via Gemini vision. Returns None (rather than
    raising) on any failure - missing/invalid credentials, network error,
    etc. - so the caller can fall back to Tesseract OCR. Logs which path
    ran (and why it fell back) so that's never a silent guess.

    Transient errors (5xx, 429 rate limits, connection/timeout issues) get
    one retry after a jittered ~2-3s delay - long enough to clear a
    rate-limit window, jittered so concurrent requests don't all retry in
    lockstep. Non-transient errors (bad API key, bad request) fail straight
    to the OCR fallback - retrying those just wastes a call. Exactly one
    retry, then bail: this is an optional enhancement, not the core path -
    reliability of Tesseract-as-fallback matters more than squeezing value
    out of a flaky Gemini call."""
    if not os.environ.get("GEMINI_API_KEY"):
        print("[extractor] GEMINI_API_KEY not set - using Tesseract OCR (no emoji detection)")
        return None
    try:
        client = genai.Client()
        image = Image.open(filepath)
        try:
            response = _call_gemini_vision(client, image)
        except Exception as exc:
            if not _is_retryable(exc):
                raise
            delay = _VISION_RETRY_BASE_DELAY_SECONDS + random.uniform(0, _VISION_RETRY_JITTER_SECONDS)
            print(f"[extractor] Gemini vision transient error ({exc!r}), retrying once in {delay:.1f}s")
            time.sleep(delay)
            response = _call_gemini_vision(client, image)
        text = (response.text or "").strip()
        if not text:
            print("[extractor] Gemini vision returned empty text - falling back to Tesseract OCR")
            return None
        print(f"[extractor] used Gemini vision ({_VISION_MODEL}) for image extraction")
        return text
    except Exception as exc:
        print(f"[extractor] Gemini vision call failed ({exc!r}) - falling back to Tesseract OCR")
        return None


def _extract_text_from_image_ocr(filepath: str) -> str:
    image = Image.open(filepath)
    # Convert to RGB to avoid issues with palette/CMYK images.
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")
    text = pytesseract.image_to_string(image)
    return text.strip()


def extract_text_from_image(filepath: str) -> str:
    vision_text = _extract_text_from_image_vision(filepath)
    if vision_text is not None:
        return vision_text
    return _extract_text_from_image_ocr(filepath)


def extract_text(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext in (".png", ".jpg", ".jpeg"):
        return extract_text_from_image(filepath)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")
