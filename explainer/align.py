"""Word-aligns a recorded VO to the script with faster-whisper word timestamps.

Two matching passes (raw tokens, then spoken-form expansions), interpolation for
unmatched words, and phrase-start snapping to real energy onsets (Whisper word
starts can drift ~0.3 s). Refuses to return collapsed timing.
"""
from __future__ import annotations

import difflib
import os
import re
import subprocess
from typing import Dict, List, Tuple

from .spec import Spec
from .timing import media_duration


class AlignError(RuntimeError):
    pass


def whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def align(spec: Spec, vo_path: str, model_name: str = "") -> Dict:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise AlignError("faster-whisper is not installed; pip install 'faster-whisper' "
                         "or build with --align scale")

    model_name = model_name or os.environ.get("WHISPER_MODEL", "small.en")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    prompt = " ".join(b.spoken or b.text for b in spec.beats)
    segs, _ = model.transcribe(vo_path, word_timestamps=True, beam_size=5, temperature=0.0,
                               condition_on_previous_text=False, initial_prompt=prompt)
    heard = [(w.word, w.start, w.end) for s in segs for w in s.words]
    if not heard:
        raise AlignError(f"no speech found in {vo_path}")
    heard_norm = [_norm(w) for w, _, _ in heard]

    words: List[Tuple[int, int, str]] = [(li, wi, w) for li, b in enumerate(spec.beats)
                                         for wi, w in enumerate(b.words)]

    def match_pass(expand: bool) -> Dict[Tuple[int, int], Tuple[float, float]]:
        toks = []
        for li, wi, w in words:
            parts = spec.spoken.get(w, w).split() if expand else [w]
            for p in parts:
                toks.append((li, wi, _norm(p)))
        sm = difflib.SequenceMatcher(None, [t[2] for t in toks], heard_norm, autojunk=False)
        got: Dict[Tuple[int, int], Tuple[float, float]] = {}
        for a0, b0, n in sm.get_matching_blocks():
            for k in range(n):
                key = toks[a0 + k][:2]
                s_, e_ = heard[b0 + k][1], heard[b0 + k][2]
                if key in got:
                    got[key] = (min(got[key][0], s_), max(got[key][1], e_))
                else:
                    got[key] = (s_, e_)
        return got

    g1, g2 = match_pass(False), match_pass(True)
    wtime: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for li, wi, _ in words:
        if (li, wi) in g1:
            wtime[(li, wi)] = g1[(li, wi)]
        elif (li, wi) in g2:
            wtime[(li, wi)] = g2[(li, wi)]
    matched = len(wtime)

    # interpolate unmatched words between matched neighbours
    keys = [(li, wi) for li, wi, _ in words]
    for i, k in enumerate(keys):
        if k in wtime:
            continue
        pi = next((j for j in range(i - 1, -1, -1) if keys[j] in wtime), None)
        ni = next((j for j in range(i + 1, len(keys)) if keys[j] in wtime), None)
        a = wtime[keys[pi]][1] if pi is not None else 0.0
        b = wtime[keys[ni]][0] if ni is not None else a + 0.4
        span = (ni if ni is not None else i + 1) - (pi if pi is not None else -1)
        pos = i - (pi if pi is not None else -1)
        if span > 1:
            wtime[k] = (a + (b - a) * (pos - 1) / (span - 1), a + (b - a) * pos / (span - 1))
        else:
            wtime[k] = (a, b)

    # snap phrase-initial words (after punctuation) to the real energy onset
    log = subprocess.run(["ffmpeg", "-i", vo_path, "-af", "silencedetect=noise=-40dB:d=0.12",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    onsets = [float(v) for v in re.findall(r"silence_end: ([\d.]+)", log)]
    snapped = 0
    for i, (li, wi, w) in enumerate(words):
        if i == 0 or not onsets or not words[i - 1][2].endswith((".", ",", ":", "?", "!")):
            continue
        s0, e0 = wtime[(li, wi)]
        o = min(onsets, key=lambda x: abs(x - s0))
        if abs(o - s0) <= 0.45:
            wtime[(li, wi)] = (o, max(e0, o + 0.1))
            snapped += 1

    dur = media_duration(vo_path)
    lines = []
    for li, beat in enumerate(spec.beats):
        ws = []
        for wi, w in enumerate(beat.words):
            s_, e_ = wtime[(li, wi)]
            ws.append({"w": w, "s": round(s_, 3), "e": round(e_, 3)})
        lines.append({"id": beat.id, "s": ws[0]["s"], "e": ws[-1]["e"], "words": ws})

    missing = [w for li, wi, w in words if (li, wi) not in g1 and (li, wi) not in g2]
    tm = {"source": "vo:" + os.path.basename(vo_path),
          "duration": round(max(dur, lines[-1]["e"]) + spec.output.tail, 3),
          "lines": lines, "match_ratio": round(matched / len(keys), 3), "unmatched": missing,
          "snapped_onsets": snapped}

    bad = [l["id"] for l in lines if l["e"] - l["s"] < 0.15 * len(l["words"])]
    if bad:
        raise AlignError(f"alignment collapsed for beats {bad} — does the VO read the "
                         "script in the spec?")
    return tm
