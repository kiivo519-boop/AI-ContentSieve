"""Transparent extractive analysis, not an LLM or visual-video analysis."""

from collections import Counter
import re

from core.transcriber import Transcript, timestamp


STOPWORDS = set("""
a an and are as at be been but by can did do does for from had has have he her
here him his how i if in into is it its just like me more my no not of on or our
out really she so some than that the their them then there these they this those
to too up us very was we were what when where which who why will with would you your
а без был была были быть в вам вас ваш вы да для до его ее её если есть и из или
их к как ко который кто ли мне мой мы на не нет но о он она они оно от по при
с со так там то того тоже только тут ты у уже что чтобы это этот я
""".split())


def words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", text.lower(), re.UNICODE)


def analyze(transcript: Transcript, title: str, duration: float) -> str:
    """Rank transcript segments by term frequency and retain source ordering."""
    tokens = words(transcript.text)
    counts = Counter(word for word in tokens if len(word) > 2 and word not in STOPWORDS)
    keywords = [word for word, _ in counts.most_common(10)]
    duration = max(duration, max((s.end for s in transcript.segments), default=0))
    lines = [
        "# AI ContentSieve — Content Analysis", "", f"## {title}", "",
        "> Local, extractive analysis of speech only. Not an LLM-generated critique;",
        "> no visual analysis, performance prediction, or factual verification.", "",
        "## Overview", f"- Detected language: {transcript.language}",
        f"- Whisper model: {transcript.model}",
        f"- Media duration: {timestamp(duration)}",
        f"- Approximate word count: {len(tokens)}",
        f"- Approximate words/minute (whole clip): {len(tokens) * 60 / duration:.0f}"
        if duration > 0 else "- Approximate words/minute: unavailable",
        "", "## Extractive summary",
    ]
    if not transcript.segments:
        lines += ["No speech detected. There is not enough text to analyze."]
    else:
        def score(index: int) -> float:
            terms = [w for w in words(transcript.segments[index].text) if w in counts]
            return sum(counts[w] for w in terms) / max(len(terms), 1) ** 0.5

        selected = sorted(sorted(range(len(transcript.segments)), key=score,
                                 reverse=True)[:3])
        lines += [f"- [{timestamp(transcript.segments[i].start)}] "
                  f"{transcript.segments[i].text}" for i in selected]
        lines += ["", "## Opening / potential hook", transcript.segments[0].text]
        cta = re.compile(
            r"\b(?:subscribe|follow|comment|share|save|like|click|check out)\b|"
            r"подпис|коммент|сохрани|лайк|поделись|переход", re.IGNORECASE,
        )
        matches = [s for s in transcript.segments if cta.search(s.text)]
        lines += ["", "## Possible calls to action (keyword matches)"]
        lines += ([f"- [{timestamp(s.start)}] {s.text}" for s in matches[:5]]
                  or ["No English/Russian call-to-action keywords detected."])
    lines += ["", "## Recurring keywords",
              ", ".join(keywords) or "Not enough text.", "",
              "## Creator review checklist",
              "- Does the opening state a clear benefit or question?",
              "- Can the key point become a standalone caption or short clip?",
              "- Is there one clear next action for the audience?",
              "- Verify names, claims, subtitles, and timing against the original.", "",
              "*Timestamps and word counts are approximate. Whisper can make errors,",
              "especially on silence, music, or overlapping speech. Keyword matching",
              "can produce false positives; English/Russian stopwords are used.*", ""]
    return "\n".join(lines)