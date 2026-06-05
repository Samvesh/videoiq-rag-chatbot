"""
Instagram Reel data extraction — cloud-safe pipeline.

Layer 1 – Apify instagram-reel-scraper (primary; residential proxies, cloud-safe)
Layer 2 – Graceful zeros fallback
"""

import os
import re
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

_APIFY_BASE  = "https://api.apify.com/v2"
_APIFY_ACTOR = "apify~instagram-reel-scraper"


# ── Key helper ────────────────────────────────────────────────────────────────
def _clean_key(env_var: str) -> str:
    key = os.getenv(env_var, "").strip()
    prefix = f"{env_var}="
    if key.upper().startswith(prefix.upper()):
        key = key[len(prefix):]
    return key.strip().strip('"').strip("'")


# ── Shortcode extraction ──────────────────────────────────────────────────────
def _extract_shortcode(url: str) -> str:
    """Extract the shortcode from Instagram Reel / Post URLs."""
    match = re.search(r"instagram\.com/(?:reel|p|tv)/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    return url.rstrip("/").split("/")[-1]


# ── Layer 1: Apify instagram-reel-scraper (primary) ──────────────────────────
async def _fetch_apify_metadata(url: str) -> dict:
    """
    Use Apify's apify/instagram-reel-scraper actor to fetch Reel metadata.
    Cloud-safe: Apify uses residential proxies — no IP blocking on Render.
    """
    token = _clean_key("APIFY_TOKEN")
    if not token:
        print("[Instagram Apify] APIFY_TOKEN not set; skipping Apify layer.")
        return {}

    print(f"[Instagram Apify] Starting actor run for url={url}")
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{_APIFY_BASE}/acts/{_APIFY_ACTOR}/run-sync-get-dataset-items",
                headers={"Authorization": f"Bearer {token}"},
                json={"directUrls": [url], "resultsLimit": 1},
            )

        print(
            f"[Instagram Apify] Response status={resp.status_code} "
            f"body_preview={resp.text[:600]}"
        )

        if resp.status_code not in (200, 201):
            print(f"[Instagram Apify] Non-200 response: {resp.status_code}")
            return {}

        items = resp.json()
        if not items or not isinstance(items, list):
            print("[Instagram Apify] Empty dataset returned.")
            return {}

        item    = items[0]
        owner   = item.get("ownerUser") or {}
        caption = item.get("caption") or item.get("text") or ""

        view_count   = int(item.get("videoPlayCount") or item.get("videoViewCount") or 0)
        like_count   = int(item.get("likesCount") or item.get("likes") or 0)
        comment_count = int(item.get("commentsCount") or item.get("comments") or 0)
        duration     = int(item.get("videoDuration") or 0)
        upload_date  = item.get("timestamp") or item.get("date") or ""
        channel      = (
            item.get("ownerFullName")
            or owner.get("fullName")
            or owner.get("username")
            or "Unknown"
        )
        followers    = int(owner.get("followersCount") or item.get("followersCount") or 0)
        hashtags     = item.get("hashtags") or []
        shortcode    = _extract_shortcode(url)

        result = {
            "title":                  f"Instagram Reel by {channel}",
            "view_count":             view_count,
            "like_count":             like_count,
            "comment_count":          comment_count,
            "duration":               duration,
            "upload_date":            upload_date,
            "channel":                channel,
            "channel_follower_count": followers,
            "tags":                   hashtags,
            "video_id":               shortcode,
            "url":                    url,
            "caption":                caption,
            "apify_failed":           False,
            "source":                 "apify",
        }

        print(
            f"[Instagram Apify] Parsed: channel={channel!r} "
            f"views={view_count} likes={like_count} comments={comment_count} "
            f"followers={followers} duration={duration}s"
        )
        return result

    except Exception as exc:
        print(f"[Instagram Apify] Exception: {exc}")
        return {}


# ── Public entry point ────────────────────────────────────────────────────────
async def get_instagram_data(url: str) -> dict:
    """Fetch Instagram Reel metadata and use caption as text transcript.

    Priority:
      1. Apify instagram-reel-scraper (primary; cloud-safe, no IP blocking)
      2. Graceful zeros fallback

    Transcript strategy (cloud-safe — no audio download required):
      Uses the Reel caption / description as the primary text content.
      This works reliably on any platform without ffmpeg or browser cookies.
    """
    # ── Layer 1: Apify (primary) ──────────────────────────────────────────────
    metadata = await _fetch_apify_metadata(url)

    # ── Full fallback if Apify fails ──────────────────────────────────────────
    if not metadata:
        shortcode = _extract_shortcode(url)
        print(f"[Instagram] All sources failed; using zero-value fallback for {shortcode}")
        metadata = {
            "title":                  "Instagram Reel (Data Unavailable)",
            "view_count":             0,
            "like_count":             0,
            "comment_count":          0,
            "duration":               0,
            "upload_date":            "",
            "channel":                "Unknown Creator",
            "channel_follower_count": 0,
            "tags":                   [],
            "video_id":               shortcode,
            "url":                    url,
            "caption":                "",
            "apify_failed":           True,
            "source":                 "fallback",
        }

    # ── Build transcript from caption ─────────────────────────────────────────
    caption  = metadata.get("caption") or ""
    title    = metadata.get("title") or "Instagram Reel"
    hashtags = metadata.get("tags") or []

    if caption:
        transcript = f"Title: {title}\n\nCaption: {caption}"
    else:
        transcript = f"Title: {title}"

    if hashtags:
        transcript += f"\n\nHashtags: {' '.join(['#' + t for t in hashtags[:20]])}"

    print(f"[Instagram] Transcript built from caption. Length: {len(transcript)}")

    # ── Engagement rate ───────────────────────────────────────────────────────
    views    = metadata.get("view_count", 0)
    likes    = metadata.get("like_count", 0)
    comments = metadata.get("comment_count", 0)
    engagement_rate = round((likes + comments) / views * 100, 2) if views > 0 else 0.0

    metadata["engagement_rate"] = engagement_rate
    metadata["transcript"]      = transcript
    return metadata
