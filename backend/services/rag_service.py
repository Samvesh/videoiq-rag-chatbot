import os
from typing import List, Dict, Any, Generator

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from services.embeddings_service import BGEEmbeddings, embed_texts
from db.chroma_client import client as chroma_client

from dotenv import load_dotenv
load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────
raw_groq_key = os.getenv("GROQ_API_KEY", "")
if raw_groq_key.startswith("GROQ_API_KEY="):
    raw_groq_key = raw_groq_key[len("GROQ_API_KEY="):]
elif raw_groq_key.startswith("groq_api_key="):
    raw_groq_key = raw_groq_key[len("groq_api_key="):]
raw_groq_key = raw_groq_key.strip().strip('"').strip("'")

_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=raw_groq_key if raw_groq_key else None,
)

# ── Prompt ────────────────────────────────────────────────────────────────────
_SYSTEM = (
    "You are VideoIQ, a friendly and insightful video performance analyst. "
    "You help creators understand why their videos perform the way they do. "
    "Answer questions in a warm, conversational tone — like a knowledgeable friend explaining things. "
    "Use the provided context to answer, but NEVER expose raw IDs, source_ids, or technical database identifiers to the user. "
    "Instead, refer to videos by their title or as 'Video A (YouTube)' and 'Video B (Instagram)'. "
    "When comparing metrics, use natural language like 'about 3.4 million views' instead of '3400000'. "
    "Format numbers in a human-friendly way (e.g., '224K likes', '1.3M views', '7% engagement rate'). "
    "Use short paragraphs and bullet points when comparing multiple aspects. "
    "Keep your answer helpful, clear, and easy to understand — avoid sounding robotic or overly technical."
)

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])

# ── Collection helper ─────────────────────────────────────────────────────────
_COLLECTION_NAME = "videoiq_chunks"


def _get_collection():
    """Returns the ChromaDB collection, creating it if needed."""
    return chroma_client.get_or_create_collection(name=_COLLECTION_NAME)


# ── Retrieval ─────────────────────────────────────────────────────────────────
def _retrieve(query: str, k: int = 6) -> List[Document]:
    collection = _get_collection()
    try:
        count = collection.count()
    except Exception:
        count = 0

    if count == 0:
        return []

    # Get all unique source_ids present in the DB
    all_data = collection.get(include=["metadatas"])
    metadatas = all_data.get("metadatas") or []
    
    unique_sources = set()
    for meta in metadatas:
        if meta and "source_id" in meta:
            unique_sources.add(meta["source_id"])
            
    # Embed query with BGE
    query_embedding = embed_texts([query])[0]
    
    docs = []
    if unique_sources:
        # Determine number of chunks to fetch per source to keep total around k
        k_per_source = max(1, k // len(unique_sources))
        
        for source_id in sorted(unique_sources):
            # Query ChromaDB specifically for this video/source
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=k_per_source,
                where={"source_id": source_id},
                include=["documents", "metadatas"],
            )
            
            if results and results.get("documents") and results["documents"][0]:
                for text, meta in zip(results["documents"][0], results["metadatas"][0]):
                    docs.append(Document(page_content=text, metadata=meta))
    else:
        # Fallback to standard query
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, count),
            include=["documents", "metadatas"],
        )
        for text, meta in zip(results["documents"][0], results["metadatas"][0]):
            docs.append(Document(page_content=text, metadata=meta))
            
    return docs


def _format_number(n: int) -> str:
    """Format a number in human-friendly style."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1_000:.1f}K".replace(".0K", "K")
    return str(n)


def _format_context(docs: List[Document]) -> str:
    if not docs:
        return "No video data has been ingested yet."
    parts = []
    for doc in docs:
        platform = doc.metadata.get("source_platform", "")
        title = doc.metadata.get("title", "Untitled Video")
        views = int(doc.metadata.get("view_count", 0))
        likes = int(doc.metadata.get("like_count", 0))
        comments = int(doc.metadata.get("comment_count", 0))
        eng = doc.metadata.get("engagement_rate", 0)
        label = "Video A (YouTube)" if platform == "youtube" else "Video B (Instagram)"

        header = (
            f"{label}: \"{title}\"\n"
            f"  Views: {_format_number(views)} | Likes: {_format_number(likes)} | "
            f"Comments: {_format_number(comments)} | Engagement Rate: {eng}%"
        )
        parts.append(f"{header}\n  Transcript excerpt: {doc.page_content[:800]}")
    return "\n\n---\n\n".join(parts)


# ── Public API ────────────────────────────────────────────────────────────────
def answer_question(query: str, session_id: str = "default") -> Generator[str, None, None]:
    """Retrieve context, build prompt, stream LLM tokens."""
    docs = _retrieve(query)
    context = _format_context(docs)

    # Build input dict and stream through prompt → LLM
    chain = _PROMPT | _llm
    for chunk in chain.stream({"context": context, "question": query}):
        token = getattr(chunk, "content", "")
        if token:
            yield token


def answer_question_generator(query: str, session_id: str = "default") -> Generator[dict, None, None]:
    """Retrieve context, build prompt, stream LLM tokens as dictionaries with sources."""
    docs = _retrieve(query)
    context = _format_context(docs)

    sources = []
    for idx, doc in enumerate(docs):
        platform = doc.metadata.get("source_platform", "")
        video_id = "A" if platform == "youtube" else "B"
        sources.append({
            "video_id": video_id,
            "chunk_index": idx + 1,
            "text_preview": doc.page_content[:200]
        })

    # Build input dict and stream through prompt → LLM
    chain = _PROMPT | _llm
    first = True
    for chunk in chain.stream({"context": context, "question": query}):
        token = getattr(chunk, "content", "")
        if token:
            payload = {"token": token}
            if first:
                payload["sources"] = sources
                first = False
            yield payload



def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """Splits a string into overlapping chunks of approximately chunk_size characters,
    trying not to split words.
    """
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
        
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
            
        space_idx = text.rfind(" ", start, end)
        if space_idx != -1 and space_idx > start + (chunk_size // 2):
            end = space_idx
            
        chunks.append(text[start:end].strip())
        start = end - chunk_overlap
        
        if start >= end:
            start = end
            
    return [c for c in chunks if c]


def upsert_documents(docs: List[Dict[str, Any]]) -> None:
    """Insert or overwrite chunked documents in ChromaDB using BGE embeddings."""
    if not docs:
        return

    collection = _get_collection()
    
    chunked_ids = []
    chunked_texts = []
    chunked_metadatas = []
    
    for doc in docs:
        source_id = str(doc["source_id"])
        content = doc.get("content") or ""
        metadata = doc.get("metadata") or {}
        
        platform = metadata.get("source_platform", "")
        is_video_a = (platform == "youtube")
        
        # Log/print what text is being passed for video_id 'A'
        if is_video_a:
            print(f"[RAG] upsert_documents - Video A (YouTube) transcript content to upsert. Length: {len(content)}, Preview: {content[:200]}")
            
        # Delete existing chunks for this source_id first to avoid orphaned chunks
        try:
            collection.delete(where={"source_id": source_id})
            print(f"[RAG] Deleted existing chunks for source_id: {source_id}")
        except Exception as e:
            print(f"[RAG] Warning: Failed to delete old chunks for {source_id}: {e}")
            
        chunks = chunk_text(content)
        if not chunks:
            chunks = [""]
            
        for i, chunk in enumerate(chunks):
            chunked_ids.append(f"{source_id}_chunk_{i}")
            chunked_texts.append(chunk)
            
            chunk_meta = metadata.copy()
            chunk_meta["chunk_index"] = i
            chunked_metadatas.append(chunk_meta)
            
            if is_video_a:
                print(f"[RAG] Video A chunk {i} length: {len(chunk)}, Preview: {chunk[:100]}")

    if not chunked_texts:
        return

    # Pre-compute embeddings for all chunks
    embeddings = embed_texts(chunked_texts)

    # Upsert chunks into ChromaDB
    collection.upsert(
        ids=chunked_ids,
        documents=chunked_texts,
        embeddings=embeddings,
        metadatas=chunked_metadatas,
    )
    print(f"[RAG] Upserted {len(chunked_ids)} chunk(s) into '{_COLLECTION_NAME}'.")
