import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environmental configurations
load_dotenv()

from routes.ingest import router as ingest_router
from routes.chat import router as chat_router

app = FastAPI(title="VideoIQ API", description="Local full-stack RAG analytics backend for YouTube and Instagram Reels")

# Dynamic CORS Configuration
client_url = os.getenv("CLIENT_URL", "").strip()
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

if client_url and client_url != "*":
    # Split comma-separated URLs (in case user specifies multiple domains), strip whitespaces/quotes
    for url in client_url.split(","):
        cleaned = url.strip().strip('"').strip("'").rstrip('/')
        if cleaned:
            origins.append(cleaned)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Route mounting
app.include_router(ingest_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

@app.get("/api/health")
def health_check():
    """Health check endpoint to verify API server is live."""
    return {"status": "ok"}
