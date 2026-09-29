"""Local multilingual Whisper transcription with exportable timestamps."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str
    segments: list[Segment]
    model: str

    def to_dict(self) -> dict:
        return asdict(self)


def timestamp(seconds: float, srt: bool = False) -> str:
    """Round before splitting to avoid invalid timestamps such as 00:00:60."""
    milliseconds = max(0, round(seconds * 1000))
    seconds_total, millis = divmod(milliseconds, 1000)
    minutes_total, secs = divmod(seconds_total, 60)
    hours, minutes = divmod(minutes_total, 60)
    separator = "," if srt else "."
    return f"{hours:02}:{minutes:02}:{secs:02}{separator}{millis:03}"


def render_script(transcript: Transcript) -> str:
    header = f"Language: {transcript.language}\nWhisper model: {transcript.model}\n"
    lines = [f"[{timestamp(s.start)} → {timestamp(s.end)}] {s.text}"
             for s in transcript.segments]
    return header + "\n" + ("\n".join(lines) or "[No speech detected]") + "\n"


def render_srt(transcript: Transcript) -> str:
    return "\n\n".join(
        f"{index}\n{timestamp(segment.start, True)} --> "
        f"{timestamp(segment.end, True)}\n{segment.text}"
        for index, segment in enumerate(transcript.segments, 1)
    ) + ("\n" if transcript.segments else "")


class WhisperTranscriber:
    """Keep one CPU model cached between sequential GUI jobs.

    CPU/fp32 works without CUDA. The first use downloads weights to Whisper's
    normal cache; subsequent transcriptions use those local weights.
    """

    def __init__(self) -> None:
        self._model = None
        self._model_name = None

    def transcribe(self, audio: Path, model_name: str,
                   status: Callable[[str], None]) -> Transcript:
        if model_name not in {"tiny", "base"}:
            raise ValueError("Choose the tiny or base Whisper model.")
        if not audio.is_file():
            raise FileNotFoundError(f"Audio file not found: {audio}")
        import whisper  # Heavy imports stay off the GUI thread.

        if self._model is None or self._model_name != model_name:
            status(f"Loading Whisper {model_name}; first use downloads model weights…")
            self._model = None
            self._model_name = None
            self._model = whisper.load_model(model_name, device="cpu")
            self._model_name = model_name
        status("Transcribing locally on CPU; this stage may take several minutes…")
        result = self._model.transcribe(str(audio), fp16=False, verbose=None,
                                        task="transcribe", temperature=0)
        segments = [
            Segment(float(item["start"]), float(item["end"]), item["text"].strip())
            for item in result.get("segments", []) if item["text"].strip()
        ]
        return Transcript(
            " ".join(segment.text for segment in segments),
            str(result.get("language") or "unknown"), segments, model_name,
        )