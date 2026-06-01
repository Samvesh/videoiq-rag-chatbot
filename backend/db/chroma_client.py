import os
import chromadb
from dotenv import load_dotenv

load_dotenv()

# Determine database persistence directory
chroma_path = os.getenv("CHROMA_PATH", "./chroma_store")

# Initialize persistent ChromaDB client
client = chromadb.PersistentClient(path=chroma_path)

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
