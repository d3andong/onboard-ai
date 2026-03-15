"""
File Helpers - Utilities for managing uploaded files on the local filesystem.
"""

import os
from pathlib import Path

from app.config import settings

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}


def get_upload_path(doc_id: str, filename: str) -> str:
    """Return the absolute path where a file should be saved."""
    safe_name = Path(filename).name  # Strip any path traversal
    return os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{safe_name}")


def delete_upload_file(doc_id: str) -> bool:
    """
    Delete the uploaded file associated with doc_id.

    Scans UPLOAD_DIR for any file whose name starts with "{doc_id}_".
    Returns True if a file was deleted, False otherwise.
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    prefix = f"{doc_id}_"
    for entry in upload_dir.iterdir():
        if entry.is_file() and entry.name.startswith(prefix):
            entry.unlink()
            return True
    return False


def validate_extension(filename: str) -> str:
    """
    Return the lowercase extension if supported.

    Raises:
        ValueError: Extension is not in SUPPORTED_EXTENSIONS.
    """
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported types: {supported}"
        )
    return ext


def validate_size(content: bytes, max_mb: int | None = None) -> None:
    """
    Raise ValueError if content exceeds max_mb megabytes.

    Args:
        content: Raw file bytes.
        max_mb:  Size limit in megabytes. Defaults to settings.MAX_FILE_SIZE_MB.
    """
    limit_mb = max_mb if max_mb is not None else settings.MAX_FILE_SIZE_MB
    limit_bytes = limit_mb * 1024 * 1024
    if len(content) > limit_bytes:
        raise ValueError(
            f"File too large ({len(content) / 1024 / 1024:.1f} MB). "
            f"Maximum allowed: {limit_mb} MB."
        )
