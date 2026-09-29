"""Download one public video and normalize its media using system FFmpeg.

The caller owns the working directory and its lifetime. No shell is used when
executing FFmpeg, and remote titles are never used as filesystem paths.
"""

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable
from urllib.parse import urlsplit


Progress = Callable[[float, str], None]
SUPPORTED_HOSTS = ("youtube.com", "youtu.be", "instagram.com", "tiktok.com")


class DownloadError(RuntimeError):
    """A user-actionable extraction or media-processing failure."""


@dataclass(frozen=True)
class DownloadedMedia:
    video: Path
    audio: Path
    title: str
    source_url: str
    duration: float


def validate_url(url: str) -> str:
    """Accept HTTP(S) links only on supported platform domains."""
    url = url.strip()
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError as exc:
        raise ValueError("The video URL is malformed.") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 80, 443}
        or not any(host == domain or host.endswith("." + domain)
                   for domain in SUPPORTED_HOSTS)
    ):
        raise ValueError("Paste a YouTube, Instagram Reels, or TikTok HTTP(S) URL.")
    if not parsed.path.strip("/"):
        raise ValueError("Paste a link to a video, not the platform homepage.")
    return url


def check_dependencies() -> None:
    """Fail before downloading if required system executables are absent."""
    missing = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        raise DownloadError(
            f"Missing {', '.join(missing)}. Install FFmpeg, add its bin folder "
            "to PATH, then restart the application. See README.md."
        )


def _ffmpeg(arguments: list[str]) -> None:
    """Capture bounded diagnostics without a pipe filling up on long jobs."""
    with tempfile.TemporaryFile() as diagnostics:
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                 *arguments],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=diagnostics,
                timeout=900,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise DownloadError("FFmpeg exceeded the 15-minute processing limit.") from exc
        except OSError as exc:
            raise DownloadError(f"Could not run FFmpeg: {exc}") from exc
        if result.returncode:
            diagnostics.seek(0, 2)
            diagnostics.seek(max(0, diagnostics.tell() - 3000))
            detail = diagnostics.read().decode("utf-8", errors="replace").strip()
            raise DownloadError(f"FFmpeg could not process this media: {detail}")


def download_media(url: str, work_dir: Path, progress: Progress) -> DownloadedMedia:
    """Download a single video, export H.264/AAC MP4 and 16 kHz mono WAV.

    MP4 normalization improves player compatibility; it does not remove any
    watermark embedded in the source video. yt-dlp retries network failures.
    """
    url = validate_url(url)
    check_dependencies()
    try:
        import yt_dlp
    except ImportError as exc:
        raise DownloadError("Install Python dependencies from requirements.txt.") from exc

    work_dir.mkdir(parents=True, exist_ok=True)
    progress(0.03, "Resolving video and downloading media…")

    def on_download(data: dict) -> None:
        if data.get("status") == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            fraction = min(data.get("downloaded_bytes", 0) / total, 1) if total else 0
            progress(0.05 + fraction * 0.30, "Downloading media…")
        elif data.get("status") == "finished":
            progress(0.36, "Download stream complete; preparing media…")

    class Logger:
        def debug(self, message: str) -> None:
            pass  # Avoid flooding the GUI with extractor internals.

        def warning(self, message: str) -> None:
            progress(0.05, f"Warning: {message}")

        def error(self, message: str) -> None:
            pass  # The raised DownloadError carries the final diagnostic.

    options = {
        "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "outtmpl": str(work_dir / "source.%(ext)s"),
        "merge_output_format": "mkv",
        "noplaylist": True,
        "playlistend": 1,
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 30,
        "quiet": True,
        "noprogress": True,
        "logger": Logger(),
        "progress_hooks": [on_download],
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
        if not info or info.get("_type") in {"playlist", "multi_video"}:
            raise DownloadError("Use a single video URL, not a playlist or profile.")
    except yt_dlp.utils.DownloadError as exc:
        raise DownloadError(
            f"Download failed: {exc}\nCheck that the video is public, update "
            "yt-dlp, and verify FFmpeg and the YouTube JavaScript runtime. "
            "Private, region-blocked, or login-required videos may be unavailable."
        ) from exc

    # yt-dlp may change extensions during merging, so inspect the final output.
    sources = [p for p in work_dir.glob("source.*")
               if p.is_file() and p.suffix.lower() in
               {".mp4", ".mkv", ".webm", ".mov", ".flv", ".avi", ".3gp", ".ts"}]
    if len(sources) != 1:
        raise DownloadError("Could not identify one complete downloaded video.")
    source = sources[0]
    video, audio = work_dir / "video.mp4", work_dir / "audio.wav"
    progress(0.40, "Creating compatible MP4 (H.264 / AAC)…")
    _ffmpeg([
        "-i", str(source), "-map", "0:v:0", "-map", "0:a:0",
        "-map_metadata", "-1", "-map_chapters", "-1",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(video),
    ])
    progress(0.52, "Extracting temporary 16 kHz mono audio…")
    _ffmpeg(["-i", str(source), "-map", "0:a:0", "-vn", "-ac", "1",
             "-ar", "16000", "-c:a", "pcm_s16le", str(audio)])
    if not video.is_file() or not audio.is_file():
        raise DownloadError("Media conversion did not produce the expected files.")
    return DownloadedMedia(video, audio, str(info.get("title") or "Untitled video"),
                           url, float(info.get("duration") or 0))