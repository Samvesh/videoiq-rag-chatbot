import os
import re
import uuid
import tempfile
import asyncio
import httpx
import yt_dlp
import instaloader
from dotenv import load_dotenv

load_dotenv()

# ── Temp dir for audio files ──────────────────────────────────────────────────
_tmp_dir = os.path.join(tempfile.gettempdir(), "videoiq_audio")
os.makedirs(_tmp_dir, exist_ok=True)

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

# ── Whisper model cache ───────────────────────────────────────────────────────
_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model("tiny")
    return _whisper_model


# ── Shortcode extraction ──────────────────────────────────────────────────────
def _extract_shortcode(url: str) -> str:
    """
    Extracts the shortcode from Instagram Reel / Post URLs.
    Handles formats:
      https://www.instagram.com/reel/ABC123/
      https://www.instagram.com/p/ABC123/
      https://instagram.com/reel/ABC123/?igshid=...
    """
    match = re.search(r"instagram\.com/(?:reel|p|tv)/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    # Fallback: last path segment
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

        description = post.caption or ""
        hashtags = re.findall(r"#(\w+)", description)

        return {
            "title":                   f"Instagram Reel by @{post.owner_username}",
            "view_count":              int(post.video_view_count or 0),
            "like_count":              int(post.likes or 0),
            "comment_count":           int(post.comments or 0),
            "duration":                0,                        # not exposed by instaloader
            "upload_date":             post.date.strftime("%Y%m%d") if post.date else "",
            "channel":                 post.owner_username,
            "channel_follower_count":  int(followers),
            "tags":                    hashtags,
            "video_id":                shortcode,
            "url":                     url,
            "apify_failed":            False,
            "source":                  "instaloader",
        }
    except Exception as e:
        print(f"[Instagram] instaloader failed for {url}: {e}")
        return {}


# ── Audio download + Whisper transcription ────────────────────────────────────
def _download_and_transcribe(url: str) -> str:
    """
    Try to download audio via yt-dlp using Chrome browser cookies.
    Falls back gracefully with an informative message if auth is needed.
    """
    file_id = str(uuid.uuid4())
    out_template = os.path.join(_tmp_dir, f"{file_id}.%(ext)s")

    cookies_file = os.getenv("INSTAGRAM_COOKIES_FILE", "")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
    }

    # Use exported cookie file if provided, otherwise try Chrome session
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts["cookiefile"] = cookies_file
    else:
        ydl_opts["cookiesfrombrowser"] = ("chrome",)

    downloaded_path = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        # Locate downloaded file
        mp3_path = os.path.join(_tmp_dir, f"{file_id}.mp3")
        if os.path.exists(mp3_path):
            downloaded_path = mp3_path
        else:
            for fname in os.listdir(_tmp_dir):
                if fname.startswith(file_id):
                    downloaded_path = os.path.join(_tmp_dir, fname)
                    break

        if not downloaded_path:
            raise FileNotFoundError("Audio file not created after download.")

        model = _get_whisper()
        result = model.transcribe(downloaded_path)
        transcript = (result.get("text") or "").strip()
        return transcript if transcript else "Audio transcription returned empty text."

    except Exception as e:
        err = str(e).lower()
        print(f"[Instagram] audio transcription failed: {e}")
        if any(k in err for k in ("login", "cookie", "auth", "empty media", "private")):
            return (
                "Instagram audio transcription requires authentication. "
                "Log into Instagram in Chrome and retry — the app reads your Chrome session automatically. "
                "Alternatively, export cookies to a Netscape file and set INSTAGRAM_COOKIES_FILE in backend/.env."
            )
        return "Instagram Reel audio could not be transcribed. Ensure the Reel is public."
    finally:
        if downloaded_path and os.path.exists(downloaded_path):
            try:
                os.remove(downloaded_path)
            except Exception:
                pass


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
                    "apify_failed":            False,
                    "source":                  "apify",
                }
    except Exception as e:
        print(f"[Instagram] Apify failed: {e}")
    return {}


# ── Public entry point ────────────────────────────────────────────────────────
async def get_instagram_data(url: str) -> dict:
    """
    Fetch Instagram Reel metadata + transcript.

    Priority order for metadata:
      1. Apify (if APIFY_TOKEN set) — richest data
      2. instaloader — works for public Reels without login ✅
      3. Graceful zeros fallback

    Transcript:
      yt-dlp with Chrome browser cookies → Whisper tiny
    """
    loop = asyncio.get_event_loop()

    # Run metadata fetch and audio transcription concurrently
    apify_task = _fetch_apify_metadata(url)
    transcript_task = loop.run_in_executor(None, _download_and_transcribe, url)

    apify_meta, transcript = await asyncio.gather(apify_task, transcript_task)

    # Pick best metadata source
    if apify_meta:
        metadata = apify_meta
    else:
        # instaloader runs in thread pool (it's sync)
        metadata = await loop.run_in_executor(None, _fetch_instaloader_metadata, url)

    # Full fallback if both fail
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
            "apify_failed":            True,
            "source":                  "fallback",
        }

    # Compute engagement rate
    views = metadata.get("view_count", 0)
    likes = metadata.get("like_count", 0)
    comments = metadata.get("comment_count", 0)
    engagement_rate = round((likes + comments) / views * 100, 2) if views > 0 else 0.0

    metadata["engagement_rate"] = engagement_rate
    metadata["transcript"] = transcript
    return metadata
