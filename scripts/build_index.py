# scripts/build_index.py
# Run once from project root: python scripts/build_index.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
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
