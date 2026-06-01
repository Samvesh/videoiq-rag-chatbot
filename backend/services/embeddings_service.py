import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# ── Gemini client cache ───────────────────────────────────────────────────────
_genai = None


def _get_genai():
    """Lazily import and configure google.generativeai."""
    global _genai
    if _genai is None:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if api_key.startswith("GEMINI_API_KEY="):
            api_key = api_key[len("GEMINI_API_KEY="):]
        api_key = api_key.strip().strip('"').strip("'")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Please set it in your environment variables."
            )
        genai.configure(api_key=api_key)
        _genai = genai
    return _genai


# ── Core embed function ───────────────────────────────────────────────────────
def embed_texts(texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
    """Embed a list of texts using Gemini text-embedding-004.

    Args:
        texts: List of strings to embed.
        task_type: One of 'retrieval_document' (for indexing) or
                   'retrieval_query' (for querying). Defaults to document.

    Returns:
        List of float vectors, one per input text.
    """
    genai = _get_genai()
    embeddings = []
    for text in texts:
        # Truncate to avoid API limits (Gemini allows ~2048 tokens)
        truncated = text[:8000] if len(text) > 8000 else text
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=truncated,
            task_type=task_type,
        )
        embeddings.append(result["embedding"])
    return embeddings


def embed_query(text: str) -> List[float]:
    """Embed a single query string with the correct task type."""
    return embed_texts([text], task_type="retrieval_query")[0]


# ── ChromaDB-compatible embedding function ────────────────────────────────────
class BGEEmbeddings:
    """Implements ChromaDB's EmbeddingFunction interface using Gemini.

    Named BGEEmbeddings for backward compat — internally uses Gemini API.
    ChromaDB calls: embeddings = embedding_fn(input=["text1", "text2"])
    """

    def __call__(self, input: List[str]) -> List[List[float]]:  # noqa: A002
        return embed_texts(input, task_type="retrieval_document")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return embed_texts(texts, task_type="retrieval_document")

    def embed_query(self, text: str) -> List[float]:
        return embed_query(text)
