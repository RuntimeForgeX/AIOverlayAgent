"""
File parsers for extracting text from PDF, DOCX, and TXT files.
"""

from pathlib import Path


def detect_file_type(file_path: str) -> str:
    """Detect file type from extension."""
    ext = Path(file_path).suffix.lower()
    mapping = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".doc": "docx",
        ".txt": "txt",
        ".md": "txt",
        ".text": "txt",
    }
    return mapping.get(ext, "txt")


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using PyPDF2."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        return "\n\n".join(pages)
    except Exception as e:
        return f"[Error extracting PDF: {e}]"


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        from docx import Document

        doc = Document(file_path)
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        return "\n\n".join(paragraphs)
    except Exception as e:
        return f"[Error extracting DOCX: {e}]"


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from a plain text file."""
    try:
        return Path(file_path).read_text(encoding="utf-8", errors="replace").strip()
    except Exception as e:
        return f"[Error reading text file: {e}]"


def extract_text(file_path: str) -> str:
    """Extract text from a file based on its type."""
    file_type = detect_file_type(file_path)
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    elif file_type == "docx":
        return extract_text_from_docx(file_path)
    else:
        return extract_text_from_txt(file_path)
