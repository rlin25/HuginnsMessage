from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from mimir.index import PERSIST_DIR, EMBEDDING_MODEL

TOP_K_CROSS_REF = 2

SUBSTRING_TO_DOCUMENT_ID = {
    "15c6-1": "SEC-15c6-1",
    "15c6-2": "SEC-15c6-2",
    "11100":  "FINRA-11100",
    "11710":  "FINRA-11710",
    "11810":  "FINRA-11810",
    "11820":  "FINRA-11820",
}

_vectorstore: Chroma | None = None


def _get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL),
        )
    return _vectorstore


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    try:
        vs = _get_vectorstore()

        # Pass 1 — semantic search
        results = vs.similarity_search_with_score(query, k=top_k)
        chunks = [
            {
                "text": doc.page_content,
                "document_id": doc.metadata["document_id"],
                "section_id": doc.metadata["section_id"],
                "similarity_score": float(score),
                "retrieved_via": "primary",
            }
            for doc, score in results
        ]

        # Cross-reference detection
        primary_doc_ids = {c["document_id"] for c in chunks}
        referenced: set[str] = set()
        combined_text = " ".join(c["text"] for c in chunks).lower()
        for substring, full_doc_id in SUBSTRING_TO_DOCUMENT_ID.items():
            if substring in combined_text and full_doc_id not in primary_doc_ids:
                referenced.add(full_doc_id)

        # Pass 2 — targeted cross-reference retrieval
        for full_doc_id in referenced:
            try:
                xref_results = vs.similarity_search_with_score(
                    query,
                    k=TOP_K_CROSS_REF,
                    filter={"document_id": full_doc_id},
                )
                for doc, score in xref_results:
                    chunks.append({
                        "text": doc.page_content,
                        "document_id": doc.metadata["document_id"],
                        "section_id": doc.metadata["section_id"],
                        "similarity_score": float(score),
                        "retrieved_via": "cross_reference",
                    })
            except Exception:
                pass

        # Deduplication by section_id — keep primary over cross_reference
        seen: dict[str, dict] = {}
        for chunk in chunks:
            sid = chunk["section_id"]
            if sid not in seen or chunk["retrieved_via"] == "primary":
                seen[sid] = chunk

        return list(seen.values())

    except Exception:
        return []
