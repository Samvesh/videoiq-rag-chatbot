import os
import re
import asyncio
import httpx
import instaloader
from dotenv import load_dotenv

load_dotenv()

# ── Instaloader context (reused across calls) ─────────────────────────────────
_loader = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    quiet=True,
)


# ── Shortcode extraction ──────────────────────────────────────────────────────
def _extract_shortcode(url: str) -> str:
    """Extract the shortcode from Instagram Reel / Post URLs."""
    match = re.search(r"instagram\.com/(?:reel|p|tv)/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    return url.rstrip("/").split("/")[-1]


# ── Metadata via instaloader (works for public Reels without login) ───────────
def _fetch_instaloader_metadata(url: str) -> dict:
    shortcode = _extract_shortcode(url)
    try:
        post = instaloader.Post.from_shortcode(_loader.context, shortcode)

        owner = post.owner_profile
        followers = 0
        try:
            followers = owner.followers
        except Exception:
            pass

        caption = post.caption or ""
        hashtags = re.findall(r"#(\w+)", caption)

        return {
            "title":                   f"Instagram Reel by @{post.owner_username}",
            "view_count":              int(post.video_view_count or 0),
            "like_count":              int(post.likes or 0),
            "comment_count":           int(post.comments or 0),
            "duration":                0,
            "upload_date":             post.date.strftime("%Y%m%d") if post.date else "",
            "channel":                 post.owner_username,
            "channel_follower_count":  int(followers),
            "tags":                    hashtags,
            "video_id":                shortcode,
            "url":                     url,
            "caption":                 caption,
            "apify_failed":            False,
            "source":                  "instaloader",
        }
    except Exception as e:
        print(f"[Instagram] instaloader failed for {url}: {e}")
        return {}


# ── Optional: Apify for richer metadata ──────────────────────────────────────
async def _fetch_apify_metadata(url: str) -> dict:
    token = os.getenv("APIFY_TOKEN", "").strip()
    if token.startswith("APIFY_TOKEN="):
        token = token[len("APIFY_TOKEN="):]
    token = token.strip().strip('"').strip("'")
    if not token:
        return {}
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                "https://api.apify.com/v2/acts/apify~instagram-reel-scraper/run-sync-get-dataset-items",
                headers={"Authorization": f"Bearer {token}"},
                json={"directUrls": [url], "resultsLimit": 1},
            )
        if resp.status_code in (200, 201):
            items = resp.json()
            if items:
                item = items[0]
                owner = item.get("ownerUser") or {}
                caption = item.get("caption") or item.get("text") or ""
                return {
                    "title":                   f"Instagram Reel by {item.get('ownerFullName') or owner.get('username') or 'Creator'}",
                    "view_count":              int(item.get("videoPlayCount") or 0),
                    "like_count":              int(item.get("likesCount") or 0),
                    "comment_count":           int(item.get("commentsCount") or 0),
                    "duration":                int(item.get("videoDuration") or 0),
                    "upload_date":             item.get("timestamp") or "",
                    "channel":                 item.get("ownerFullName") or owner.get("username") or "Unknown",
                    "channel_follower_count":  int(owner.get("followersCount") or 0),
                    "tags":                    item.get("hashtags") or [],
                    "video_id":                _extract_shortcode(url),
                    "url":                     url,
                    "caption":                 caption,
                    "apify_failed":            False,
                    "source":                  "apify",
                }
    except Exception as e:
        print(f"[Instagram] Apify failed: {e}")
    return {}


# ── Public entry point ────────────────────────────────────────────────────────
async def get_instagram_data(url: str) -> dict:
    """Fetch Instagram Reel metadata and use caption as text transcript.

    Priority for metadata:
      1. Apify (if APIFY_TOKEN is set) — richest data including caption
      2. instaloader — works for public Reels without login
      3. Graceful zeros fallback

    Transcript strategy (cloud-safe — no audio download required):
      Uses the Reel caption / description as the primary text content.
      This works reliably on any platform without ffmpeg or browser cookies.
    """
    loop = asyncio.get_event_loop()

    # Fetch Apify metadata (async)
    apify_meta = await _fetch_apify_metadata(url)

    if apify_meta:
        metadata = apify_meta
    else:
        # instaloader is synchronous — run in thread pool
        metadata = await loop.run_in_executor(None, _fetch_instaloader_metadata, url)

    # Full fallback if both sources fail
    if not metadata:
        shortcode = _extract_shortcode(url)
        metadata = {
            "title":                   "Instagram Reel (Data Unavailable)",
            "view_count":              0,
            "like_count":              0,
            "comment_count":           0,
            "duration":                0,
            "upload_date":             "",
            "channel":                 "Unknown Creator",
            "channel_follower_count":  0,
            "tags":                    [],
            "video_id":                shortcode,
            "url":                     url,
            "caption":                 "",
            "apify_failed":            True,
            "source":                  "fallback",
        }

    # Build transcript from caption (reliable on all platforms)
    caption = metadata.get("caption") or ""
    title = metadata.get("title") or "Instagram Reel"
    hashtags = metadata.get("tags") or []

    if caption:
        transcript = f"Title: {title}\n\nCaption: {caption}"
    else:
        transcript = f"Title: {title}"

    if hashtags:
        transcript += f"\n\nHashtags: {' '.join(['#' + t for t in hashtags[:20]])}"

    print(f"[Instagram] Transcript built from caption. Length: {len(transcript)}")

    # Compute engagement rate
    views = metadata.get("view_count", 0)
    likes = metadata.get("like_count", 0)
    comments = metadata.get("comment_count", 0)
    engagement_rate = round((likes + comments) / views * 100, 2) if views > 0 else 0.0

    metadata["engagement_rate"] = engagement_rate
    metadata["transcript"] = transcript
    return metadata
