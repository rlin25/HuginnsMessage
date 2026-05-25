import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pypdf
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from mimir.index import PERSIST_DIR, EMBEDDING_MODEL

RAW_DIR = Path("knowledge_base/raw")
MIN_CHUNK_LENGTH = 200
SECTION_PATTERN = re.compile(r"^\([a-z]\)", re.MULTILINE)

DOCUMENT_MAP = {
    "FINRA-11100.pdf": "FINRA-11100",
    "FINRA-11710.pdf": "FINRA-11710",
    "FINRA-11810.pdf": "FINRA-11810",
    "FINRA-11820.pdf": "FINRA-11820",
    "SEC-15c6-1.pdf":  "SEC-15c6-1",
    "SEC-15c6-2.pdf":  "SEC-15c6-2",
}


def extract_text(path: Path) -> str:
    if path.suffix == ".pdf":
        reader = pypdf.PdfReader(str(path))
        return "".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


def _is_real_section(text: str, match) -> bool:
    """Reject false splits where (x) appears mid-sentence (lowercase continuation)."""
    after = text[match.end():match.end() + 60].lstrip()
    # Strip an optional leading quote or parenthesis, then check for uppercase
    first = after.lstrip('"(').lstrip()
    return bool(first) and first[0].isupper()


def parse_sections(text: str, document_id: str) -> list[dict]:
    boundaries = [m for m in SECTION_PATTERN.finditer(text) if _is_real_section(text, m)]

    if not boundaries:
        return [{"text": text.strip(), "section_id": f"{document_id}-preamble",
                 "document_id": document_id}]

    # Build raw section list with sequential suffix deduplication
    letter_counts: dict[str, int] = {}
    raw: list[tuple[str, str]] = []
    for i, m in enumerate(boundaries):
        end = boundaries[i + 1].start() if i + 1 < len(boundaries) else len(text)
        letter = m.group(0)[1]
        body = text[m.start():end].strip()
        letter_counts[letter] = letter_counts.get(letter, 0) + 1
        section_id = f"{document_id}-{letter}-{letter_counts[letter]}"
        raw.append((section_id, f"{document_id} Section ({letter}):\n{body}"))

    # Preamble: text before first section boundary
    preamble = text[:boundaries[0].start()].strip()
    if preamble and len(preamble) >= MIN_CHUNK_LENGTH:
        seed = [{"text": preamble, "section_id": f"{document_id}-preamble",
                 "document_id": document_id}]
    elif preamble:
        # Too short to stand alone — prepend to first section
        sid, body = raw[0]
        raw[0] = (sid, preamble + "\n" + body)
        seed = []
    else:
        seed = []

    # Apply 200-char minimum: merge short chunks with preceding
    chunks: list[dict] = list(seed)
    for section_id, content in raw:
        if len(content) < MIN_CHUNK_LENGTH and chunks:
            chunks[-1]["text"] += "\n" + content
        else:
            chunks.append({"text": content, "section_id": section_id,
                           "document_id": document_id})

    return chunks


def main() -> None:
    all_docs: list[Document] = []

    for filename, document_id in DOCUMENT_MAP.items():
        path = RAW_DIR / filename
        if not path.exists():
            print(f"WARNING: {path} not found — skipping")
            continue

        text = extract_text(path)
        chunks = parse_sections(text, document_id)

        print(f"\n{document_id}: {len(chunks)} chunks")
        for chunk in chunks:
            print(f"  {chunk['section_id']}: {len(chunk['text'])} chars")
            all_docs.append(Document(
                page_content=chunk["text"],
                metadata={"document_id": chunk["document_id"],
                          "section_id": chunk["section_id"]},
            ))

    # Gate: no duplicate section_ids
    section_ids = [d.metadata["section_id"] for d in all_docs]
    dupes = [s for s in set(section_ids) if section_ids.count(s) > 1]
    if dupes:
        print(f"\nERROR: Duplicate section_ids found: {dupes}")
        sys.exit(1)

    print(f"\nTotal chunks: {len(all_docs)} across {len(DOCUMENT_MAP)} documents")
    print("Building Chroma index (embedding model download on first run)...")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    Chroma.from_documents(all_docs, embeddings, persist_directory=PERSIST_DIR)
    print(f"Index saved to {PERSIST_DIR}/")


if __name__ == "__main__":
    main()
