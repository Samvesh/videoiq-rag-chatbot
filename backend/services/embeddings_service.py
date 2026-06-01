"""
Gemini embedding service using the REST API directly via httpx.

Model confirmed from GET /v1beta/models?key=... (ListModels):
  - models/gemini-embedding-001   ← embedContent supported ✓
  - models/gemini-embedding-2     ← embedContent supported ✓
  - models/embedding-001          ← does NOT exist for this key ✗
  - models/text-embedding-004     ← does NOT exist for this key ✗

Using httpx directly instead of the google-generativeai SDK to avoid
API-version mismatches between SDK versions installed on Render.
"""

import os
import httpx
from typing import List
from dotenv import load_dotenv

load_dotenv()

# ── Confirmed model name from ListModels() ────────────────────────────────────
_EMBED_MODEL = "gemini-embedding-001"
_EMBED_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{_EMBED_MODEL}:embedContent"
)
_MAX_CHARS = 6000  # well under the 2048-token limit


# ── API key helper ────────────────────────────────────────────────────────────
def _get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    for prefix in ("GEMINI_API_KEY=", "gemini_api_key="):
        if key.lower().startswith(prefix.lower()):
            key = key[len(prefix):]
            break
    return key.strip().strip('"').strip("'")


# ── Single-text embed via REST ────────────────────────────────────────────────
def _embed_one(text: str, api_key: str) -> List[float]:
    """Call the embedContent REST endpoint for one piece of text."""
    truncated = text[:_MAX_CHARS]
    response = httpx.post(
        _EMBED_URL,
        params={"key": api_key},
        json={"content": {"parts": [{"text": truncated}]}},
        timeout=30.0,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Gemini embed failed [{response.status_code}]: {response.text[:300]}"
        )
    return response.json()["embedding"]["values"]


# ── Public functions ──────────────────────────────────────────────────────────
def embed_texts(texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
    """Embed a list of strings. task_type is accepted for API compat but ignored
    because gemini-embedding-001 does not require it."""
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it in Render → Environment Variables."
        )
    return [_embed_one(t, api_key) for t in texts]


def embed_query(text: str) -> List[float]:
    """Embed a single query string."""
    return embed_texts([text])[0]


# ── ChromaDB / LangChain compatible class ─────────────────────────────────────
class BGEEmbeddings:
    """EmbeddingFunction interface backed by Gemini gemini-embedding-001 REST API.

    Named BGEEmbeddings for backward compatibility with existing call-sites.
    """

    def __call__(self, input: List[str]) -> List[List[float]]:  # noqa: A002
        return embed_texts(input)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return embed_texts(texts)

    def embed_query(self, text: str) -> List[float]:
        return embed_query(text)
