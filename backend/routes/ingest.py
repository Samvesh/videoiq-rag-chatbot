from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio

from services.youtube_service import get_youtube_data
from services.instagram_service import get_instagram_data
from services.rag_service import upsert_documents

router = APIRouter()


class IngestRequest(BaseModel):
    youtube_url: Optional[str] = None
    instagram_url: Optional[str] = None


@router.post("/ingest", summary="Ingest YouTube/Instagram URLs and store chunks in Chroma")
async def ingest(request: IngestRequest):
    try:
        return await _ingest_impl(request)
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[Ingest] Unhandled error: {exc}")
        raise HTTPException(status_code=500, detail=f"Server error: {exc}")


async def _ingest_impl(request: IngestRequest):
    if not request.youtube_url and not request.instagram_url:
        raise HTTPException(status_code=400, detail="At least one URL must be provided.")

    coroutines = []
    task_keys = []
    if request.youtube_url:
        coroutines.append(get_youtube_data(str(request.youtube_url)))
        task_keys.append("youtube")
    if request.instagram_url:
        coroutines.append(get_instagram_data(str(request.instagram_url)))
        task_keys.append("instagram")

    # Gather all concurrently; catch individual exceptions without crashing
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    docs_to_upsert = []
    errors = []
    video_a_meta = None
    video_b_meta = None

    for i, res in enumerate(results):
        key = task_keys[i]
        if isinstance(res, Exception):
            errors.append(f"{key} error: {res}")
            print(f"[Ingest] Service error for {key}: {res}")
            continue
        if not isinstance(res, dict):
            continue

        source_id = res.get("video_id") or res.get("title") or "unknown"
        content = res.get("transcript") or ""
        platform = "youtube" if key == "youtube" else "instagram"

        if key == "youtube":
            print(f"[Ingest] get_youtube_data() returned transcript. Length: {len(content)}, Preview: {content[:200]}")

        # Build flat metadata — ChromaDB only accepts str/int/float/bool values
        metadata = {
            "title":           str(res.get("title") or ""),
            "url":             str(res.get("url") or ""),
            "view_count":      int(res.get("view_count") or 0),
            "like_count":      int(res.get("like_count") or 0),
            "comment_count":   int(res.get("comment_count") or 0),
            "duration":        int(res.get("duration") or 0),
            "channel":         str(res.get("channel") or ""),
            "engagement_rate": float(res.get("engagement_rate") or 0.0),
            "source_platform": platform,
            "source_id":       str(source_id),
        }

        # Keep richer dictionary for frontend response containing follower counts and upload dates
        ui_metadata = {
            "title":                  str(res.get("title") or ""),
            "url":                    str(res.get("url") or ""),
            "view_count":             int(res.get("view_count") or 0),
            "like_count":             int(res.get("like_count") or 0),
            "comment_count":          int(res.get("comment_count") or 0),
            "duration":               int(res.get("duration") or 0),
            "channel":                str(res.get("channel") or ""),
            "engagement_rate":        float(res.get("engagement_rate") or 0.0),
            "source_platform":        platform,
            "source_id":              str(source_id),
            "video_id":               str(source_id),
            "upload_date":            str(res.get("upload_date") or ""),
            "channel_follower_count": int(res.get("channel_follower_count") or res.get("channel_subscriber_count") or 0),
        }

        if key == "youtube":
            video_a_meta = ui_metadata
        else:
            video_b_meta = ui_metadata

        docs_to_upsert.append({
            "source_id": str(source_id),
            "content":   content,
            "metadata":  metadata,
        })

    if docs_to_upsert:
        upsert_documents(docs_to_upsert)
        return {
            "status": "success",
            "ingested": len(docs_to_upsert),
            "errors": errors,
            "videoA": video_a_meta,
            "videoB": video_b_meta,
        }

    # If nothing ingested, surface the errors
    detail = "; ".join(errors) if errors else "No valid content could be ingested."
    raise HTTPException(status_code=400, detail=detail)
