def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """
    Split text into overlapping chunks
    """
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


def extract_metadata(text: str, title: str = None) -> dict:
    """
    Extract metadata from document
    """
    return {
        "title": title or "Unknown",
        "length": len(text),
        "word_count": len(text.split())
    }


def format_sources(sources: list) -> str:
    """
    Format sources for display
    """
    formatted = []
    for i, source in enumerate(sources, 1):
        formatted.append(f"{i}. {source.get('title', 'Unknown')}")
    return "\n".join(formatted)
