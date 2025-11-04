from typing import Optional, Dict, Any, List

from agentics.core.extract import extract_payment_info, extract_due_date
from agentics.adapters.pdf import _read_pdf_text, pdf_to_images
from agentics.adapters.ocr import _read_image_text, pdf_to_image_and_ocr
from agentics.io.returns import (
    next_extraction_path,
    next_transcription_path,
    last_transcription_path,
    is_duplicate_transcription,
)


def extract_due_date_from_path(path: str) -> Optional[Dict[str, str]]:
    lower = path.lower()
    text = ""
    if lower.endswith(".txt"):
        text = _read_text_file(path)
    elif lower.endswith(".pdf"):
        text = _read_pdf_text(path)
    elif lower.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")):
        text = _read_image_text(path)
    else:
        return None
    return extract_due_date(text)


def _read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


__all__ = [
    "extract_payment_info",
    "extract_due_date",
    "extract_due_date_from_path",
    "_read_pdf_text",
    "_read_image_text",
    "_read_text_file",
    "pdf_to_images",
    "pdf_to_image_and_ocr",
    "next_extraction_path",
    "next_transcription_path",
    "last_transcription_path",
    "is_duplicate_transcription",
]


