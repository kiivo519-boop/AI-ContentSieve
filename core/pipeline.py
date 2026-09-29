"""Transactional job orchestration and UTF-8 result exports."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from uuid import uuid4

from core.analyzer import analyze
from core.downloader import Progress, download_media, validate_url
from core.transcriber import WhisperTranscriber, render_script, render_srt


@dataclass(frozen=True)
class JobResult:
    folder: Path
    transcript: str
    analysis: str


def run_pipeline(url: str, output: Path, model: str,
                 transcriber: WhisperTranscriber, progress: Progress) -> JobResult:
    """Publish only complete jobs; cleanup staging on success or failure."""
    url = validate_url(url)
    output = output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    name = f"contentsieve_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}"
    destination = output / name
    # Staging on the destination volume allows a final atomic directory rename.
    with tempfile.TemporaryDirectory(prefix=".contentsieve-", dir=output) as temp:
        work = Path(temp)
        media = download_media(url, work / "media", progress)
        progress(0.60, "Preparing local transcription…")
        transcript = transcriber.transcribe(
            media.audio, model, lambda message: progress(0.65, message)
        )
        progress(0.88, "Analyzing transcript and writing results…")
        script = render_script(transcript)
        analysis = analyze(transcript, media.title, media.duration)
        publish = work / "results"
        publish.mkdir()
        media.video.replace(publish / "video.mp4")
        (publish / "transcript.txt").write_text(script, encoding="utf-8")
        (publish / "transcript.srt").write_text(render_srt(transcript), encoding="utf-8")
        (publish / "analysis.md").write_text(analysis, encoding="utf-8")
        metadata = {
            "app": "AI ContentSieve", "source_url": url, "title": media.title,
            "duration_seconds": media.duration,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "analysis_method": "local_extractive_term_frequency",
            "transcript": transcript.to_dict(),
        }
        (publish / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        publish.rename(destination)
    progress(1.0, "Complete. Temporary audio and source media removed.")
    return JobResult(destination, script, analysis)