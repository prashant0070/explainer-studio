import subprocess

import numpy as np

from explainer.tighten import tighten

SR = 48000


def _make_vo(path, segments):
    """segments: list of (kind, seconds) where kind is 'tone' or 'silence'."""
    parts = []
    for kind, dur in segments:
        n = int(dur * SR)
        if kind == "tone":
            t = np.arange(n) / SR
            parts.append((0.4 * np.sin(2 * np.pi * 300 * t)).astype(np.float32))
        else:
            parts.append(np.zeros(n, np.float32))
    x = np.concatenate(parts)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR),
                    "-ac", "1", "-i", "-", path], input=x.tobytes(), check=True)
    return len(x) / SR


def test_tighten_shortens_long_gaps(tmp_path):
    src = str(tmp_path / "vo.wav")
    dst = str(tmp_path / "tight.wav")
    total = _make_vo(src, [("tone", 1.0), ("silence", 1.5), ("tone", 1.0),
                           ("silence", 0.2), ("tone", 1.0)])
    rep = tighten(src, dst, max_gap=0.38, edits_json=str(tmp_path / "edits.json"))
    assert rep["in_s"] == round(total, 3)
    assert len(rep["cuts"]) == 1                      # only the 1.5 s gap is cut
    assert abs(rep["removed_s"] - (1.5 - 0.38)) < 0.1
    assert abs(rep["out_s"] - (total - rep["removed_s"])) < 0.05


def test_tighten_preserves_speech_duration(tmp_path):
    src = str(tmp_path / "vo.wav")
    dst = str(tmp_path / "tight.wav")
    _make_vo(src, [("tone", 1.0), ("silence", 2.0), ("tone", 1.0)])
    rep = tighten(src, dst, max_gap=0.38)
    # 2 s of tone must survive intact (plus the kept 0.38 s gap and head/tail padding)
    assert rep["out_s"] >= 2.0 + 0.38 - 0.05


def test_tighten_no_gaps_is_noop(tmp_path):
    src = str(tmp_path / "vo.wav")
    dst = str(tmp_path / "tight.wav")
    total = _make_vo(src, [("tone", 2.0)])
    rep = tighten(src, dst, max_gap=0.38)
    assert rep["cuts"] == []
    assert abs(rep["out_s"] - total) < 0.05
