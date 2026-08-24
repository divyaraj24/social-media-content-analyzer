"""
Text extraction utilities.

- PDFs: parsed with pypdf, preserving page-by-page text.
- Images: transcribed by Gemini Flash (vision) when GEMINI_API_KEY is set
  (this is what lets emoji survive — Tesseract OCR is text-glyph-only and
  drops pictographs entirely, see docs/limitations.md), falling back to
  Tesseract OCR via pytesseract otherwise.
"""
import os

from google import genai
from google.genai import types
from pypdf import PdfReader
from PIL import Image
import pytesseract

_VISION_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
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


def _extract_text_from_image_vision(filepath: str) -> str | None:
    """Transcribe an image via Gemini vision. Returns None (rather than
    raising) on any failure - missing/invalid credentials, network error,
    etc. - so the caller can fall back to Tesseract OCR."""
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    try:
        client = genai.Client()
        image = Image.open(filepath)
        response = client.models.generate_content(
            model=_VISION_MODEL,
            contents=[_VISION_PROMPT, image],
            config=types.GenerateContentConfig(temperature=0),
        )
        text = (response.text or "").strip()
        return text or None
    except Exception:
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
