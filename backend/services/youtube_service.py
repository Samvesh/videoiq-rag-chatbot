"""
YouTube data extraction — cloud-safe pipeline.

Layer 1 – Metadata + Transcript: Apify supreme_coder~youtube-transcript-scraper (primary; cloud-safe)
Layer 2 – Metadata:              YouTube Data API v3 (official, zero bot-detection)
Layer 3 – Transcript:            Gemini video understanding (fallback; accepts YouTube URLs)
Layer 4 – Fallback:              Title + description text from YouTube API
"""

import os
import re
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Constants ─────────────────────────────────────────────────────────────────
_YT_API_BASE        = "https://www.googleapis.com/youtube/v3"
_GEMINI_BASE        = "https://generativelanguage.googleapis.com/v1beta/models"
_GEMINI_VIDEO_MODEL = "gemini-2.0-flash"   # confirmed available; supports YouTube URLs
_APIFY_BASE         = "https://api.apify.com/v2"
_APIFY_ACTOR        = "supreme_coder~youtube-transcript-scraper"


# ── Key helpers ───────────────────────────────────────────────────────────────
def _preview_response_body(resp: httpx.Response, limit: int = 1200) -> str:
    """Return a compact response preview without leaking request secrets."""
    key = resp.request.url.params.get("key", "")
    text = resp.text
    if key:
        text = text.replace(key, "[redacted]")
    return text[:limit]


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


def _duration_str_to_seconds(duration: str) -> int:
    """Convert HH:MM:SS or MM:SS string to total seconds."""
    if not duration:
        return 0
    parts = duration.strip().split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return parts[0]
    except (ValueError, TypeError):
        pass
    return 0


# ── URL normalisation ────────────────────────────────────────────────────────
def _normalize_youtube_url(url: str) -> str:
    """
    Ensure Apify always receives a canonical https://www.youtube.com/watch?v=<id>
    URL regardless of what the user pasted (youtu.be, shorts, embed, etc.).
    """
    video_id = _extract_video_id(url)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url


# ── Layer 1: Apify supreme_coder~youtube-transcript-scraper ───────────────────
async def _fetch_apify_youtube(url: str) -> dict:
    """
    Use Apify's supreme_coder/youtube-transcript-scraper actor to fetch
    metadata + transcript.  Cloud-safe: Apify runs on its own proxies.
    Returns empty dict if APIFY_TOKEN is not set or the call fails.
    """
    token = _clean_key("APIFY_TOKEN")
    if not token:
        print("[YouTube Apify] APIFY_TOKEN not set; skipping Apify layer.")
        return {}

    # Always send the canonical watch URL — short/embed URLs cause invalid-input
    canonical_url = _normalize_youtube_url(url)
    if canonical_url != url:
        print(f"[YouTube Apify] Normalised URL: {url!r} → {canonical_url!r}")

    run_input = {
        "urls": [canonical_url],
    }

    print(f"[YouTube Apify] Starting actor run for url={url}")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{_APIFY_BASE}/acts/{_APIFY_ACTOR}/run-sync-get-dataset-items",
                headers={"Authorization": f"Bearer {token}"},
                json=run_input,
            )

        print(
            f"[YouTube Apify] Response status={resp.status_code} "
            f"body_preview={resp.text[:600]}"
        )

        if resp.status_code not in (200, 201):
            print(f"[YouTube Apify] Non-200 response: {resp.status_code}")
            return {}

        items = resp.json()
        if not items or not isinstance(items, list):
            print("[YouTube Apify] Empty dataset returned.")
            return {}

        item = items[0]

        # ── Extract transcript ────────────────────────────────────────────────
        # supreme_coder~youtube-transcript-scraper returns transcript as plain text
        transcript = ""
        raw_transcript = item.get("transcript") or item.get("subtitles") or ""
        if isinstance(raw_transcript, list):
            # Segment list: [{"text": "...", "start": ..., "duration": ...}]
            transcript = " ".join(
                seg.get("text", "") for seg in raw_transcript if seg.get("text")
            ).strip()
        elif isinstance(raw_transcript, str):
            transcript = raw_transcript.strip()

        # ── Extract metrics ───────────────────────────────────────────────────
        view_count      = int(item.get("viewCount") or item.get("views") or 0)
        like_count      = int(item.get("likes") or item.get("likeCount") or 0)
        comment_count   = int(item.get("commentsCount") or item.get("commentCount") or 0)
        duration_raw    = item.get("duration") or ""
        duration_secs   = _duration_str_to_seconds(str(duration_raw)) if isinstance(duration_raw, str) else int(duration_raw or 0)
        channel_name    = item.get("channelName") or item.get("author") or item.get("channel") or "Unknown Channel"
        subscribers_raw = item.get("channelSubscriberCount") or item.get("subscriberCount") or item.get("numberOfSubscribers") or 0
        if isinstance(subscribers_raw, str) and subscribers_raw:
            # Handle "1.2M", "450K", "1,234,567" formats
            s = subscribers_raw.replace(",", "").strip()
            if s.endswith("M"):
                subscribers = int(float(s[:-1]) * 1_000_000)
            elif s.endswith("K"):
                subscribers = int(float(s[:-1]) * 1_000)
            else:
                subscribers = int(s) if s.isdigit() else 0
        else:
            subscribers = int(subscribers_raw or 0)
        title       = item.get("title") or "YouTube Video"
        description = item.get("description") or item.get("text") or ""
        upload_date = (item.get("date") or item.get("uploadDate") or item.get("publishedAt") or "")[:10].replace("-", "")
        tags        = item.get("tags") or []
        video_id    = _extract_video_id(url) or item.get("id") or item.get("videoId") or ""

        result = {
            "title":                    title,
            "description":              description,
            "view_count":               view_count,
            "like_count":               like_count,
            "comment_count":            comment_count,
            "duration":                 duration_secs,
            "upload_date":              upload_date,
            "channel":                  channel_name,
            "channel_subscriber_count": subscribers,
            "tags":                     tags,
            "video_id":                 video_id,
            "url":                      url,
            "transcript":               transcript,
            "source":                   "apify",
        }

        print(
            f"[YouTube Apify] Parsed: title={title!r} channel={channel_name!r} "
            f"views={view_count} likes={like_count} comments={comment_count} "
            f"duration={duration_secs}s transcript_len={len(transcript)}"
        )
        return result

    except Exception as exc:
        print(f"[YouTube Apify] Exception: {exc}")
        return {}


# ── Layer 2: Metadata via YouTube Data API v3 ─────────────────────────────────
async def _fetch_youtube_api_metadata(video_id: str) -> dict:
    """
    Call the official YouTube Data API v3.
    Returns empty dict if YOUTUBE_API_KEY is not set or the call fails.
    """
    api_key = _clean_key("YOUTUBE_API_KEY")
    if not api_key:
        print("[YouTube API] YOUTUBE_API_KEY not set; YouTube Data API v3 metadata call skipped.")
        return {}

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            print(f"[YouTube API] Fetching videos metadata for video_id={video_id}")
            resp = await client.get(
                f"{_YT_API_BASE}/videos",
                params={
                    "id": video_id,
                    "part": "snippet,statistics,contentDetails",
                    "key": api_key,
                },
            )
            print(
                f"[YouTube API] Raw videos response status={resp.status_code} "
                f"body={_preview_response_body(resp)}"
            )
            if resp.status_code != 200:
                return {}

            items = resp.json().get("items", [])
            if not items:
                print(f"[YouTube API] No video found for ID: {video_id}")
                return {}

            item      = items[0]
            snippet   = item.get("snippet", {})
            stats     = item.get("statistics", {})
            content   = item.get("contentDetails", {})

            channel_id  = snippet.get("channelId", "")
            subscribers = 0
            if channel_id:
                ch_resp = await client.get(
                    f"{_YT_API_BASE}/channels",
                    params={"id": channel_id, "part": "statistics", "key": api_key},
                )
                print(
                    f"[YouTube API] Raw channels response status={ch_resp.status_code} "
                    f"channel_id={channel_id} body={_preview_response_body(ch_resp)}"
                )
                if ch_resp.status_code == 200:
                    ch_items = ch_resp.json().get("items", [])
                    if ch_items:
                        subscribers = int(
                            ch_items[0].get("statistics", {}).get("subscriberCount", 0)
                        )
                    else:
                        print(f"[YouTube API] No channel statistics found for channel_id={channel_id}")
                else:
                    print(f"[YouTube API] Channel statistics fetch failed for channel_id={channel_id}")

            metadata = {
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
            print(
                "[YouTube API] Parsed metadata "
                f"source={metadata['source']} title={metadata['title']!r} "
                f"channel={metadata['channel']!r} views={metadata['view_count']} "
                f"likes={metadata['like_count']} comments={metadata['comment_count']} "
                f"duration={metadata['duration']}"
            )
            return metadata

        except Exception as exc:
            print(f"[YouTube API] Exception: {exc}")
            return {}


# ── Layer 3: Transcript via Gemini video understanding ────────────────────────
async def _fetch_transcript_gemini(video_id: str, url: str) -> str:
    """
    Gemini 2.0 Flash accepts YouTube URLs directly in fileData.fileUri.
    No cookies, no proxies — works from any IP including cloud providers.
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

    Layer 1 – Apify youtube-scraper      (primary; residential proxies, full data)
    Layer 2 – YouTube Data API v3        (metadata fallback; official API)
    Layer 3 – Gemini video understanding (transcript fallback; always cloud-safe)
    Layer 4 – Title + description text   (guaranteed final fallback)
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return {"error": "Unable to parse YouTube video ID from URL"}

    # ── Layer 1: Apify (primary) ──────────────────────────────────────────────
    apify_data = await _fetch_apify_youtube(url)

    if apify_data:
        # Apify returned both metadata and (possibly) transcript
        meta       = apify_data
        transcript = apify_data.get("transcript", "")
    else:
        # ── Layer 2: YouTube Data API v3 (metadata fallback) ──────────────────
        meta       = await _fetch_youtube_api_metadata(video_id)
        transcript = ""

        if not meta:
            # Minimal stub when no metadata source is available
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
            print(
                "[YouTube API] Metadata fallback stub created "
                f"for video_id={video_id}; channel='Unknown Channel', metrics=0, duration=0."
            )

    # ── Layer 3: Gemini transcript fallback ───────────────────────────────────
    if not transcript:
        print(f"[YouTube Service] No transcript from Apify; falling back to Gemini for {video_id}")
        transcript = await _fetch_transcript_gemini(video_id, url)

    # ── Layer 4: Title + description guaranteed fallback ─────────────────────
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
