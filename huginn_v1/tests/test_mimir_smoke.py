# python tests/test_mimir_smoke.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mimir.retriever import retrieve

test_cases = [
    {
        "label": "price_mismatch query",
        "query": "price_mismatch: Counterparty confirms settlement at 102.50 but our records show 101.75",
        "expected_doc_id": "SOP-SM-001",
        "expected_sub_type": "price_mismatch",
    },
    {
        "label": "quantity_mismatch query",
        "query": "quantity_mismatch: Our records indicate 10,000 shares but counterparty confirms 9,500 shares",
        "expected_doc_id": "SOP-SM-002",
        "expected_sub_type": "quantity_mismatch",
    },
    {
        "label": "wrong_settlement_date query",
        "query": "wrong_settlement_date: Settlement date recorded as 2026-05-16 but counterparty expects 2026-05-17",
        "expected_doc_id": "SOP-SM-003",
        "expected_sub_type": "wrong_settlement_date",
    },
]

all_pass = True
for tc in test_cases:
    chunks = retrieve(tc["query"])
    top = chunks[0] if chunks else None

    if not top:
        print(f"FAIL: {tc['label']} — no chunks returned")
        all_pass = False
        continue

    # Top result should match expected document
    doc_match = top["document_id"] == tc["expected_doc_id"]
    sub_match = top["sub_type"] == tc["expected_sub_type"]
    has_text = bool(top.get("text"))
    has_score = isinstance(top.get("similarity_score"), float)

    if doc_match and sub_match and has_text and has_score:
        print(f"PASS: {tc['label']} → {top['document_id']} (score: {top['similarity_score']:.4f})")
    else:
        print(f"FAIL: {tc['label']}")
        print(f"  document_id: expected {tc['expected_doc_id']}, got {top['document_id']}")
        print(f"  sub_type: expected {tc['expected_sub_type']}, got {top['sub_type']}")
        print(f"  has_text: {has_text}, has_score: {has_score}")
        all_pass = False

if all_pass:
    print("\nAll Mimir smoke tests passed. Gate cleared for Subplan 3.")
else:
    print("\nOne or more tests failed. Do not proceed to Subplan 3.")
