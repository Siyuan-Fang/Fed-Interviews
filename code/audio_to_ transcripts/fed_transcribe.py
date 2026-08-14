#!/usr/bin/env python3
"""Speaker-attributed transcription of broadcast interviews with Federal Reserve officials.

Replication code; README.md documents the choices that affect accuracy and how they
were measured. Stages 1-3 run on one CUDA GPU. Needs FFmpeg on PATH and ``HF_TOKEN``
(environment or ``.env``) for the gated pyannote pipeline.

    0. ffmpeg                    -> 16 kHz mono PCM
    1. Whisper large-v3          -> segment text     (faster-whisper, sequential)
    2. wav2vec2 forced alignment -> word timestamps  (WhisperX)
    3. pyannote diarization      -> speaker per word
    4. turn construction         -> dialogue transcript

Usage:
    python fed_transcribe.py -i audio                     # a directory, or one file
    python fed_transcribe.py -i audio --network presser    # FOMC press conference
"""

from __future__ import annotations

import os

# Must precede any tokenizers import downstream: pyannote's dataloader forks, and a
# forked fast tokenizer warns on every worker.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import argparse  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import textwrap  # noqa: E402
import time  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, Iterator  # noqa: E402

import fed_glossary  # noqa: E402

AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg", ".opus"}
VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts", ".m4v"}
SAMPLE_RATE = 16_000

# Gated on HuggingFace; accept the terms once. Pinning the older 3.1 release does not
# avoid this: pyannote.audio 4.x takes its PLDA weights from community-1 either way.
DIARIZE_MODEL = "pyannote/speaker-diarization-community-1"

# torchaudio alignment bundle. WhisperX defaults to the base model for English; the
# large one gives tighter word boundaries, hence tighter speaker turns.
ALIGN_MODEL_EN = "WAV2VEC2_ASR_LARGE_LV60K_960H"

# Ceiling for the domain prompt: faster-whisper only truncates at 223 of Whisper's
# 448 tokens, by which point the model degenerates into echoing the prompt.
PROMPT_TOKEN_BUDGET = 160

# A sentence ends at terminal punctuation, allowing for a trailing quote or bracket.
SENTENCE_END = re.compile(r"[.!?…]['\"”’)\]]*$")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """Every parameter of one transcription run."""

    inputs: list[Path]
    outdir: Path = Path("transcripts")
    audio_dir: Path = Path("wav")

    # Stage 1: recognition.
    model: str = "large-v3"
    device: str = "auto"  # auto | cuda | cpu
    compute_type: str | None = None  # None -> float16 on CUDA, float32 on CPU
    language: str = "en"
    beam_size: int = 5

    # Stage 1: domain priors.
    network: str = fed_glossary.DEFAULT_NETWORK
    speaker_hint: str | None = None
    initial_prompt: str | None = None  # None -> build from network + hint
    prompt_budget: int = PROMPT_TOKEN_BUDGET
    corrections: bool = True

    # Stage 2: alignment.
    align: bool = True
    align_model: str | None = None  # None -> ALIGN_MODEL_EN for English

    # Stage 3: diarization.
    diarize: bool = True
    diarize_model: str = DIARIZE_MODEL
    hf_token: str | None = None
    num_speakers: int | None = None
    min_speakers: int | None = 2  # an interview has at least two voices
    max_speakers: int | None = None

    # Stage 4: turn construction.
    turn_gap: float = 3.0  # merge same-speaker turns separated by less than this
    min_turn_words: int = 3  # absorb shorter interjections into the surrounding turn

    # Output.
    formats: tuple[str, ...] = ("dialogue", "srt", "json")
    loudnorm: bool = False
    keep_audio: bool = True
    overwrite: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def fmt_clock(seconds: float | None) -> str:
    """Seconds -> HH:MM:SS, for the timestamps in the dialogue transcript."""
    if seconds is None:
        return "--:--:--"
    total = int(seconds)
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def fmt_srt_ts(seconds: float | None) -> str:
    """Seconds -> HH:MM:SS,mmm, the timestamp format the SRT spec requires."""
    ms = int(round(max(0.0, float(seconds or 0.0)) * 1000))
    return (f"{ms // 3_600_000:02d}:{ms % 3_600_000 // 60_000:02d}"
            f":{ms % 60_000 // 1000:02d},{ms % 1000:03d}")


def resolve_hf_token(explicit: str | None) -> str | None:
    """Read the HuggingFace token from the CLI, the environment, or ``.env``."""
    if explicit:
        return explicit.strip()
    names = ("HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN")
    for name in names:
        if os.environ.get(name):
            return os.environ[name].strip()

    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.is_file():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() in names and value.strip():
            return value.strip().strip("\"'")
    return None


def collect_inputs(paths: list[Path]) -> list[Path]:
    """Expand directories, keep media files, sort by name for a stable run order."""
    media = AUDIO_SUFFIXES | VIDEO_SUFFIXES
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found += [p for p in sorted(path.iterdir()) if p.is_file()
                      and p.suffix.lower() in media and not p.name.startswith(".")]
        elif path.is_file():
            found.append(path)
        else:
            log(f"skipping missing path: {path}")
    return found


def ensure_nltk_data(language: str = "english") -> None:
    """Build the ``punkt_tab/<language>.pickle`` WhisperX's aligner loads, which no
    nltk release ships. Up front, or alignment fails after the most expensive stage.
    """
    import pickle
    import socket

    import nltk

    resource = f"tokenizers/punkt_tab/{language}"
    try:
        nltk.data.find(f"{resource}.pickle")
        return
    except LookupError:
        pass
    try:
        nltk.data.find(resource)
    except LookupError:
        log("downloading nltk sentence-tokenizer tables (punkt_tab)")
        timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)  # the default is no timeout at all
        try:
            nltk.download("punkt_tab", quiet=True)
        except Exception as exc:
            log(f"warning: punkt_tab download failed ({type(exc).__name__}); "
                "alignment will fail. Fetch it manually into ~/nltk_data/tokenizers/")
            return
        finally:
            socket.setdefaulttimeout(timeout)

    from nltk.tokenize import PunktTokenizer

    target = Path(nltk.data.path[0]) / "tokenizers" / "punkt_tab"
    target.mkdir(parents=True, exist_ok=True)
    with open(target / f"{language}.pickle", "wb") as fh:
        pickle.dump(PunktTokenizer(language), fh)


# ---------------------------------------------------------------------------
# Stage 0: audio extraction
# ---------------------------------------------------------------------------


def extract_audio(src: Path, dst: Path, loudnorm: bool = False) -> Path:
    """Decode to 16 kHz mono PCM, the input format Whisper and pyannote expect."""
    if dst.exists() and dst.stat().st_size > 0:
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-vn"]
    if loudnorm:
        # EBU R128. Broadcast level swings, and flattening it stabilises
        # voice-activity detection at the cost of a higher noise floor.
        cmd += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"]
    cmd += ["-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(dst)]
    done = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if done.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {src.name}: {done.stderr.strip()[:500]}")
    return dst


def probe_duration(path: Path) -> float:
    """Media duration in seconds, used to report the real-time factor. 0 if unknown."""
    done = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, errors="replace",
    )
    try:
        return float(done.stdout.strip())
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


def resolve_device(requested: str) -> str:
    """Pick the torch device for all three model stages."""
    import torch

    available = torch.cuda.is_available()
    if requested == "cuda" and not available:
        log("warning: CUDA requested but unavailable, falling back to CPU")
        return "cpu"
    if requested == "auto":
        return "cuda" if available else "cpu"
    return requested


def fit_prompt(prompt: str | None, budget: int) -> str | None:
    """Trim the domain prompt to ``budget`` tokens on sentence boundaries; faster-whisper
    would cut it mid-sentence, silently, and too late (see PROMPT_TOKEN_BUDGET).
    """
    if not prompt:
        return None
    try:
        from transformers import AutoTokenizer

        # All Whisper sizes share one tokenizer; tiny is the cheapest to fetch.
        encode = AutoTokenizer.from_pretrained("openai/whisper-tiny").encode
    except Exception as exc:  # counting is a check, not a reason to abort a run
        log(f"  prompt budget not checked ({type(exc).__name__})")
        return prompt

    def n_tokens(text: str) -> int:
        return len(encode(text, add_special_tokens=False))

    total = n_tokens(prompt)
    if total <= budget:
        log(f"  domain prompt: {total}/{budget} tokens")
        return prompt

    sentences = re.split(r"(?<=[.!?]) +", prompt)
    kept: list[str] = []
    used = 0
    for sentence in sentences:
        cost = n_tokens(sentence + " ")
        if used + cost > budget:
            break
        kept.append(sentence)
        used += cost
    log(f"  domain prompt: {used}/{budget} tokens "
        f"({len(sentences) - len(kept)} of {len(sentences)} sentences dropped)")
    return " ".join(kept) or None


class ModelCache:
    """Load the three models once and reuse them across files: about 8.5 GB of VRAM
    in float16 together, so all three can stay resident for a whole run.
    """

    def __init__(self, cfg: Config, device: str):
        self.cfg = cfg
        self.device = device
        self.compute_type = cfg.compute_type or (
            # CTranslate2 has no float16 CPU kernel, and int8 drops whole utterances
            # rather than merely losing precision.
            "float16" if device == "cuda" else "float32"
        )
        self.prompt: str | None = None
        self._asr: Any = None
        self._align: tuple[Any, Any, str] | None = None
        self._diarize: Any = None
        self._diarize_off = False  # missing token or load failure: do not retry

    def asr(self) -> Any:
        if self._asr is not None:
            return self._asr
        from faster_whisper import WhisperModel

        cfg = self.cfg
        prompt = (cfg.initial_prompt if cfg.initial_prompt is not None
                  else fed_glossary.build_initial_prompt(cfg.network, cfg.speaker_hint))
        self.prompt = fit_prompt(prompt, cfg.prompt_budget)

        log(f"  loading Whisper {cfg.model} "
            f"(device={self.device}, compute_type={self.compute_type})")
        t0 = time.time()
        self._asr = WhisperModel(cfg.model, device=self.device,
                                 compute_type=self.compute_type)
        log(f"  model ready ({time.time() - t0:.1f}s)")
        return self._asr

    def align(self, language: str) -> tuple[Any, Any, str] | None:
        """Alignment model for one language, cached until the language changes."""
        if self._align and self._align[2] == language:
            return self._align
        import whisperx

        name = self.cfg.align_model or (ALIGN_MODEL_EN if language == "en" else None)
        log(f"  loading alignment model (language={language}, model={name or 'default'})")
        try:
            model, metadata = whisperx.load_align_model(
                language_code=language, device=self.device, model_name=name)
        except Exception as exc:
            log(f"warning: alignment model failed to load, skipping alignment: "
                f"{type(exc).__name__}: {exc}")
            return None
        self._align = (model, metadata, language)
        return self._align

    def diarize(self) -> Any:
        if self._diarize is not None or self._diarize_off:
            return self._diarize
        from whisperx.diarize import DiarizationPipeline

        token = resolve_hf_token(self.cfg.hf_token)
        if not token:
            self._diarize_off = True
            log("warning: no HuggingFace token found, skipping diarization. "
                f"Accept the terms at https://huggingface.co/{DIARIZE_MODEL}, "
                "create a READ token, and put HF_TOKEN=... in .env")
            return None

        log(f"  loading diarization pipeline ({self.cfg.diarize_model})")
        t0 = time.time()
        try:
            self._diarize = DiarizationPipeline(
                model_name=self.cfg.diarize_model, token=token, device=self.device)
        except Exception as exc:
            self._diarize_off = True
            log(f"warning: diarization pipeline failed to load "
                f"({type(exc).__name__}: {exc}). If this is a gated-repo error, "
                f"accept the terms at https://huggingface.co/{DIARIZE_MODEL}")
            return None
        log(f"  diarization pipeline ready ({time.time() - t0:.1f}s)")
        return self._diarize


# ---------------------------------------------------------------------------
# Stages 1-3
# ---------------------------------------------------------------------------


def run_asr(audio_path: Path, cfg: Config, cache: ModelCache) -> tuple[dict[str, Any], Any]:
    """Stage 1: Whisper's own long-form loop, one 30-second window after another, each
    conditioned on the previous one. Stage 2 replaces the timestamps it returns.
    """
    import whisperx

    model = cache.asr()
    audio = whisperx.load_audio(str(audio_path))
    t0 = time.time()
    segments, info = model.transcribe(
        audio,
        language=cfg.language,
        beam_size=cfg.beam_size,
        initial_prompt=cache.prompt,
        condition_on_previous_text=True,
        vad_filter=True,
    )
    # faster-whisper decodes lazily; the generator has to be drained here.
    result = {
        "segments": [{"start": s.start, "end": s.end, "text": s.text.strip()}
                     for s in segments if s.text.strip()],
        "language": info.language,
    }
    log(f"  transcribed {len(result['segments'])} segments ({time.time() - t0:.1f}s)")
    return result, audio


def apply_corrections(segments: list[dict[str, Any]]) -> dict[str, int]:
    """Apply the glossary's substitutions in place. Before alignment, deliberately:
    "F O M C" -> "FOMC" changes the token count that timestamps are computed from.
    """
    total: dict[str, int] = {}
    for seg in segments:
        seg["text"], hits = fed_glossary.apply_corrections(str(seg.get("text") or ""))
        for key, count in hits.items():
            total[key] = total.get(key, 0) + count
    return total


def run_align(result: dict[str, Any], audio: Any, cfg: Config,
              cache: ModelCache) -> dict[str, Any]:
    """Stage 2: forced alignment, refining timestamps from segment to word level."""
    import whisperx

    language = result.get("language", cfg.language)
    loaded = cache.align(language)
    if loaded is None:
        return result
    model, metadata, _ = loaded

    t0 = time.time()
    aligned = whisperx.align(result["segments"], model, metadata, audio, cache.device,
                             return_char_alignments=False, print_progress=False)
    n_words = sum(len(seg.get("words") or []) for seg in aligned["segments"])
    log(f"  aligned {n_words} words ({time.time() - t0:.1f}s)")
    aligned["language"] = language
    return aligned


def run_diarize(result: dict[str, Any], audio: Any, cfg: Config,
                cache: ModelCache) -> tuple[dict[str, Any], int]:
    """Stage 3: label every word with a speaker; returns the result and the speaker
    count. Without a token the input comes back unchanged, transcript intact.
    """
    import whisperx

    pipeline = cache.diarize()
    if pipeline is None:
        return result, 0

    t0 = time.time()
    speakers = pipeline(audio, num_speakers=cfg.num_speakers,
                        min_speakers=cfg.min_speakers, max_speakers=cfg.max_speakers)
    n_speakers = int(speakers["speaker"].nunique()) if len(speakers) else 0
    log(f"  diarized {n_speakers} speakers over {len(speakers)} segments "
        f"({time.time() - t0:.1f}s)")
    return whisperx.assign_word_speakers(speakers, result), n_speakers


# ---------------------------------------------------------------------------
# Stage 4: from labelled words to dialogue turns
# ---------------------------------------------------------------------------


def iter_words(segments: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    """Flatten the segment/word tree into one stream. Segments alignment could not
    resolve carry no words; their text becomes one pseudo-word rather than vanishing.
    """
    for seg in segments:
        words = seg.get("words") or []
        if words:
            for word in words:
                text = str(word.get("word") or "").strip()
                if text:
                    yield {"word": text, "start": word.get("start"),
                           "end": word.get("end"), "speaker": word.get("speaker")}
        else:
            text = str(seg.get("text") or "").strip()
            if text:
                yield {"word": text, "start": seg.get("start"),
                       "end": seg.get("end"), "speaker": seg.get("speaker")}


def group_sentences(words: list[dict[str, Any]],
                    majority: float = 0.6) -> list[dict[str, Any]]:
    """Group words into sentences and give each its majority speaker, since diarization
    labels words and so flips speaker mid-sentence wherever voices overlap.

    Below ``majority`` the sentence is treated as crosstalk and split at the label
    changes; unlabelled words inherit the previous sentence's speaker.
    """
    units: list[dict[str, Any]] = []
    buffer: list[dict[str, Any]] = []

    def flush() -> None:
        if not buffer:
            return
        labels = [w["speaker"] for w in buffer if w.get("speaker")]
        if labels:
            top, count = max({s: labels.count(s) for s in set(labels)}.items(),
                             key=lambda kv: kv[1])
            if count / len(buffer) >= majority:
                units.append({"speaker": top, "words": list(buffer)})
                buffer.clear()
                return
        # Crosstalk, or nothing labelled at all: keep the word-level labels and
        # cut wherever they change.
        for word in buffer:
            speaker = word.get("speaker")
            if units and units[-1]["speaker"] == speaker:
                units[-1]["words"].append(word)
            else:
                units.append({"speaker": speaker, "words": [word]})
        buffer.clear()

    for word in words:
        buffer.append(word)
        if SENTENCE_END.search(word["word"]):
            flush()
    flush()

    # Propagate labels into unlabelled units: forward first, then backwards for
    # any units before the first labelled one.
    last: str | None = None
    for unit in units:
        if unit["speaker"]:
            last = unit["speaker"]
        else:
            unit["speaker"] = last
    first = next((u["speaker"] for u in units if u["speaker"]), "SPEAKER_00")
    for unit in units:
        if unit["speaker"]:
            break
        unit["speaker"] = first
    return units


def build_turns(units: list[dict[str, Any]], gap: float = 3.0,
                min_words: int = 3) -> list[dict[str, Any]]:
    """Merge sentence units into speaker turns. Two clean-ups, in order:

      1. Absorb interjections shorter than ``min_words`` framed by the same other
         speaker -- usually diarization jitter where speech overlaps. Real
         backchannels ("Right.") go to whoever holds the floor; 0 disables it.
      2. Merge same-speaker units less than ``gap`` seconds apart. Same-speaker
         silence here is 1.3 s at the first quartile, 2.3 s at the ninth decile.
    """
    kept: list[dict[str, Any]] = []
    i = 0
    while i < len(units):
        unit = units[i]
        island = (
            0 < i < len(units) - 1
            and len(unit["words"]) < min_words
            and units[i - 1]["speaker"] == units[i + 1]["speaker"] != unit["speaker"]
        )
        if island and kept:
            kept[-1]["words"] += unit["words"] + units[i + 1]["words"]
            i += 2  # this unit and the one after it both join the previous turn
            continue
        kept.append({"speaker": unit["speaker"], "words": list(unit["words"])})
        i += 1

    turns: list[dict[str, Any]] = []
    for unit in kept:
        if turns and turns[-1]["speaker"] == unit["speaker"]:
            prev_end = turns[-1]["words"][-1].get("end")
            start = unit["words"][0].get("start")
            if prev_end is not None and start is not None and start - prev_end <= gap:
                turns[-1]["words"] += unit["words"]
                continue
        turns.append(unit)

    for turn in turns:
        words = turn["words"]
        starts = [w["start"] for w in words if w.get("start") is not None]
        ends = [w["end"] for w in words if w.get("end") is not None]
        turn["start"] = min(starts) if starts else None
        turn["end"] = max(ends) if ends else None
        turn["text"] = " ".join(" ".join(w["word"] for w in words).split())
        # Share of the turn's words diarization itself assigned to this speaker
        # rather than inheriting through pooling. Published so it can be audited.
        labelled = sum(1 for w in words if w.get("speaker") == turn["speaker"])
        turn["speaker_share"] = round(labelled / len(words), 3) if words else 0.0
    return turns


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_dialogue(path: Path, turns: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    """The primary deliverable: a human-readable, speaker-attributed transcript."""
    lines = [
        f"# {meta['stem']} -- speaker-attributed dialogue",
        f"# model {meta['model']} | language {meta['language']} | "
        f"{meta['n_speakers']} speakers | {meta['n_turns']} turns",
        f"# audio {fmt_clock(meta['duration'])} | processed in {meta['elapsed']:.0f}s "
        f"({meta['rtf']:.1f}x real time)",
        f"# generated {meta['generated_at']}",
        "",
    ]
    for turn in turns:
        lines.append(f"[{fmt_clock(turn['start'])}] {turn['speaker']}")
        lines.append("\n".join(textwrap.wrap(
            turn["text"], width=88, initial_indent="    ", subsequent_indent="    ",
        )) or f"    {turn['text']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_srt(path: Path, segments: list[dict[str, Any]]) -> None:
    """Subtitles, for checking against the audio in a player. Keeps the original
    segmentation, since turns are far too long to display.
    """
    blocks: list[str] = []
    for seg in segments:
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        speaker = seg.get("speaker")
        blocks.append(f"{len(blocks) + 1}\n{fmt_srt_ts(seg.get('start'))} --> "
                      f"{fmt_srt_ts(seg.get('end'))}\n"
                      f"{f'[{speaker}] ' if speaker else ''}{text}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def write_json(path: Path, result: dict[str, Any], turns: list[dict[str, Any]],
               meta: dict[str, Any]) -> None:
    """Machine-readable output: turns plus the underlying word-level segments."""
    payload = {
        "metadata": meta,
        "turns": [{"speaker": t["speaker"], "start": t["start"], "end": t["end"],
                   "text": t["text"], "n_words": len(t["words"]),
                   "speaker_share": t["speaker_share"]} for t in turns],
        "segments": result.get("segments", []),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Per-file pipeline
# ---------------------------------------------------------------------------


def process_one(src: Path, cfg: Config, cache: ModelCache) -> dict[str, Any] | None:
    """Run all stages for one media file and write the requested outputs."""
    stem = src.stem
    done_marker = cfg.outdir / f"{stem}.json"
    if done_marker.exists() and not cfg.overwrite:
        log(f"--- {src.name}: already transcribed, skipping (--overwrite to redo)")
        return None

    log(f"--- {src.name}")
    t_start = time.time()

    audio_path = src if src.suffix.lower() == ".wav" else cfg.audio_dir / f"{stem}.wav"
    if audio_path != src:
        extract_audio(src, audio_path, loudnorm=cfg.loudnorm)
    duration = probe_duration(audio_path)

    result, audio = run_asr(audio_path, cfg, cache)
    if cfg.corrections:
        hits = apply_corrections(result["segments"])
        if hits:
            top = sorted(hits.items(), key=lambda kv: -kv[1])
            log("  glossary corrections: "
                + ", ".join(f"{k} x{v}" for k, v in top[:8])
                + (f", +{len(top) - 8} more" if len(top) > 8 else ""))
    if cfg.align:
        result = run_align(result, audio, cfg, cache)
    n_speakers = 0
    if cfg.diarize:
        result, n_speakers = run_diarize(result, audio, cfg, cache)

    words = list(iter_words(result.get("segments", [])))
    turns = build_turns(group_sentences(words), cfg.turn_gap, cfg.min_turn_words)

    elapsed = time.time() - t_start
    meta = {
        "stem": stem,
        "source": str(src),
        "model": cfg.model,
        "compute_type": cache.compute_type,
        "align_model": cfg.align_model or ALIGN_MODEL_EN,
        "diarize_model": cfg.diarize_model,
        "network_prompt": cfg.network,
        "language": result.get("language", cfg.language),
        "n_speakers": n_speakers,
        "n_turns": len(turns),
        "n_words": len(words),
        "duration": round(duration, 2),
        "elapsed": round(elapsed, 1),
        "rtf": round(duration / elapsed, 2) if elapsed > 0 else 0.0,
        "device": cache.device,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }

    cfg.outdir.mkdir(parents=True, exist_ok=True)
    if "dialogue" in cfg.formats:
        write_dialogue(cfg.outdir / f"{stem}.dialogue.txt", turns, meta)
    if "srt" in cfg.formats:
        write_srt(cfg.outdir / f"{stem}.srt", result.get("segments", []))
    if "json" in cfg.formats:
        write_json(cfg.outdir / f"{stem}.json", result, turns, meta)
    if not cfg.keep_audio and audio_path != src:
        audio_path.unlink(missing_ok=True)

    log(f"  done: {len(turns)} turns, {len(words)} words, {n_speakers} speakers, "
        f"{elapsed:.0f}s ({meta['rtf']:.1f}x real time)")
    return meta


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Speaker-attributed transcription of Federal Reserve interviews.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-i", "--input", nargs="+", required=True, type=Path,
                   help="input files or directories")
    p.add_argument("-o", "--outdir", type=Path, default=Path("transcripts"),
                   help="directory for the transcripts")
    p.add_argument("--audio-dir", type=Path, default=Path("wav"),
                   help="directory for the extracted 16 kHz wav files")
    p.add_argument("--overwrite", action="store_true",
                   help="re-transcribe files that already have output")

    g = p.add_argument_group("recognition")
    g.add_argument("--model", default="large-v3", help="Whisper model")
    g.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"],
                   help="torch device for all three model stages")
    g.add_argument("--compute-type", default=None,
                   choices=["float16", "float32", "int8_float16", "int8_float32", "int8"],
                   help="CTranslate2 precision (default: float16 on CUDA, float32 on "
                        "CPU; the int8 variants drop whole utterances)")
    g.add_argument("--language", default="en", help="language code")
    g.add_argument("--beam-size", type=int, default=5, help="beam search width")

    g = p.add_argument_group("domain priors")
    g.add_argument("--network", default=fed_glossary.DEFAULT_NETWORK,
                   choices=sorted(fed_glossary.INTERVIEW_CONTEXTS),
                   help="source of the material; selects the prompt's opening "
                        "sentence ('presser' for FOMC press conferences)")
    g.add_argument("--speaker-hint", default=None,
                   help="one sentence naming the official, e.g. \"The official being "
                        "interviewed is Governor Christopher Waller.\"")
    g.add_argument("--initial-prompt", default=None,
                   help="replace the domain prompt entirely (ignores --network)")
    g.add_argument("--no-initial-prompt", action="store_true",
                   help="decode without a domain prompt")
    g.add_argument("--prompt-budget", type=int, default=PROMPT_TOKEN_BUDGET,
                   help="token ceiling for the domain prompt")
    g.add_argument("--no-corrections", action="store_true",
                   help="skip the glossary's post-decoding substitutions")

    g = p.add_argument_group("alignment and diarization")
    g.add_argument("--no-align", action="store_true",
                   help="skip word-level alignment (degrades speaker attribution)")
    g.add_argument("--align-model", default=None,
                   help=f"torchaudio alignment bundle (default: {ALIGN_MODEL_EN} for English)")
    g.add_argument("--no-diarize", action="store_true", help="skip speaker diarization")
    g.add_argument("--diarize-model", default=DIARIZE_MODEL, help="pyannote pipeline")
    g.add_argument("--hf-token", default=None,
                   help="HuggingFace token (default: HF_TOKEN from the environment or .env)")
    g.add_argument("--num-speakers", type=int, default=None,
                   help="exact number of speakers, when known")
    g.add_argument("--min-speakers", type=int, default=2, help="lower bound on speakers")
    g.add_argument("--max-speakers", type=int, default=None, help="upper bound on speakers")

    g = p.add_argument_group("output")
    g.add_argument("--formats", nargs="+", default=["dialogue", "srt", "json"],
                   choices=["dialogue", "srt", "json"], help="output formats")
    g.add_argument("--turn-gap", type=float, default=3.0,
                   help="seconds of silence tolerated when merging same-speaker turns")
    g.add_argument("--min-turn-words", type=int, default=3,
                   help="absorb shorter interjections into the surrounding turn "
                        "(0 keeps every unit as diarized)")
    g.add_argument("--loudnorm", action="store_true",
                   help="apply EBU R128 loudness normalisation when extracting audio")
    g.add_argument("--no-keep-audio", action="store_true",
                   help="delete the extracted wav after transcription")
    return p


def main() -> int:
    args = build_parser().parse_args()

    missing = [tool for tool in ("ffmpeg", "ffprobe") if not shutil.which(tool)]
    if missing:
        log(f"error: {', '.join(missing)} not found on PATH; install FFmpeg first")
        return 1

    inputs = collect_inputs(args.input)
    if not inputs:
        log("error: no media files found")
        return 1
    if not args.no_align:
        ensure_nltk_data()

    prompt = args.initial_prompt
    if args.no_initial_prompt:
        prompt = ""  # empty means "explicitly none"; None means "build the default"

    cfg = Config(
        inputs=inputs, outdir=args.outdir, audio_dir=args.audio_dir,
        model=args.model, device=args.device, compute_type=args.compute_type,
        language=args.language, beam_size=args.beam_size,
        network=args.network, speaker_hint=args.speaker_hint,
        initial_prompt=prompt, prompt_budget=args.prompt_budget,
        corrections=not args.no_corrections, align=not args.no_align,
        align_model=args.align_model, diarize=not args.no_diarize,
        diarize_model=args.diarize_model, hf_token=args.hf_token,
        num_speakers=args.num_speakers, min_speakers=args.min_speakers,
        max_speakers=args.max_speakers, formats=tuple(args.formats),
        turn_gap=args.turn_gap, min_turn_words=args.min_turn_words,
        loudnorm=args.loudnorm, keep_audio=not args.no_keep_audio,
        overwrite=args.overwrite,
    )

    cache = ModelCache(cfg, resolve_device(cfg.device))
    log(f"{len(inputs)} file(s) to process on {cache.device}")

    failed: list[str] = []
    for src in inputs:
        try:
            process_one(src, cfg, cache)
        except KeyboardInterrupt:
            log("interrupted")
            return 130
        except Exception as exc:
            failed.append(src.name)
            log(f"error: {src.name} failed: {type(exc).__name__}: {exc}")
            import traceback

            traceback.print_exc()

    if failed:
        log(f"finished with {len(failed)}/{len(inputs)} failures: {', '.join(failed)}")
        return 1
    log("finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
