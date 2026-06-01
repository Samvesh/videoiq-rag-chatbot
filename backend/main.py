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


@app.get("/api/debug/models")
async def list_embedding_models():
    """
    TEMPORARY DEBUG ENDPOINT — DO NOT USE IN PRODUCTION.
    Queries the Google Generative AI REST API directly (no SDK) to list every
    model available to the configured GEMINI_API_KEY that supports embedContent.
    Checks both /v1beta/models and /v1/models endpoints.
    """
    import httpx

    raw_key = os.getenv("GEMINI_API_KEY", "").strip()
    for prefix in ("GEMINI_API_KEY=", "gemini_api_key="):
        if raw_key.lower().startswith(prefix.lower()):
            raw_key = raw_key[len(prefix):]
            break
    api_key = raw_key.strip().strip('"').strip("'")

    result = {
        "api_key_prefix": api_key[:12] + "..." if api_key else "(empty)",
        "api_key_length": len(api_key),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for version in ("v1beta", "v1"):
            url = f"https://generativelanguage.googleapis.com/{version}/models"
            try:
                resp = await client.get(url, params={"key": api_key})
                result[version] = {
                    "status": resp.status_code,
                }
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    embed_models = [
                        {
                            "name": m.get("name"),
                            "displayName": m.get("displayName"),
                            "supportedMethods": m.get("supportedGenerationMethods", []),
                        }
                        for m in models
                        if "embedContent" in m.get("supportedGenerationMethods", [])
                    ]
                    result[version]["embedding_models"] = embed_models
                    result[version]["total_models"] = len(models)
                else:
                    result[version]["body"] = resp.text[:500]
            except Exception as exc:
                result[version] = {"error": str(exc)}

    return result
