"""Turn uploaded files into plain text, page by page."""

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

SUPPORTED_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
}
SUPPORTED_EXTENSIONS = {".pdf": "pdf", ".txt": "txt", ".md": "md"}


class ExtractionError(ValueError):
    pass


def detect_kind(filename: str, content_type: str | None) -> str:
    if content_type in SUPPORTED_TYPES:
        return SUPPORTED_TYPES[content_type]
    lower = filename.lower()
    for ext, kind in SUPPORTED_EXTENSIONS.items():
        if lower.endswith(ext):
            return kind
    raise ExtractionError("Unsupported file type. Upload a PDF, TXT or Markdown file.")


def extract_pages(data: bytes, kind: str) -> list[str]:
    """Return one text string per page (text files count as a single page)."""
    if kind == "pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = [(page.extract_text() or "") for page in reader.pages]
        except PdfReadError as exc:
            raise ExtractionError(f"Could not read PDF: {exc}") from exc
    else:
        try:
            pages = [data.decode("utf-8")]
        except UnicodeDecodeError:
            pages = [data.decode("latin-1")]

    if not any(p.strip() for p in pages):
        raise ExtractionError(
            "No text found in the file. Scanned PDFs need OCR before upload."
        )
    return pages
