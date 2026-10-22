"""Audio mix: original code-synthesised SFX bed keyed to the cut list, an optional
music bed (user-supplied, looped + gained), and the VO on top with ducking."""
from __future__ import annotations

import os
import subprocess
import wave
from typing import Dict, Optional

import numpy as np

from .render import shot_rows
from .spec import Spec

SR = 48000


def _decode(path: str, n: Optional[int] = None) -> np.ndarray:
    raw = subprocess.check_output(["ffmpeg", "-loglevel", "error", "-i", path,
                                   "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"])
    x = np.frombuffer(raw, np.float32).copy()
    if n is not None:
        if len(x) < n:
            reps = int(np.ceil(n / max(1, len(x))))
            x = np.tile(x, reps)
        x = x[:n]
    return x


def write_wav(x: np.ndarray, path: str) -> None:
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def build_mix(spec: Spec, tm: Dict, out_path: str, vo_path: str = "") -> str:
    dur = tm["duration"]
    n = int(dur * SR) + SR
    rng = np.random.default_rng(1)
    bed = np.zeros(n, np.float32)

    def bandnoise(m, lo, hi):
        if m < 16:
            return np.zeros(max(m, 0), np.float32)
        x = rng.normal(0, 1, m).astype(np.float32)
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(m, 1 / SR)
        X[(f < lo) | (f > hi)] = 0
        y = np.fft.irfft(X, m).astype(np.float32)
        return y / (np.abs(y).max() + 1e-9)

    def add(sig, t, g=1.0):
        i = int(t * SR)
        j = min(n, i + len(sig))
        if j > i:
            bed[i:j] += sig[:j - i] * g

    def env(m, a, r):
        e = np.ones(m, np.float32)
        ai, ri = int(a * SR), int(r * SR)
        if ai:
            e[:ai] = np.linspace(0, 1, ai)
        if ri:
            e[-ri:] *= np.linspace(1, 0, ri) ** 2
        return e

    def whoosh(d=0.45):
        m = int(d * SR)
        x = bandnoise(m, 300, 6000)
        tt = np.linspace(0, 1, m)
        return x * np.sin(np.pi * tt) ** 2 * 0.5

    def impact(d=1.2):
        m = int(d * SR)
        tt = np.arange(m) / SR
        f = 48 + 40 * np.exp(-tt * 8)
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 3.2)
                + bandnoise(m, 60, 2000) * np.exp(-tt * 25) * 0.4).astype(np.float32)

    def tick():
        m = int(0.018 * SR)
        tt = np.arange(m) / SR
        return (np.sin(2 * np.pi * 2400 * tt) * np.exp(-tt * 300)).astype(np.float32)

    if spec.audio.sfx:
        tt = np.arange(n) / SR
        drone = (np.sin(2 * np.pi * 55 * tt) + 0.6 * np.sin(2 * np.pi * 82.4 * tt + 1)
                 + 0.3 * np.sin(2 * np.pi * 110.2 * tt)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt))
        drone = drone * 0.05 + bandnoise(n, 40, 400) * 0.03
        bed += (drone * env(n, 1.0, 2.0)).astype(np.float32)

        rows = shot_rows(spec, tm)
        add(impact(), 0.0, 0.9)
        for si, s, e, tr in rows:
            shot = spec.shots[si]
            if tr == "whip":
                add(whoosh(), max(0, s - 0.15), 0.55)
            if tr == "zoom":
                add(whoosh(0.3), max(0, s - 0.08), 0.35)
            if shot.type in ("counter", "gauge", "bars", "list"):
                for k in range(int((e - s) * 12)):
                    if k % 2 == 0:
                        add(tick(), s + 0.15 + k / 12, 0.18)
            if shot.type in ("end", "title") and si != 0:
                add(impact(1.5), s, 0.6)
            for p in shot.punches:
                w0 = tm["lines"][p.beat]["words"]
                pt = w0[min(p.word, len(w0) - 1)]["s"]
                add(whoosh(0.18), max(0, pt - 0.1), 0.16)

    if spec.audio.music:
        music = _decode(spec.path(spec.audio.music), n)
        gain = 10 ** (spec.audio.music_gain_db / 20)
        bed += music * gain * env(n, 0.5, 2.0)

    sfx = bed[:int(dur * SR)]

    if vo_path and os.path.exists(vo_path):
        vo = _decode(vo_path)
        vo = vo[:len(sfx)]
        vo = np.pad(vo, (0, len(sfx) - len(vo)))
        # duck the bed about -15 dB under the voice, further while words are spoken
        k = int(0.08 * SR)
        envv = np.convolve(np.abs(vo), np.ones(k) / k, "same")
        envv = envv / (envv.max() + 1e-9)
        duck = 1 - 0.7 * np.clip(envv / 0.08, 0, 1)
        mixd = vo / (np.abs(vo).max() + 1e-9) * 0.9 + sfx * duck * 0.32
    else:
        mixd = sfx * 0.8

    write_wav(mixd / max(1.0, np.abs(mixd).max() / 0.95), out_path)
    return out_path
