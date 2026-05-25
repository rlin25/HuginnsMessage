# Huginn v2 — Setup Notes

**Status:** Implementation complete. Phase 7 (Feedback Loop) complete.
**Last updated:** May 2026

---

## Environment

- Python 3.10.12
- Linux (WSL2 tested; standard Linux expected to work identically)
- Virtual environment: `venv/` at `huginn_v2/venv/`
- Working directory: `huginn_v2/` (all commands run from here)

---

## Setup Steps

### 1. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API key

Create a `.env` file in the project root (parent of `huginn_v2/`):

```
ANTHROPIC_API_KEY=sk-ant-...
```

The `.env` file may also live at `huginn_v2/.env` — `find_dotenv(usecwd=True)` in `nodes.py` searches upward from the working directory.

**Do not commit `.env`.** It is listed in `.gitignore`.

### 4. Place regulatory documents

The six PDFs must be present in `knowledge_base/raw/` before running the indexer:

| Filename | Source |
|---|---|
| `FINRA-11100.pdf` | FINRA Rulebook — Rule 11100 |
| `FINRA-11710.pdf` | FINRA Rulebook — Rule 11710 |
| `FINRA-11810.pdf` | FINRA Rulebook — Rule 11810 |
| `FINRA-11820.pdf` | FINRA Rulebook — Rule 11820 |
| `SEC-15c6-1.pdf` | eCFR — 17 CFR § 240.15c6-1 |
| `SEC-15c6-2.pdf` | eCFR — 17 CFR § 240.15c6-2 |

### 5. Build the knowledge base index

```bash
python scripts/build_index.py
```

Inspect the chunk inspection log printed to stdout. Confirm all six documents are indexed and section boundaries are semantically correct before running the agent. Do not skip this inspection.

Expected chunk counts (approximate):
- FINRA-11100: ~4 chunks
- FINRA-11710: ~5 chunks
- FINRA-11810: ~14 chunks
- FINRA-11820: ~3 chunks
- SEC-15c6-1: ~4 chunks
- SEC-15c6-2: ~2 chunks

The index is written to `knowledge_base/processed/`. This directory is in `.gitignore`.

### 6. Run tests

```bash
python -m pytest tests/test_models.py tests/test_retriever.py -v
```

Unit tests only (no Claude API call):
- `tests/test_models.py` — 6 tests
- `tests/test_retriever.py` — 4 tests

Full integration tests (requires `ANTHROPIC_API_KEY`):

```bash
python -m pytest tests/test_integration.py -v
```

Integration tests make live Claude API calls and take ~80 seconds.

### 7. Run the server

```bash
uvicorn api.main:app --reload
```

API docs at `http://127.0.0.1:8000/docs`.

---

## Pinned Versions (Known Working)

From `pip freeze` on the development environment:

| Package | Version |
|---|---|
| `anthropic` | 0.104.1 |
| `chromadb` | 1.5.9 |
| `fastapi` | 0.136.3 |
| `huggingface_hub` | 1.16.1 |
| `langchain` | 1.3.1 |
| `langchain-chroma` | 1.1.0 |
| `langchain-community` | 0.4.2 |
| `langchain-core` | 1.4.0 |
| `langchain-huggingface` | 1.2.2 |
| `langchain-text-splitters` | 1.1.2 |
| `langgraph` | 1.2.1 |
| `langgraph-checkpoint` | 4.1.1 |
| `pydantic` | 2.13.4 |
| `pypdf` | 6.12.1 |
| `python-dotenv` | 1.2.2 |
| `sentence-transformers` | 5.5.1 |
| `uvicorn` | 0.47.0 |

---

## Known Issues

**Issue 1 — No `requirements.txt`** *(resolved)*
`requirements.txt` generated from `pip freeze`. 151 packages including all transitive dependencies.

**Issue 2 — `GET /escalations` not implemented** *(resolved)*
`GET /escalations` implemented in `api/main.py`. Queries `logs/audit.db` filtered by `outcome = 'escalate'` and returns the full event dict for each entry. Returns `{"escalations": []}` when no escalations exist or the database does not yet exist.

**Issue 3 — HuggingFace unauthenticated warning**
Every test run prints:
```
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN...
```
Non-fatal. The sentence-transformers model is loaded from local cache after the first download. To suppress: set `HF_TOKEN` in the environment or in `.env`. Not worth fixing in v2.

**Issue 4 — Integration test suite gaps** *(resolved)*
Three tests added to `tests/test_integration.py` (now 12 tests total):
- `test_low_confidence_escalates_with_reason` — vague description, asserts `outcome == "escalate"`, `confidence_score < 0.75`, `escalation_reason` contains `"confidence score"`
- `test_wrong_settlement_date_retrieves_sec_rule` — T+1 description, asserts `"SEC-15c6-1"` in `retrieved_document_ids`
- `test_get_escalations_returns_queue` — asserts `GET /escalations` returns entries with correct schema

**Issue 5 — `logs/` created at runtime** *(won't fix)*
Expected behavior. The logger creates the directory on first write. `logs/` is in `.gitignore`.
