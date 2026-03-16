import json
import os
from datetime import datetime


TEST_QUERY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "test_query")
os.makedirs(TEST_QUERY_DIR, exist_ok=True)


def save_query_response(conversation_id: str, query: str, response) -> None:
    """Save query and response to test_query directory"""
    conv_dir = os.path.join(TEST_QUERY_DIR, f"conversation_{conversation_id}")
    os.makedirs(conv_dir, exist_ok=True)

    existing = [f for f in os.listdir(conv_dir) if f.startswith("query_") and f.endswith(".json")]
    next_index = len(existing) + 1
    filename = os.path.join(conv_dir, f"query_{next_index:03d}.json")

    data = {
        "timestamp": datetime.now().isoformat(),
        "conversation_id": conversation_id,
        "query_index": next_index,
        "query": query,
        "answer": response.answer,
        "processing_time": response.processing_time,
        "model_used": response.model_used,
        "sources": [
            {
                "title": s.title,
                "relevance_score": s.relevance_score,
                "content": s.content,
                "metadata": s.metadata,
            }
            for s in response.sources
        ],
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
