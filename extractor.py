"""
Text extraction utilities.

- PDFs: parsed with pypdf, preserving page-by-page text.
- Images: run through Tesseract OCR via pytesseract.
"""
import os
from pypdf import PdfReader
from PIL import Image
import pytesseract


def extract_text_from_pdf(filepath: str) -> str:
    reader = PdfReader(filepath)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text.strip())
    return "\n\n".join(t for t in pages_text if t)


def extract_text_from_image(filepath: str) -> str:
    image = Image.open(filepath)
    # Convert to RGB to avoid issues with palette/CMYK images.
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")
    text = pytesseract.image_to_string(image)
    return text.strip()


def extract_text(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext in (".png", ".jpg", ".jpeg"):
        return extract_text_from_image(filepath)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")
