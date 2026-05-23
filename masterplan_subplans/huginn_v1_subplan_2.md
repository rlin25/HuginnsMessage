# Huginn v1 — Subplan 2: Knowledge Base + Mimir

**Component:** `knowledge_base/raw/`, `scripts/build_index.py`, `mimir/retriever.py`, `mimir/index.py`
**Depends on:** Subplan 1 gate must be confirmed passing.
**Gate:** Calling `retrieve()` with a query for each of the three sub-types returns relevant, non-empty chunks with correct metadata fields before Subplan 3 begins.

---

## Reference Documents

- `huginn_v1_interface_contract.md` — Component 4 (Mimir Retriever)
- `huginn_v1_design_decisions.md` — Decisions 2, 8, 12, 22, 23

---

## What to Build

Four things, in order:

1. **Three synthetic SOP documents** in `knowledge_base/raw/`
2. **`scripts/build_index.py`** — one-time preprocessing script
3. **`mimir/index.py`** — Chroma loading and initialization
4. **`mimir/retriever.py`** — the single public retrieval function

---

## Step 1 — Synthetic SOP Documents

Create three `.txt` files in `knowledge_base/raw/`. These represent the internal SOPs of a fictional financial firm, Arcturus Capital Management. Write them to be realistic enough that similarity search works — each should use vocabulary specific to its sub-type.

### `sop_price_mismatch.txt`

```
ARCTURUS CAPITAL MANAGEMENT
Standard Operating Procedure — Settlement Price Mismatch
Document ID: SOP-SM-001
Sub-type: price_mismatch

OVERVIEW
A price mismatch exception arises when the settlement price recorded in Arcturus's internal systems differs from the price confirmed by the counterparty or custodian at settlement. Price discrepancies must be resolved before settlement can proceed, as they directly affect the cash leg of the transaction.

IDENTIFICATION
Price mismatch exceptions are flagged when the absolute difference between Arcturus's recorded settlement price and the counterparty's confirmed price exceeds 0.01 per unit, or when a percentage variance of more than 0.05% is observed on fixed-income instruments.

RESOLUTION PROCEDURE
Step 1 — Verify both parties' trade confirmations against the original execution report. Retrieve the original term sheet or execution message from the order management system.
Step 2 — Identify the source of discrepancy. Common causes include: accrued interest calculation differences (particularly for bonds settling between coupon dates), incorrect clean vs. dirty price treatment, currency conversion rounding, and data entry errors on either side.
Step 3 — Contact the counterparty operations desk directly via SWIFT MT535/MT536 message or phone to confirm their recorded price and request their original execution confirmation.
Step 4 — If the Arcturus price is incorrect: amend the trade record in the order management system and obtain supervisor sign-off before resubmitting to the clearinghouse.
Step 5 — If the counterparty price is incorrect: provide the counterparty with documentary evidence (original execution report, exchange confirmation) and request they submit an amendment.
Step 6 — If the source cannot be resolved within 2 hours of exception flag: escalate to the Senior Settlement Manager and place the trade in the pending queue.
Step 7 — Document all communications and the final resolution in the exception log with timestamps.

ESCALATION TRIGGERS
- Either party cannot provide documentary evidence of agreed price
- Discrepancy exceeds 0.5% of trade value
- Trade is on the sanctions watchlist (escalate immediately to Compliance)
- Trade involves AML-flagged counterparty (escalate immediately to Compliance)

AUTO-RESOLUTION CRITERIA
Auto-resolution is appropriate when: the discrepancy source is identified and attributable to a known calculation difference (e.g. accrued interest), both parties agree on the corrected price, and the amendment is processed and confirmed by both sides within the resolution window.
```

### `sop_quantity_mismatch.txt`

```
ARCTURUS CAPITAL MANAGEMENT
Standard Operating Procedure — Settlement Quantity Mismatch
Document ID: SOP-SM-002
Sub-type: quantity_mismatch

OVERVIEW
A quantity mismatch exception arises when the number of securities units recorded in Arcturus's settlement instructions differs from the quantity confirmed by the counterparty or custodian. Quantity mismatches affect the securities leg of the transaction and can result in partial settlement or complete settlement failure if unresolved.

IDENTIFICATION
Quantity mismatch exceptions are flagged when the settlement instruction quantity from either party does not match, regardless of the magnitude of the discrepancy. Even a single unit difference prevents matched settlement.

RESOLUTION PROCEDURE
Step 1 — Pull both parties' settlement instructions from the SWIFT MT54x message history. Compare the securities quantity field in each instruction.
Step 2 — Cross-reference against the original trade confirmation (MT515 or equivalent). The agreed quantity should be recorded there unambiguously.
Step 3 — Identify the source of discrepancy. Common causes include: partial fill execution that was not properly consolidated, stock split or corporate action applied inconsistently, lot allocation errors in multi-portfolio trades, and clerical data entry errors.
Step 4 — If a corporate action (stock split, rights issue) affected the position between trade date and settlement date, verify that both parties applied the adjustment with the same ex-date and ratio.
Step 5 — Contact the counterparty operations desk to confirm their source quantity and request their trade confirmation documentation.
Step 6 — If the Arcturus quantity is incorrect: amend the settlement instruction and resubmit. Obtain supervisor approval if the amendment exceeds 10% of original quantity.
Step 7 — If the counterparty quantity is incorrect: provide documentary evidence and request their amendment.
Step 8 — If a partial settlement is acceptable to both parties, document the partial agreement and create a new exception record for the remaining quantity.
Step 9 — If not resolved within 3 hours of exception flag: escalate to Senior Settlement Manager.

ESCALATION TRIGGERS
- Neither party can produce original trade confirmation with agreed quantity
- Discrepancy exceeds 5% of total trade quantity
- Corporate action dispute that cannot be resolved with the registrar
- Counterparty is subject to regulatory hold

AUTO-RESOLUTION CRITERIA
Auto-resolution is appropriate when: the source of the discrepancy is a documented calculation error or data entry error on one side, both parties agree on the corrected quantity, and the amended settlement instruction is matched and confirmed.
```

### `sop_wrong_settlement_date.txt`

```
ARCTURUS CAPITAL MANAGEMENT
Standard Operating Procedure — Wrong Settlement Date
Document ID: SOP-SM-003
Sub-type: wrong_settlement_date

OVERVIEW
A wrong settlement date exception arises when the settlement date recorded in Arcturus's system or submitted to the clearinghouse differs from the date expected by the counterparty. Settlement date mismatches can cause failed settlements, penalty charges under CSDR (Central Securities Depositories Regulation), and overnight financing costs.

IDENTIFICATION
Wrong settlement date exceptions are flagged when Arcturus's settlement instruction specifies a value date that does not match the counterparty's instruction. The standard settlement cycle for US equities is T+1 (one business day after trade date). Fixed income and other instruments may have different standard cycles.

RESOLUTION PROCEDURE
Step 1 — Confirm the trade date and the applicable settlement convention for the instrument type. US equities: T+1. US Treasuries: T+1. Corporate bonds: T+2 in some markets. FX spot: T+2. Reference the instrument's settlement convention in the system.
Step 2 — Check whether either the trade date or settlement date contains a holiday or non-business day adjustment error. Use the exchange or market calendar to confirm the correct settlement date calculation.
Step 3 — Retrieve both parties' SWIFT MT54x settlement instructions and compare the value date field directly.
Step 4 — Identify the source of discrepancy. Common causes include: holiday calendar not updated for the relevant market, system applying wrong settlement convention for the instrument type, manual date entry error, and time-zone boundary issues for trades executed near end-of-day.
Step 5 — If Arcturus's date is incorrect: cancel and resubmit the settlement instruction with the correct value date immediately. Settlement date amendments are time-sensitive — delays can cause the trade to fall outside the clearinghouse's amendment window.
Step 6 — If the counterparty's date is incorrect: contact their operations desk immediately and request amendment. Provide documentary evidence of the correct settlement convention.
Step 7 — If the settlement date has already passed (failed settlement): calculate penalty charges per the applicable CSDR/internal penalty schedule and report to the Senior Settlement Manager.
Step 8 — If not resolved within 1 hour of exception flag: escalate to Senior Settlement Manager. Wrong settlement date exceptions are the most time-critical settlement mismatch type.

ESCALATION TRIGGERS
- Settlement date has already passed (failed settlement)
- Amendment window at clearinghouse is at risk of closing
- Dispute involves cross-border settlement with conflicting holiday calendars
- Counterparty refuses to amend without management approval

AUTO-RESOLUTION CRITERIA
Auto-resolution is appropriate when: the correct settlement date is unambiguously determinable from the instrument's settlement convention, the amendment window is still open, and the amended instruction is submitted and matched before the clearinghouse cutoff.
```

---

## Step 2 — Build Index Script

```python
# scripts/build_index.py
# Run once from project root: python scripts/build_index.py

from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

RAW_DIR = Path("knowledge_base/raw")
PERSIST_DIR = "knowledge_base/processed"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

# Sub-type metadata map — keyed on filename stem
DOCUMENT_METADATA = {
    "sop_price_mismatch": {
        "document_id": "SOP-SM-001",
        "sub_type": "price_mismatch",
    },
    "sop_quantity_mismatch": {
        "document_id": "SOP-SM-002",
        "sub_type": "quantity_mismatch",
    },
    "sop_wrong_settlement_date": {
        "document_id": "SOP-SM-003",
        "sub_type": "wrong_settlement_date",
    },
}

def build_index():
    print("Loading documents...")
    all_chunks = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " "],
    )

    for txt_file in sorted(RAW_DIR.glob("*.txt")):
        stem = txt_file.stem
        metadata = DOCUMENT_METADATA.get(stem)
        if not metadata:
            print(f"  WARNING: No metadata mapping for {txt_file.name} — skipping")
            continue

        loader = TextLoader(str(txt_file))
        docs = loader.load()
        chunks = splitter.split_documents(docs)

        # Attach metadata to every chunk
        for chunk in chunks:
            chunk.metadata.update(metadata)

        print(f"  {txt_file.name}: {len(chunks)} chunks → document_id={metadata['document_id']}")
        all_chunks.extend(chunks)

    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"Loading embeddings model: {EMBEDDING_MODEL}")
    print("  (First run downloads ~420MB — subsequent runs use local cache)")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print(f"\nBuilding Chroma index at {PERSIST_DIR}...")
    vectorstore = Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
    )

    print(f"Index built. {vectorstore._collection.count()} vectors stored.")
    print("Done. Run mimir/retriever.py smoke test to verify.")

if __name__ == "__main__":
    build_index()
```

Run after creating the SOP files:
```bash
python scripts/build_index.py
```

---

## Step 3 — Mimir Index Loader

```python
# mimir/index.py

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

PERSIST_DIR = "knowledge_base/processed"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

_vectorstore = None


def get_vectorstore() -> Chroma:
    """
    Returns the Chroma vectorstore, initializing it on first call.
    Subsequent calls return the cached instance.
    """
    global _vectorstore
    if _vectorstore is None:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        _vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings,
        )
    return _vectorstore
```

---

## Step 4 — Mimir Retriever

```python
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
```

---

## Gate Verification Script

Run from project root after building the index:

```python
# python tests/test_mimir_smoke.py

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
```

**Expected output:**
```
PASS: price_mismatch query → SOP-SM-001 (score: 0.XXXX)
PASS: quantity_mismatch query → SOP-SM-002 (score: 0.XXXX)
PASS: wrong_settlement_date query → SOP-SM-003 (score: 0.XXXX)

All Mimir smoke tests passed. Gate cleared for Subplan 3.
```

---

## Notes

- Chroma similarity scores from `similarity_search_with_score` are L2 distances — lower values mean higher similarity. The smoke test does not assert on specific score values, only that a score is present and is a float.
- The vectorstore is initialized lazily in `mimir/index.py` — the first call to `retrieve()` in a process will load the embedding model into memory. This takes a few seconds. Subsequent calls in the same process are fast.
- Do not import from `agent/`, `logger/`, `api/`, or `models/` in this component.
