from sentence_transformers import SentenceTransformer
from typing import List

# ── Model cache ───────────────────────────────────────────────────────────────
_model: SentenceTransformer = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("BAAI/bge-small-en")
    return _model


# ── Core embed function (used by both ChromaDB and LangChain) ─────────────────
def embed_texts(texts: List[str]) -> List[List[float]]:
    """Encode texts with BGE-small-en and return normalised float vectors."""
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()


# ── ChromaDB-compatible embedding function ────────────────────────────────────
class BGEEmbeddings:
    """
    Implements ChromaDB's EmbeddingFunction interface:
    https://docs.trychroma.com/guides/embeddings
    ChromaDB calls:  embeddings = embedding_fn(input=["text1", "text2"])
    """

    def __call__(self, input: List[str]) -> List[List[float]]:   # noqa: A002
        return embed_texts(input)

    # ── LangChain compatibility (used if imported as Embeddings) ──────────────
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return embed_texts(texts)

    def embed_query(self, text: str) -> List[float]:
        return embed_texts([text])[0]
