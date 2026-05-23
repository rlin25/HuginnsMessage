# mimir/retriever.py

from mimir.index import get_vectorstore


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """
    Accepts a query string, returns the top_k most relevant SOP chunks.

    Each returned dict contains:
      - text: str          — the chunk content
      - document_id: str   — the source SOP document ID (e.g. "SOP-SM-001")
      - sub_type: str      — the sub_type this document covers
      - similarity_score: float  — semantic similarity to the query (higher = more similar)

    Returns an empty list if the index is unavailable or empty.
    Never raises exceptions for no-results.
    """
    try:
        vectorstore = get_vectorstore()
        results = vectorstore.similarity_search_with_score(query, k=top_k)

        chunks = []
        for doc, score in results:
            chunks.append({
                "text": doc.page_content,
                "document_id": doc.metadata.get("document_id", "unknown"),
                "sub_type": doc.metadata.get("sub_type", "unknown"),
                "similarity_score": float(score),
            })

        return chunks

    except Exception as e:
        print(f"[Mimir] Retrieval error: {e}")
        return []
