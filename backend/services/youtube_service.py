import os
import re
import uuid
import tempfile
import asyncio
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

load_dotenv()

# Temp directory for audio (if needed in future extensions)
_tmp_dir = os.path.join(tempfile.gettempdir(), "videoiq_audio")
os.makedirs(_tmp_dir, exist_ok=True)

def _extract_video_id(url: str) -> str:
    """Extract the YouTube video ID from various URL formats."""
    # Patterns cover standard, shortened, embed, and /shorts/ URLs
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(regex, url)
    return match.group(1) if match else ""

def _yt_dlp_opts():
    """Base yt-dlp options with minimal output, suitable for metadata extraction."""
    return {
        'quiet': True,
        'skip_download': True,
        'extract_flat': False,
        'no_warnings': True,
    }

def _extract_metadata(url: str) -> dict:
    """Pull video metadata using yt-dlp. Returns a dict with common fields."""
    opts = _yt_dlp_opts()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return {}
            return {
                'title': info.get('title') or 'YouTube Video',
                'description': info.get('description') or '',
                'view_count': int(info.get('view_count') or 0),
                'like_count': int(info.get('like_count') or 0),
                'comment_count': int(info.get('comment_count') or 0),
                'duration': int(info.get('duration') or 0),
                'upload_date': info.get('upload_date') or '',
                'channel': info.get('channel') or info.get('uploader') or 'Unknown Channel',
                'channel_subscriber_count': int(info.get('channel_follower_count') or 0),
                'tags': info.get('tags') or [],
                'video_id': info.get('id') or _extract_video_id(url),
                'url': url,
                'source': 'yt-dlp'
            }
    except Exception as e:
        print(f"[YouTube Service] yt-dlp metadata extraction failed: {e}")
        return {}

def _fetch_transcript(video_id: str) -> str:
    """Retrieve the transcript via youtube-transcript-api v1.x. Returns a single string."""
    try:
        ytt = YouTubeTranscriptApi()
        transcript = ytt.fetch(video_id, languages=['en'])
        # transcript is a FetchedTranscript iterable of snippet objects
        return " ".join([snippet.text for snippet in transcript])
    except Exception as e:
        print(f"[YouTube Service] Transcript fetch failed for {video_id}: {e}")
        return ""

async def get_youtube_data(url: str) -> dict:
    """Public async entry point used by the ingest route.
    Returns a dict containing metadata, transcript and engagement rate.
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return {'error': 'Unable to parse YouTube video ID from URL'}

    loop = asyncio.get_event_loop()
    # Run I/O bound parts in thread pool
    meta = await loop.run_in_executor(None, lambda: _extract_metadata(url))
    transcript = await loop.run_in_executor(None, lambda: _fetch_transcript(video_id))

    # Fallback to Title + Description if transcript is empty
    if not transcript:
        title = meta.get('title') or 'YouTube Video'
        description = meta.get('description') or ''
        transcript = f"Title: {title}\nDescription: {description}"
        print(f"[YouTube Service] Transcript empty for {video_id}, using fallback.")

    # Merge and compute engagement rate
    views = meta.get('view_count', 0)
    likes = meta.get('like_count', 0)
    comments = meta.get('comment_count', 0)
    engagement_rate = round((likes + comments) / views * 100, 2) if views > 0 else 0.0

    meta.update({
        'transcript': transcript,
        'engagement_rate': engagement_rate,
        'video_id': video_id,
        'source': 'youtube'
    })
    return meta
