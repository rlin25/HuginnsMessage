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
