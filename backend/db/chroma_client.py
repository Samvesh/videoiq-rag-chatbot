import os
from dotenv import load_dotenv

load_dotenv()

class LazyChromaClient:
    def __init__(self):
        self._real_client = None

    def _get_client(self):
        if self._real_client is None:
            import chromadb
            chroma_path = os.getenv("CHROMA_PATH", "").strip()
            if chroma_path.startswith("CHROMA_PATH="):
                chroma_path = chroma_path[len("CHROMA_PATH="):]
            chroma_path = chroma_path.strip().strip('"').strip("'")
            if not chroma_path:
                chroma_path = "./chroma_store"
            self._real_client = chromadb.PersistentClient(path=chroma_path)
        return self._real_client

    def __getattr__(self, name):
        return getattr(self._get_client(), name)

client = LazyChromaClient()

def get_collection():
    """Fetches the existing collection or creates a new one if it doesn't exist."""
    return client.get_or_create_collection(name="videoiq_chunks")

def reset_collection():
    """Deletes the current collection and recreates it empty."""
    try:
        client.delete_collection(name="videoiq_chunks")
    except Exception:
        # Collection might not exist yet; ignore error and proceed to create
        pass
    return client.get_or_create_collection(name="videoiq_chunks")
