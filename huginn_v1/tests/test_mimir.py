# tests/test_mimir.py

import pytest
from mimir.retriever import retrieve


class TestMimirRetrieve:

    def test_price_mismatch_returns_correct_document(self):
        query = "price_mismatch: counterparty confirms different price at settlement"
        chunks = retrieve(query)
        assert len(chunks) > 0
        top = chunks[0]
        assert top["document_id"] == "SOP-SM-001"
        assert top["sub_type"] == "price_mismatch"

    def test_quantity_mismatch_returns_correct_document(self):
        query = "quantity_mismatch: our records indicate different number of shares than counterparty"
        chunks = retrieve(query)
        assert len(chunks) > 0
        top = chunks[0]
        assert top["document_id"] == "SOP-SM-002"
        assert top["sub_type"] == "quantity_mismatch"

    def test_wrong_settlement_date_returns_correct_document(self):
        query = "wrong_settlement_date: settlement date in our system does not match counterparty"
        chunks = retrieve(query)
        assert len(chunks) > 0
        top = chunks[0]
        assert top["document_id"] == "SOP-SM-003"
        assert top["sub_type"] == "wrong_settlement_date"

    def test_each_chunk_has_required_fields(self):
        query = "price_mismatch: bond settlement discrepancy"
        chunks = retrieve(query)
        assert len(chunks) > 0
        for chunk in chunks:
            assert "text" in chunk
            assert "document_id" in chunk
            assert "sub_type" in chunk
            assert "similarity_score" in chunk
            assert isinstance(chunk["text"], str)
            assert len(chunk["text"]) > 0
            assert isinstance(chunk["similarity_score"], float)

    def test_returns_empty_list_not_exception_on_unusual_query(self):
        # Unusual query should return something or empty — never raise
        result = retrieve("xyzzy completely unrelated query with no settlement context")
        assert isinstance(result, list)

    def test_top_k_parameter_respected(self):
        query = "price_mismatch: settlement discrepancy"
        chunks = retrieve(query, top_k=1)
        assert len(chunks) <= 1

        chunks = retrieve(query, top_k=2)
        assert len(chunks) <= 2
