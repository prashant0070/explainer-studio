"""Word timing: no-VO estimate, VO-duration scaling, and timing.json I/O.

timing.json format (same shape as the reference build):
{"source": str, "duration": float,
 "lines": [{"id": str, "s": float, "e": float,
            "words": [{"w": str, "s": float, "e": float}]}]}
"""
from __future__ import annotations

import json
import subprocess
from typing import Dict, List

from .spec import Spec


def media_duration(path: str) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(out)


def spoken_form(spec: Spec, token: str) -> str:
    return spec.spoken.get(token, token.strip(".,:!?"))


def estimate(spec: Spec) -> Dict:
    """Estimated narration pacing when there is no VO (demo mode)."""
    t = 0.0
    lines: List[Dict] = []
    for beat in spec.beats:
        words = []
        for w in beat.text.split():
            sp = spoken_form(spec, w)
            d = 0.06 + 0.047 * len(sp)
            words.append({"w": w, "s": round(t, 3), "e": round(t + d, 3)})
            t += d
            if w.endswith((".", "?", "!")):
                t += 0.2
            elif w.endswith((",", ":", ";")):
                t += 0.08
        lines.append({"id": beat.id, "s": words[0]["s"], "e": round(t, 3), "words": words})
        t += 0.12
    return {"source": "estimate", "duration": round(t + spec.output.tail, 3), "lines": lines}


def scale_to_vo(spec: Spec, vo_path: str) -> Dict:
    """Estimated pacing stretched to the real VO duration (fallback when
    faster-whisper is unavailable). Cuts land close to, not on, the words."""
    tm = estimate(spec)
    vo_dur = media_duration(vo_path)
    last_e = tm["lines"][-1]["e"]
    k = max(0.2, (vo_dur - 0.15)) / max(last_e, 0.001)
    for line in tm["lines"]:
        line["s"] = round(line["s"] * k, 3)
        line["e"] = round(line["e"] * k, 3)
        for w in line["words"]:
            w["s"] = round(w["s"] * k, 3)
            w["e"] = round(w["e"] * k, 3)
    tm["source"] = f"scale:{vo_path}"
    tm["duration"] = round(vo_dur + spec.output.tail, 3)
    return tm


def save(tm: Dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(tm, f, indent=1)


def load(path: str) -> Dict:
    with open(path) as f:
        return json.load(f)
