"""Shortens silent gaps in a VO to max_gap seconds by removing silent samples only.
Voice samples are never stretched, sped up or filtered; 12 ms crossfades sit fully
inside the removed silence."""
from __future__ import annotations

import json
import re
import subprocess
import wave
from typing import Dict

import numpy as np

SR = 48000
THRESH_DB = -40


def tighten(src: str, dst: str, max_gap: float = 0.38, edits_json: str = "") -> Dict:
    min_sil = max_gap + 0.04
    xf = int(0.012 * SR)
    raw = subprocess.check_output(["ffmpeg", "-loglevel", "error", "-i", src,
                                   "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"])
    x = np.frombuffer(raw, np.float32).copy()
    log = subprocess.run(["ffmpeg", "-i", src, "-af",
                          f"silencedetect=noise={THRESH_DB}dB:d={min_sil}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(v) for v in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(v) for v in re.findall(r"silence_end: ([\d.]+)", log)]
    cuts = []
    for s, e in zip(starts, ends):
        if s < 0.05 or e > len(x) / SR - 0.05:   # leave the head and tail alone
            continue
        excess = (e - s) - max_gap
        if excess <= 0.02:
            continue
        mid = (s + e) / 2
        cuts.append((mid - excess / 2, mid + excess / 2))

    out = []
    pos = 0
    for a, b in cuts:
        ia, ib = int(a * SR), int(b * SR)
        seg = x[pos:ia].copy()
        if out and len(seg) > xf:
            fade = np.linspace(0, 1, xf, dtype=np.float32)
            out[-1][-xf:] = out[-1][-xf:] * (1 - fade) + seg[:xf] * fade
            seg = seg[xf:]
        out.append(seg)
        pos = ib
    seg = x[pos:].copy()
    if out and len(seg) > xf:
        fade = np.linspace(0, 1, xf, dtype=np.float32)
        out[-1][-xf:] = out[-1][-xf:] * (1 - fade) + seg[:xf] * fade
        seg = seg[xf:]
    out.append(seg)
    y = np.concatenate(out) if out else x

    with wave.open(dst, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())

    report = {"source": src, "max_gap": max_gap, "threshold_db": THRESH_DB,
              "removed_s": round(sum(b - a for a, b in cuts), 3),
              "cuts": [[round(a, 3), round(b, 3)] for a, b in cuts],
              "in_s": round(len(x) / SR, 3), "out_s": round(len(y) / SR, 3)}
    if edits_json:
        with open(edits_json, "w") as f:
            json.dump(report, f, indent=1)
    return report
