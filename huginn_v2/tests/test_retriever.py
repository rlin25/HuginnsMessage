from mimir.retriever import retrieve


def test_basic_retrieval_structure():
    chunks = retrieve("price_mismatch: counterparty confirms different price than recorded")
    assert len(chunks) > 0
    for chunk in chunks:
        assert "text" in chunk
        assert "document_id" in chunk
        assert "section_id" in chunk
        assert "similarity_score" in chunk
        assert chunk["retrieved_via"] in ("primary", "cross_reference")


def test_two_pass_fires_on_settlement_failure():
    chunks = retrieve("settlement_mismatch: seller failed to deliver securities on settlement date")
    doc_ids = [c["document_id"] for c in chunks]
    print(f"\nRetrieved chunks ({len(chunks)} total):")
    for c in chunks:
        print(f"  [{c['retrieved_via']:15s}] {c['section_id']} (score={c['similarity_score']:.4f})")
        print(f"    {c['text'][:120].strip()!r}")
    assert len(set(doc_ids)) > 1, "Expected chunks from multiple documents"


def test_no_duplicate_section_ids():
    chunks = retrieve("settlement_mismatch: seller failed to deliver securities on settlement date")
    section_ids = [c["section_id"] for c in chunks]
    assert len(section_ids) == len(set(section_ids)), f"Duplicate section_ids: {section_ids}"


def test_empty_query_returns_gracefully():
    chunks = retrieve("")
    assert isinstance(chunks, list)
