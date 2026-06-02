"""
YouTube data extraction — cloud-safe pipeline.

Layer 1 – Metadata:   YouTube Data API v3 (official, zero bot-detection)
Layer 2 – Transcript: youtube-transcript-api (fast; works for captioned videos)
Layer 3 – Transcript: Gemini video understanding (fallback; accepts YouTube URLs directly)
Layer 4 – Fallback:   Title + description text from YouTube API
"""

import os
import re
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Constants ─────────────────────────────────────────────────────────────────
_YT_API_BASE   = "https://www.googleapis.com/youtube/v3"
_GEMINI_BASE   = "https://generativelanguage.googleapis.com/v1beta/models"
_GEMINI_VIDEO_MODEL = "gemini-2.0-flash"   # confirmed available; supports YouTube URLs


# ── Key helpers ───────────────────────────────────────────────────────────────
def _clean_key(env_var: str) -> str:
    key = os.getenv(env_var, "").strip()
    prefix = f"{env_var}="
    if key.upper().startswith(prefix.upper()):
        key = key[len(prefix):]
    return key.strip().strip('"').strip("'")


# ── Video ID extraction ───────────────────────────────────────────────────────
def _extract_video_id(url: str) -> str:
    """Extract 11-char video ID from any YouTube URL format."""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else ""


# ── ISO 8601 duration → seconds ───────────────────────────────────────────────
def _parse_iso_duration(iso: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)


# ── Layer 1: Metadata via YouTube Data API v3 ─────────────────────────────────
async def _fetch_youtube_api_metadata(video_id: str) -> dict:
    """
    Call the official YouTube Data API v3.
    Returns empty dict if YOUTUBE_API_KEY is not set or the call fails.
    Get a free key at: https://console.cloud.google.com → Enable 'YouTube Data API v3'
    """
    api_key = _clean_key("YOUTUBE_API_KEY")
    if not api_key:
        print("[YouTube Service] YOUTUBE_API_KEY not set — skipping YouTube API metadata.")
        return {}

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            # Video snippet + statistics + contentDetails
            resp = await client.get(
                f"{_YT_API_BASE}/videos",
                params={
                    "id": video_id,
                    "part": "snippet,statistics,contentDetails",
                    "key": api_key,
                },
            )
            if resp.status_code != 200:
                print(f"[YouTube API] videos endpoint → {resp.status_code}: {resp.text[:200]}")
                return {}

            items = resp.json().get("items", [])
            if not items:
                print(f"[YouTube API] No video found for ID: {video_id}")
                return {}

            item      = items[0]
            snippet   = item.get("snippet", {})
            stats     = item.get("statistics", {})
            content   = item.get("contentDetails", {})

            # Optional: fetch subscriber count
            channel_id  = snippet.get("channelId", "")
            subscribers = 0
            if channel_id:
                ch_resp = await client.get(
                    f"{_YT_API_BASE}/channels",
                    params={"id": channel_id, "part": "statistics", "key": api_key},
                )
                if ch_resp.status_code == 200:
                    ch_items = ch_resp.json().get("items", [])
                    if ch_items:
                        subscribers = int(
                            ch_items[0].get("statistics", {}).get("subscriberCount", 0)
                        )

            return {
                "title":                    snippet.get("title") or "YouTube Video",
                "description":              snippet.get("description") or "",
                "view_count":               int(stats.get("viewCount") or 0),
                "like_count":               int(stats.get("likeCount") or 0),
                "comment_count":            int(stats.get("commentCount") or 0),
                "duration":                 _parse_iso_duration(content.get("duration", "")),
                "upload_date":              (snippet.get("publishedAt") or "")[:10].replace("-", ""),
                "channel":                  snippet.get("channelTitle") or "Unknown Channel",
                "channel_subscriber_count": subscribers,
                "tags":                     snippet.get("tags") or [],
                "video_id":                 video_id,
                "url":                      f"https://www.youtube.com/watch?v={video_id}",
                "source":                   "youtube_api_v3",
            }

        except Exception as exc:
            print(f"[YouTube API] Exception: {exc}")
            return {}


# ── Layer 2: Transcript via youtube-transcript-api ────────────────────────────
def _fetch_transcript_api(video_id: str) -> str:
    """
    Fast path — works for videos with manually uploaded captions even on cloud IPs.
    Returns empty string if blocked or unavailable.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        ytt = YouTubeTranscriptApi()
        snippets = ytt.fetch(video_id, languages=["en"])
        text = " ".join(s.text for s in snippets)
        print(f"[YouTube Service] Transcript via youtube-transcript-api: {len(text)} chars")
        return text
    except Exception as exc:
        print(f"[YouTube Service] youtube-transcript-api failed: {exc}")
        return ""


# ── Layer 3: Transcript via Gemini video understanding ────────────────────────
async def _fetch_transcript_gemini(video_id: str, url: str) -> str:
    """
    Gemini 2.0 Flash accepts YouTube URLs directly in fileData.fileUri.
    No cookies, no proxies — works from any IP including cloud providers.
    Uses the same GEMINI_API_KEY already configured for embeddings.
    """
    api_key = _clean_key("GEMINI_API_KEY")
    if not api_key:
        return ""

    payload = {
        "contents": [{
            "parts": [
                {
                    "fileData": {
                        "fileUri": url,
                        "mimeType": "video/*",
                    }
                },
                {
                    "text": (
                        "Please provide a comprehensive transcript or detailed summary of this YouTube video. "
                        "Cover all main topics, key points, and important details discussed. "
                        "Be thorough so it can be used for analysis."
                    )
                },
            ]
        }],
        "generationConfig": {
            "maxOutputTokens": 2048,
            "temperature": 0.1,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{_GEMINI_BASE}/{_GEMINI_VIDEO_MODEL}:generateContent",
                params={"key": api_key},
                json=payload,
            )

        if resp.status_code == 200:
            candidates = resp.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text  = " ".join(p.get("text", "") for p in parts).strip()
                print(f"[YouTube Service] Transcript via Gemini: {len(text)} chars")
                return text
        else:
            print(f"[YouTube Service] Gemini video failed: {resp.status_code} {resp.text[:300]}")

    except Exception as exc:
        print(f"[YouTube Service] Gemini video exception: {exc}")

    return ""


# ── Public entry point ────────────────────────────────────────────────────────
async def get_youtube_data(url: str) -> dict:
    """
    Fetch YouTube video metadata and transcript using a cloud-safe pipeline.

    Metadata:   YouTube Data API v3 (official; no bot detection)
    Transcript: youtube-transcript-api → Gemini video → title+description fallback
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return {"error": "Unable to parse YouTube video ID from URL"}

    # ── Metadata (Layer 1) ────────────────────────────────────────────────────
    meta = await _fetch_youtube_api_metadata(video_id)

    if not meta:
        # Minimal stub when YOUTUBE_API_KEY is absent
        meta = {
            "title":                    "YouTube Video",
            "description":              "",
            "view_count":               0,
            "like_count":               0,
            "comment_count":            0,
            "duration":                 0,
            "upload_date":              "",
            "channel":                  "Unknown Channel",
            "channel_subscriber_count": 0,
            "tags":                     [],
            "video_id":                 video_id,
            "url":                      url,
            "source":                   "fallback",
        }

    # ── Transcript (Layers 2 → 3 → 4) ────────────────────────────────────────
    loop = asyncio.get_event_loop()

    # Layer 2: youtube-transcript-api (fast, sometimes works on cloud)
    transcript = await loop.run_in_executor(None, lambda: _fetch_transcript_api(video_id))

    # Layer 3: Gemini video understanding (always cloud-safe)
    if not transcript:
        print(f"[YouTube Service] Falling back to Gemini video understanding for {video_id}")
        transcript = await _fetch_transcript_gemini(video_id, url)

    # Layer 4: Title + description (guaranteed fallback)
    if not transcript:
        title       = meta.get("title") or "YouTube Video"
        description = meta.get("description") or ""
        transcript  = f"Title: {title}\n\nDescription: {description}"
        print(f"[YouTube Service] Using title+description fallback. Length: {len(transcript)}")

    # ── Engagement rate ───────────────────────────────────────────────────────
    views    = meta.get("view_count", 0)
    likes    = meta.get("like_count", 0)
    comments = meta.get("comment_count", 0)
    engagement_rate = round((likes + comments) / views * 100, 2) if views > 0 else 0.0

    meta.update({
        "transcript":      transcript,
        "engagement_rate": engagement_rate,
        "video_id":        video_id,
    })
    return meta
