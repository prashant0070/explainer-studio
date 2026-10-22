"""Loudness normalisation (two-pass loudnorm to -14 LUFS / -1.5 dBTP + peak
limiter make-up), mux, and the phone-friendly 720x1280 share encode."""
from __future__ import annotations

import json
import os
import subprocess
from typing import Dict, Tuple


def _run(*cmd: str) -> None:
    subprocess.run(list(cmd), check=True)


def measure_loudness(path: str) -> Dict[str, float]:
    err = subprocess.run(["ffmpeg", "-i", path, "-af", "loudnorm=print_format=json",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    return {"integrated_lufs": float(m["input_i"]), "true_peak_dbtp": float(m["input_tp"]),
            "lra": float(m["input_lra"])}


def normalize(mix_wav: str, out_wav: str, target_i: float = -14.0,
              target_tp: float = -1.5) -> float:
    """Two-pass linear loudnorm, then make-up gain through a peak limiter
    (VO dynamics untouched below the ceiling). Returns the make-up gain in dB."""
    work = out_wav + ".pass1.wav"
    meas = subprocess.run(
        ["ffmpeg", "-i", mix_wav, "-af",
         f"loudnorm=I={target_i}:TP={target_tp}:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = (f"loudnorm=I={target_i}:TP={target_tp}:LRA=11:measured_I={m['input_i']}:"
          f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    _run("ffmpeg", "-y", "-loglevel", "error", "-i", mix_wav, "-af", ln, "-ar", "48000", work)
    total_gain = 0.0
    cur = work
    for i in range(3):   # the limiter eats some gain; iterate until within 0.3 dB
        chk = subprocess.run(["ffmpeg", "-i", cur, "-af", "loudnorm=print_format=json",
                              "-f", "null", "-"], capture_output=True, text=True).stderr
        gi = float(json.loads(chk[chk.rindex("{"):chk.rindex("}") + 1])["input_i"])
        gain = round(target_i - gi, 2)
        if i > 0 and abs(gain) < 0.3:
            os.replace(cur, out_wav)
            break
        nxt = out_wav if i == 2 else out_wav + f".pass{i + 2}.wav"
        _run("ffmpeg", "-y", "-loglevel", "error", "-i", cur, "-af",
             f"volume={gain}dB,alimiter=limit=0.84:attack=3:release=60:level=disabled",
             "-ar", "48000", nxt)
        if cur != work:
            os.remove(cur)
        total_gain += gain
        cur = nxt
    else:
        if cur != out_wav:
            os.replace(cur, out_wav)
    if os.path.exists(work):
        os.remove(work)
    return round(total_gain, 2)


def mux(video: str, audio: str, out: str) -> None:
    _run("ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", audio,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", out)


def share_encode(master: str, out: str, bitrate_k: int = 700,
                 passlog_prefix: str = "") -> Tuple[str, float]:
    """720x1280, H.264 Main L3.1, yuv420p, two-pass, faststart — opens on any phone."""
    passlog = passlog_prefix or (out + ".x264pass")
    for ps in (1, 2):
        _run("ffmpeg", "-y", "-loglevel", "error", "-i", master,
             "-vf", "scale=720:1280:flags=lanczos",
             "-c:v", "libx264", "-profile:v", "main", "-level", "3.1",
             "-pix_fmt", "yuv420p", "-b:v", f"{bitrate_k}k",
             "-maxrate", f"{int(bitrate_k * 1.43)}k", "-bufsize", f"{bitrate_k * 2}k",
             "-pass", str(ps), "-passlogfile", passlog,
             *(["-an", "-f", "mp4", "/dev/null"] if ps == 1 else
               ["-c:a", "aac", "-b:a", "96k", "-ac", "2", "-movflags", "+faststart", out]))
    for ext in ("-0.log", "-0.log.mbtree"):
        p = passlog + ext
        if os.path.exists(p):
            os.remove(p)
    return out, round(os.path.getsize(out) / 1e6, 2)
