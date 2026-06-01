import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environmental configurations
load_dotenv()

from routes.ingest import router as ingest_router
from routes.chat import router as chat_router

app = FastAPI(
    title="VideoIQ API",
    description="Full-stack RAG analytics backend for YouTube and Instagram Reels",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# allow_origins=["*"] with allow_credentials=False is required for public APIs.
# Using a specific origin list with credentials=True breaks when Vercel creates
# preview URLs (they are different from the production URL) or when CLIENT_URL
# is misconfigured. Since this backend has no session cookies / auth tokens,
# wildcarding is safe and the simplest correct solution.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(ingest_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/api/health")
def health_check():
    """Health check endpoint to verify the API server is live."""
    return {"status": "ok"}
