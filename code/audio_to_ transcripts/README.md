# Speaker-attributed transcription of Federal Reserve interviews

Replication code. Each media file becomes a dialogue transcript in which every
utterance carries a speaker label and a timestamp.

| Stage | Component | Output |
|---|---|---|
| 0 | FFmpeg | 16 kHz mono PCM |
| 1 | Whisper `large-v3` (faster-whisper, sequential) | segment-level text |
| 2 | wav2vec2 `LARGE_LV60K_960H` (WhisperX) | word-level timestamps |
| 3 | pyannote `speaker-diarization-community-1` | speaker label per word |
| 4 | turn construction | dialogue transcript |

Domain priors and post-hoc corrections in `fed_glossary.py` handle the vocabulary of
U.S. monetary policy. On an RTX 4090 the pipeline runs at about 13x real time over
this corpus (8-21x per file).

The corpus transcribed for the paper: 138 files, 27.5 hours of audio, 298,176 words
in 3,396 turns, 2.1 hours of compute on one RTX 4090.

## Install

Linux with an NVIDIA GPU (developed on an RTX 4090, 24 GB, CUDA 12.8; uses about
8.5 GB of VRAM), FFmpeg on `PATH`, Python 3.10-3.13. `--device cpu` works, far more
slowly, and was not benchmarked.

```bash
apt-get install -y ffmpeg

python -m venv .venv
.venv/bin/pip install torch==2.8.0 torchaudio==2.8.0 torchvision==0.23.0 \
    --index-url https://download.pytorch.org/whl/cu128
.venv/bin/pip install whisperx==3.8.6
```

The CUDA build of `torch` must go first: installing `whisperx` on its own pulls the
CPU-only wheels over it. Versions used for the paper: `torch` 2.8.0+cu128, `whisperx`
3.8.6, `faster-whisper` 1.2.1, `ctranslate2` 4.8.1, `pyannote.audio` 4.0.7,
`transformers` 4.57.6, FFmpeg 4.4.2.

The first run downloads about 4.5 GB of weights into `~/.cache/huggingface`,
`~/.cache/torch` and `~/nltk_data`. Where `huggingface.co` is unreachable, set
`HF_ENDPOINT=https://hf-mirror.com`.

### HuggingFace token

Diarization is gated: accept the terms at
<https://huggingface.co/pyannote/speaker-diarization-community-1>, create a READ
token, and put `HF_TOKEN=hf_...` in `.env` here. Pinning pyannote 3.1 does not avoid
this — 4.x loads its PLDA weights from `community-1` either way. Test access by
downloading a file; `HfApi.model_info` returns metadata for gated repositories and so
proves nothing:

```bash
.venv/bin/python -c "
from huggingface_hub import hf_hub_download
hf_hub_download('pyannote/speaker-diarization-community-1', 'config.yaml')"
```

Without a token the run still completes, and produces a transcript with no speaker
labels rather than failing.

## Usage

```bash
# The whole corpus. Models are loaded once and reused across files.
.venv/bin/python fed_transcribe.py -i audio

# FOMC press conference: primes the press corps and their outlets.
.venv/bin/python fed_transcribe.py -i audio --network presser

# Known one-on-one interview: bounding the speaker count sharpens diarization.
.venv/bin/python fed_transcribe.py -i audio --min-speakers 2 --max-speakers 3

# Known interviewee: the safest way to prime a specific name.
.venv/bin/python fed_transcribe.py -i audio/20181203_113000.mp3 \
    --speaker-hint "The official being interviewed is Vice Chair Richard Clarida."
```

Files with an existing `transcripts/*.json` are skipped, so an interrupted run
resumes; `--overwrite` forces re-transcription. `--help` lists every parameter.

Output is not bit-reproducible — float16 beam search on the GPU is not deterministic
across processes, and re-transcribing one file changed its word count by about 1%.
The transcripts in `transcripts/` are the ones the paper uses.

## Output

Three files per input, in `transcripts/`:

| File | Contents |
|---|---|
| `<stem>.dialogue.txt` | the primary deliverable: turns, each with a timestamp and a speaker |
| `<stem>.json` | the same turns plus every word with its timestamp, and a `speaker_share` per turn |
| `<stem>.srt` | subtitles, for spot-checking against the audio in a player |

```
# 20211116_134500 -- speaker-attributed dialogue
# model large-v3 | language en | 4 speakers | 21 turns
# audio 00:14:12 | processed in 61s (14.0x real time)
# generated 2026-08-13T23:19:51+08:00

[00:00:00] SPEAKER_01
    But there is an elephant in the room, or at least it will be imminently in the room.
    So let me start with that. Sherrod Brown, chair of the Senate Banking Committee,
    told us last night, as far as he knows, it is down to Lael Brainard or Jay Powell
```

`speaker_share` is the fraction of a turn's words that diarization itself assigned to
that speaker, as opposed to inheriting the label through sentence pooling; low values
flag turns worth checking by hand. The median turn is 1.000 and 0.9% fall below 0.7.

Speaker labels are stable within a file but carry no meaning across files, and
mapping them to names is left to the user. Three files here are full programme blocks
rather than single interviews (24, 47 and 49 minutes) and contain the surrounding
newscast, so their speaker count runs into the twenties; the interview inside them is
still labelled consistently.

## Choices that affect accuracy

The first three depart from WhisperX's defaults and were measured on three files of
this corpus (2.7, 14.2 and 36.5 minutes).

| Choice | Why |
|---|---|
| sequential decoding, not batched chunking | Chunking is 3-5x faster but silently discards speech: 22.2%, 17.1% and 17.2% fewer words on the three files. In one it dropped eleven consecutive seconds from an answer on tariff pass-through and shifted the following sentences by thirteen seconds, which alignment and diarization then preserved. Stage 1 runs faster-whisper's own long-form loop; WhisperX is used only to align. |
| cross-window text conditioning on | Whisper's documented route to repetition loops, so it was measured: word count within 2%, punctuation density up from 6.4-14.1 to 12.3-16.5 marks per 100 words, no 8-gram repeated more than twice. faster-whisper resets the prompt on every temperature fallback, which is what keeps the loops away. |
| a domain prompt, not `hotwords` | The prompt's main effect is style — without it Whisper drifts into lowercase, unpunctuated text on broadcast audio. Hotwords compete for the same 448-token window and bias beam search hard enough to replace a correct word with a similar-sounding wrong one ("NX", net exports, became "index"); supplied alongside a prompt they collapsed the output into `FOMC, FOMC, FOMC`. New vocabulary goes into `CORRECTIONS` instead, which costs no tokens. |
| corrections applied before alignment | Rewriting `F O M C` as `FOMC` changes the token count, so timestamps computed beforehand would not match the published text. |
| numerals kept | WhisperX suggests suppressing them to help alignment, but "25 basis points" and "3.2%" are the object of study. |
| voice-activity filtering on | Stops Whisper inventing boilerplate ("Thanks for watching") over music and dead air; changed the test transcripts by at most 4 words out of 7,010. |
| `LARGE_LV60K_960H` for alignment | Turns are cut from word timestamps, so alignment precision bounds attribution precision. WhisperX defaults to `BASE_960H` for English. |
| labels pooled per sentence, 60% majority | Diarization labels words, not clauses, so word-by-word reading flips speaker mid-sentence where voices overlap. Below 60% the sentence is treated as crosstalk and split at the label changes. |
| `--turn-gap 3.0` | Same-speaker silence here is 1.3 s at the first quartile and 2.3 s at the ninth decile, so 3 s absorbs pauses for breath without merging across a break or a taped clip. |
| `--min-turn-words 3` | Absorbs a short interjection framed by the same other speaker, usually diarization jitter where speech overlaps. The cost is that genuine backchannels ("Right.") go to whoever holds the floor; `0` disables it. |
| `--min-speakers 2` | An interview has at least two voices; clustering otherwise occasionally collapses to one. |
| float16 on CUDA, float32 on CPU | CTranslate2 has no float16 CPU kernel, and its `int8` variants drop whole utterances rather than merely losing precision. |
