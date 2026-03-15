"""
Chunker - Split extracted text into overlapping chunks for embedding.

Strategy (in priority order):
  1. Split on paragraph boundaries (double newlines)
  2. If a paragraph exceeds chunk_size, split on sentence boundaries
  3. As a last resort, split on word boundaries

Section headers (Markdown `#`…`######` or ALL-CAPS short lines) are
detected and attached to every subsequent chunk as metadata.

Independently testable:
    python -m app.services.chunker
"""

import re
from dataclasses import dataclass, field

from app.services.document_processor import ProcessedDocument


@dataclass
class Chunk:
    """A single text chunk ready for embedding and storage."""
    id: str                  # "{doc_id}_chunk_{index}"
    text: str
    doc_id: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)
    # metadata keys: filename, file_type, section_header,
    #                char_start, char_end, word_count, uploaded_at, section


# ── Public API ───────────────────────────────────────────────

def chunk_document(
    doc: ProcessedDocument,
    doc_id: str,
    chunk_size: int = 500,
    overlap: int = 50,
    uploaded_at: str = "",
    source_path: str = "",
) -> list[Chunk]:
    """
    Split a ProcessedDocument into Chunk objects.

    Args:
        doc:         Output of document_processor.process_file().
        doc_id:      Unique identifier for the parent document.
        chunk_size:  Target chunk length in characters.
        overlap:     Characters of the previous chunk to prepend to the next.
        uploaded_at: ISO 8601 timestamp string stored in each chunk's metadata.

    Returns:
        List of non-empty Chunk objects in document order.
    """
    filename = doc.metadata.get("filename", "")
    file_type = doc.metadata.get("file_type", "")
    word_count = doc.metadata.get("word_count", 0)

    units = _split_into_units(doc.text, chunk_size)

    chunks: list[Chunk] = []
    current_text = ""
    current_section: str | None = None
    char_cursor = 0   # approximate character position in original text

    def _flush(text: str, section: str | None, start: int) -> None:
        text = text.strip()
        if not text:
            return
        idx = len(chunks)
        chunks.append(Chunk(
            id=f"{doc_id}_chunk_{idx}",
            text=text,
            doc_id=doc_id,
            chunk_index=idx,
            metadata={
                "filename":       filename,
                "file_type":      file_type,
                "section_header": section or "",
                "section":        section or "",
                "char_start":     start,
                "char_end":       start + len(text),
                "word_count":     word_count,
                "uploaded_at":    uploaded_at,
                "source_path":    source_path,
                "total_chunks":   0,  # backfilled below
            },
        ))

    for unit in units:
        # Track current section header
        detected = _detect_header(unit)
        if detected:
            current_section = detected

        separator = "\n\n" if current_text else ""
        candidate = current_text + separator + unit

        if len(candidate) <= chunk_size:
            current_text = candidate
        else:
            # Flush the accumulated text, then start a new chunk
            chunk_start = char_cursor - len(current_text)
            _flush(current_text, current_section, max(0, chunk_start))

            # Carry overlap from the tail of the flushed chunk
            if overlap and current_text:
                tail = current_text[-overlap:]
                current_text = tail + "\n\n" + unit
            else:
                current_text = unit

        char_cursor += len(unit) + 2  # +2 for the separator

    # Flush whatever remains
    _flush(current_text, current_section, max(0, char_cursor - len(current_text)))

    # Backfill total_chunks now that we know the final count
    total = len(chunks)
    for c in chunks:
        c.metadata["total_chunks"] = total

    return chunks


# ── Private helpers ───────────────────────────────────────────

def _split_into_units(text: str, chunk_size: int) -> list[str]:
    """
    Produce a flat list of text units by splitting paragraphs,
    then long paragraphs into sentences, then long sentences into words.
    """
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    units: list[str] = []
    for para in paragraphs:
        if len(para) <= chunk_size:
            units.append(para)
        else:
            # Try sentence splitting
            sentences = _split_sentences(para)
            for sent in sentences:
                if len(sent) <= chunk_size:
                    units.append(sent)
                else:
                    # Fall back to word splitting
                    units.extend(_split_words(sent, chunk_size))

    return units


def _split_sentences(text: str) -> list[str]:
    """Split on sentence-ending punctuation followed by whitespace."""
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _split_words(text: str, chunk_size: int) -> list[str]:
    """Split on word boundaries to fit within chunk_size."""
    words = text.split()
    result: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > chunk_size:
            result.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        result.append(current)
    return result


def _detect_header(text: str) -> str | None:
    """
    Return the header text if the unit looks like a section header.
    Matches Markdown headers (# … ######) and short ALL-CAPS lines.
    """
    stripped = text.strip()

    # Markdown header
    md_match = re.match(r"^#{1,6}\s+(.+)$", stripped)
    if md_match:
        return md_match.group(1).strip()

    # Short ALL-CAPS line (e.g. "BENEFITS", "TOOLS & ACCESS")
    if len(stripped) <= 60 and stripped == stripped.upper() and stripped.isalpha():
        return stripped.title()

    return None


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from app.services.document_processor import process_file

    path = sys.argv[1] if len(sys.argv) > 1 else "test_docs/sample_handbook.md"
    doc = process_file(path)
    chunks = chunk_document(doc, doc_id="test123", chunk_size=500, overlap=50)

    print(f"Document:  {doc.metadata['filename']}")
    print(f"Chunks:    {len(chunks)}")
    for c in chunks[:3]:
        section = c.metadata.get("section") or "—"
        print(f"\n[{c.id}] section={section!r}  chars={len(c.text)}")
        print(c.text[:200])
