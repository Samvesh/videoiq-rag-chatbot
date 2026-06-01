import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# ── Lazy cached embedder instances (one per task_type) ────────────────────────
_doc_embedder = None
_query_embedder = None


def _get_api_key() -> str:
    """Read and clean GEMINI_API_KEY from environment."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    for prefix in ("GEMINI_API_KEY=", "gemini_api_key="):
        if api_key.lower().startswith(prefix.lower()):
            api_key = api_key[len(prefix):]
            break
    return api_key.strip().strip('"').strip("'")


def _make_embedder(task_type: str):
    """Create a GoogleGenerativeAIEmbeddings instance.

    Uses langchain_google_genai which is already in requirements.txt and
    correctly handles the Gemini API endpoint + model availability.

    Model: models/embedding-001
      - Available in BOTH v1 and v1beta API endpoints
      - text-embedding-004 is only in v1 and fails on older SDK versions
        that default to v1beta (google-generativeai < 0.7)
    """
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Add it in Render → Environment Variables."
        )

    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key,
        task_type=task_type,
    )


# ── Core embed functions ──────────────────────────────────────────────────────

def embed_texts(texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
    """Embed a list of documents using Gemini embedding-001.

    Args:
        texts: Strings to embed.
        task_type: 'retrieval_document' for indexing (default).

    Returns:
        List of float vectors.
    """
    global _doc_embedder
    if _doc_embedder is None:
        _doc_embedder = _make_embedder("retrieval_document")
    return _doc_embedder.embed_documents(texts)


def embed_query(text: str) -> List[float]:
    """Embed a single search query using Gemini embedding-001.

    Uses task_type='retrieval_query' for better asymmetric retrieval quality.
    """
    global _query_embedder
    if _query_embedder is None:
        _query_embedder = _make_embedder("retrieval_query")
    return _query_embedder.embed_query(text)


# ── ChromaDB / LangChain compatible embedding class ───────────────────────────

class BGEEmbeddings:
    """ChromaDB EmbeddingFunction interface backed by Gemini embedding-001.

    Named BGEEmbeddings for backward compatibility with existing call sites.
    """

    def __call__(self, input: List[str]) -> List[List[float]]:  # noqa: A002
        return embed_texts(input, task_type="retrieval_document")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return embed_texts(texts, task_type="retrieval_document")

    def embed_query(self, text: str) -> List[float]:
        return embed_query(text)
