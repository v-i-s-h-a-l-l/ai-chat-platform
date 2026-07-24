"""Magic-byte MIME validation for uploaded documents."""

from __future__ import annotations

from pathlib import Path

# Client-declared MIME must map to one of these after content sniffing.
ALLOWED_MIMES = frozenset(
    {
        "application/pdf",
        "text/plain",
        "text/markdown",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".text"}
_DOCX_EXTENSIONS = {".docx"}
_PDF_EXTENSIONS = {".pdf"}


def detect_mime(data: bytes, filename: str, claimed_mime: str | None) -> str:
    """Detect MIME from magic bytes + extension; reject spoofed types."""
    if not data:
        raise ValueError("Empty file is not allowed")

    ext = Path(filename).suffix.lower()
    sniffed = _sniff_mime(data, ext)

    if sniffed not in ALLOWED_MIMES:
        raise ValueError(f"Unsupported or unrecognized file type: {sniffed}")

    claimed = (claimed_mime or "").split(";")[0].strip().lower() or "application/octet-stream"

    # Allow common aliases / browser quirks when content matches.
    if claimed in ALLOWED_MIMES and claimed != sniffed:
        # text/plain vs text/markdown is interchangeable for our pipeline
        if {claimed, sniffed} <= {"text/plain", "text/markdown"}:
            return sniffed
        # Some browsers send application/octet-stream — trust sniffed content
        if claimed == "application/octet-stream":
            return sniffed
        raise ValueError(
            f"File content type ({sniffed}) does not match declared type ({claimed})"
        )

    if claimed not in ALLOWED_MIMES and claimed != "application/octet-stream":
        raise ValueError(f"Unsupported file type: {claimed}")

    return sniffed


def _sniff_mime(data: bytes, ext: str) -> str:
    head = data[:8]

    if head.startswith(b"%PDF"):
        return "application/pdf"

    # DOCX is a ZIP container (PK..)
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
        if ext in _DOCX_EXTENSIONS or _looks_like_docx(data):
            return DOCX_MIME
        raise ValueError("ZIP archives are not allowed; upload a .docx Word document")

    if _is_mostly_text(data):
        if ext in {".md", ".markdown"}:
            return "text/markdown"
        return "text/plain"

    if ext in _PDF_EXTENSIONS:
        raise ValueError("File extension is .pdf but content is not a valid PDF")
    if ext in _DOCX_EXTENSIONS:
        raise ValueError("File extension is .docx but content is not a valid Word document")

    return "application/octet-stream"


def _looks_like_docx(data: bytes) -> bool:
    # Minimal OOXML marker inside the ZIP local headers region
    sample = data[:4096]
    return b"word/" in sample or b"[Content_Types].xml" in sample


def _is_mostly_text(data: bytes, sample_size: int = 4096) -> bool:
    sample = data[:sample_size]
    if not sample:
        return False
    # Reject NUL bytes typical of binaries
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        try:
            sample.decode("latin-1")
        except UnicodeDecodeError:
            return False
    # High ratio of printable / whitespace characters
    printable = sum(1 for b in sample if 32 <= b <= 126 or b in (9, 10, 13))
    return (printable / len(sample)) >= 0.85
