# Huginn Setup Notes
**Last updated:** May 2026
**Status:** Implementation complete. Phase 7 (Feedback Loop) complete.

---

## 1. Pre-Build Reading List

### LangGraph & Agentic Orchestration (~45 min estimated / ran ~65 min actual)

| Item | Link | Time Estimate | Focus Notes |
|------|------|---------------|-------------|
| LangGraph Tutorial (v1.0) | https://agentsindex.ai/blog/langgraph-tutorial | 20–25 min | `StateGraph`, `MessageState`, `create_react_agent`, checkpointing, human-in-the-loop interrupts. Skip anything overlapping the quickstart. Slow down on checkpointing and interrupt sections — these map directly to Huginn's escalation logic. Note: original LangGraph concepts URL (langchain-ai.github.io/langgraph/concepts/) is dead. |
| Human-in-the-Loop Concepts | https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/ | 10 min | Interrupt points and how escalation checkpoints work. Verify this URL resolves before reading. |

**Completed quickstart:** Calculator tool using Anthropic Claude API. Required translating OpenAI examples to Anthropic — swap `ChatOpenAI` for `ChatAnthropic` from `langchain_anthropic`. This translation requirement recurs throughout all LangChain/LangGraph documentation.

---

### RAG Pipeline / Mimir (~40 min estimated / allow 50 min actual)

| Item | Link | Time Estimate | Focus Notes |
|------|------|---------------|-------------|
| LangChain RAG Tutorial | https://python.langchain.com/docs/tutorials/rag/ | 25–30 min | Code alongside selectively. Skip document loading (web scraping) — Huginn uses local files. Focus on: retriever interface, `similarity_search_with_score`, RAG agent pattern. Use Anthropic tab for chat model, HuggingFace tab for embeddings, In-Memory tab for vector store. |
| LangChain FAISS / Vector Store Docs | https://docs.langchain.com/oss/python/integrations/vectorstores/faiss | 10 min | Understand `similarity_search`, saving/loading indexes, converting to retriever. Note: Huginn uses Chroma not FAISS — read for concepts, implement with Chroma. |
| Greg Kamradt Chunking Notebook (Levels 1–3 only) | https://github.com/FullStackRetrieval-com/RetrievalTutorials/blob/main/tutorials/LevelsOfTextSplitting/5_Levels_Of_Text_Splitting.ipynb | 5–10 min | Read on GitHub only — no need to run. Level 3+ requires OpenAI key. Focus on why chunking strategy matters for different document types. Relevant to how Mimir chunks SOP documents. |

**Key embeddings note:** LangChain RAG docs default to `OpenAIEmbeddings`. Use `HuggingFaceEmbeddings` with `sentence-transformers/all-mpnet-base-v2` as drop-in replacement. No API key required. Downloads ~420MB on first use, then caches locally.

---

### FastAPI (~15 min estimated)

| Item | Link | Time Estimate | Focus Notes |
|------|------|---------------|-------------|
| FastAPI First Steps through Request Body | https://fastapi.tiangolo.com/tutorial/first-steps/ | 15 min | Read first four pages: First Steps, Path Parameters, Query Parameters, Request Body. Query Parameters: skim only — low priority for Huginn. Request Body: most important page — Huginn's exception ingestion endpoint uses this pattern. Focus on how `@app.post(...)` maps to a route and how Pydantic `BaseModel` defines incoming JSON schema. |

---

### Financial Domain (~20 min estimated)

| Item | Link | Time Estimate | Focus Notes |
|------|------|---------------|-------------|
| Trade Lifecycle — Clearing & Settlement | https://www.intuition.com/stage-three-and-four-of-the-trade-lifecycle-clearing-and-settlement/ | 10 min | First pass only, no note-taking. Absorb vocabulary: trade, counterparty, clearing, settlement, T+1, failed settlement, breaks report. This is context, not implementation knowledge. |
| Post-Trade Lifecycle & Settlement Failures — Duco | https://du.co/post-trade-lifecycle-management/ | 10 min | Covers real-world settlement failure rates and costs. Gives business context for why Huginn matters as a product. |

**Key vocabulary to absorb:**
- **Trade** — agreement to buy/sell a security at an agreed price
- **Counterparty** — the other party in a trade
- **Clearing** — post-execution confirmation that both sides' details match
- **Settlement** — the actual exchange of cash for securities
- **T+1** — settlement occurs one business day after trade execution (US standard as of May 2024)
- **Failed Settlement / Settlement Exception** — exchange doesn't happen on the expected date
- **Breaks Report** — daily list of all trades that failed to settle; Huginn's effective input
- **DTCC** — central US clearinghouse that processes and guarantees trades

---

## 2. Environment Setup

### Prerequisites
- Python 3.11+
- VS Code
- Git

---

### Step 1 — Create project folder and initialize Git
```bash
mkdir huginn
cd huginn
git init
```

---

### Step 2 — Create and activate virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```

**Note:** Always activate the virtual environment before working. If you see permission errors installing packages outside a venv, this is why — see Known Issues below.

---

### Step 3 — Create `.env` file
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Never hardcode API keys in source files.

---

### Step 4 — Create `.gitignore`
```
venv/
.env
__pycache__/
*.db
.chroma/
logs/
*.jsonl
knowledge_base/processed/
```

Create this before your first commit.

---

### Step 5 — Install dependencies
```bash
pip install anthropic langchain langchain-anthropic langchain-community langchain-huggingface langchain-chroma langchain-text-splitters langgraph fastapi uvicorn python-dotenv sentence-transformers pytest
```

**Dependency notes:**
- `anthropic` is the Anthropic SDK — called directly in `agent/nodes.py` for the Claude API call (Decision 32)
- `langchain-community` provides `TextLoader` for loading SOP `.txt` files during indexing
- `langchain-text-splitters` provides `RecursiveCharacterTextSplitter` used in `scripts/build_index.py` (Decision 30)
- `langchain-chroma` replaces FAISS — Chroma was selected over FAISS for disk persistence and metadata filtering support (Design Decision 12)
- `sentence-transformers` provides HuggingFace embeddings locally with no API key required (Decision 31)
- SQLite is built into Python's standard library — no pip install needed (Design Decision 3)
- `uvicorn` is the ASGI server that runs FastAPI
- `pytest` is the test runner — required for `tests/`

[Updated post-implementation: `anthropic`, `langchain-community`, `langchain-text-splitters`, and `pytest` were missing from the original install command. All four are required by the implementation.]

---

### Step 6 — Freeze requirements immediately
```bash
pip freeze > requirements.txt
```

Run this right after installation. LangChain ships breaking changes regularly — pinned versions protect you.

---

### Step 7 — Create folder structure
```
huginn_v1/
├── mimir/              ← RAG pipeline (Chroma vector store, SOP indexing, retriever)
├── agent/              ← LangGraph state machine (classify, retrieve, reason, decide, log)
├── api/                ← FastAPI layer (3 endpoints: POST /exceptions, GET /exceptions/{job_id}, GET /escalations)
├── knowledge_base/
│   ├── raw/            ← Synthetic SOP documents (.txt, 3 files, one per settlement mismatch sub-type)
│   └── processed/      ← Chroma persistent index (auto-generated by build_index.py, gitignored)
├── logger/             ← Audit logger (writes JSONL + SQLite + escalation queue)
├── models/             ← Pydantic exception schema
├── scripts/            ← build_index.py (one-time SOP indexing)
├── tests/              ← pytest test suite (conftest.py + test_agent, test_mimir, test_api)
├── logs/               ← audit.jsonl, escalation_queue.jsonl (auto-created at runtime, gitignored)
├── .env
└── .gitignore
```

[Updated post-implementation: Root directory is `huginn_v1/`. SOP documents live in `knowledge_base/raw/` (not `data/sops/`). Test fixture JSON is defined inline in `tests/conftest.py` (not in a separate `data/exceptions/` folder). `logger/`, `models/`, and `scripts/` directories added. `requirements.txt` is not currently in the repo — see Known Issue 7.]

---

### Step 8 — Verify setup
```bash
python -c "import langchain; import langgraph; import fastapi; import chromadb; print('All imports successful')"
```

---

## 3. Known Issues

### Issue 1 — Permission denied on pip install
**Error:**
```
ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied: 'C:\Python311\Scripts\jsondiff'
```
**Cause:** Attempting to install packages into the system Python directory without admin rights.

**Fix:** Always use a virtual environment. The venv gives you full write access without requiring admin privileges:
```bash
python -m venv venv
venv\Scripts\activate
pip install <package>
```

---

### Issue 2 — OpenAI/ChatGPT code in LangGraph examples
**Cause:** All LangGraph and LangChain documentation and tutorials default to OpenAI. No OpenAI subscription available.

**Fix:** Swap `ChatOpenAI` for `ChatAnthropic` from `langchain_anthropic`:
```python
# Instead of:
from langchain_openai import ChatOpenAI
model = ChatOpenAI(model="gpt-4o-mini")

# Use:
from langchain_anthropic import ChatAnthropic
model = ChatAnthropic(model="claude-sonnet-4-20250514")
```
This swap is required throughout all LangChain/LangGraph tutorials and will recur during the build.

---

### Issue 3 — LangGraph hello world produces no visible output
**Cause:** `graph.invoke()` returns a dict but doesn't print it automatically outside the Python interactive shell.

**Fix:** Add an explicit print statement:
```python
result = graph.invoke({"messages": [{"role": "user", "content": "hi!"}]})
print(result["messages"][-1].content)
```

---

### Issue 4 — FastAPI dev server shows nothing at `http://0.0.0.0:8000`
**Cause:** `0.0.0.0` is not a browseable address — it means "listening on all interfaces."

**Fix:** Always visit:
```
http://127.0.0.1:8000
```
Or for the interactive docs page:
```
http://127.0.0.1:8000/docs
```

---

### Issue 5 — FastAPI returns `{"detail": "Not Found"}` at root
**Cause:** No route defined for `/` in the FastAPI app, or visiting `http://127.0.0.1:8000/#` (note the `#`).

**Fix:** Remove the `#` from the URL. Navigate to `/docs` to see all defined routes. If no routes exist yet, define at least one `@app.get("/")` endpoint.

---

### Issue 6 — `fastapi dev` command fails with no file specified
**Cause:** Running `fastapi dev` without specifying a Python file.

**Fix:**
```bash
fastapi dev main.py
```
Or use uvicorn directly:
```bash
uvicorn main:app --reload
```

---

### Issue 7 — `requirements.txt` not in repo

**Cause:** Step 6 instructs running `pip freeze > requirements.txt` immediately after installation, but this step was not completed before the first commit. The architecture document lists `requirements.txt` in the folder structure and the README references it, but the file does not currently exist in the repository.

**Fix:** Activate the virtual environment, then run:
```bash
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Add pinned requirements.txt"
```
Do this before beginning v2 so the working dependency set is captured before any packages are updated.

---

### Issue 8 — PyMuPDF not used; listed in original architecture document

**Cause:** The architecture document listed PyMuPDF as a dependency for PDF parsing of SOP documents. During implementation, SOP documents were written as plaintext `.txt` files, eliminating the need for PDF parsing. `langchain_community.document_loaders.TextLoader` handles `.txt` files natively. PyMuPDF was never installed.

**Fix:** Do not install PyMuPDF. The architecture document has been updated (Phase 7 Feedback Loop) to remove it from the library stack. If v2 introduces real FINRA/SEC regulatory documents in PDF format, PyMuPDF or `pypdf` can be added at that time.

---

*Cross-referenced sources: Knowledge Acquisition conversation (reading list), Issue Troubleshooting conversation (known issues), huginn_v1_design_decisions.md (Chroma over FAISS, SQLite logger, folder structure, three FastAPI endpoints). Issues 7–8 added during Phase 7 (Feedback Loop).*
