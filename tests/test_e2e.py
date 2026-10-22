"""End-to-end CLI build on the tiny project with a synthetic VO fixture.
Uses --align scale so it runs without faster-whisper or model downloads."""
import json
import os
import subprocess

import numpy as np
import pytest

from explainer.cli import main

SR = 48000


@pytest.fixture
def synth_vo(tmp_path):
    """Speech-shaped noise bursts with pauses — enough for tighten + scale timing."""
    rng = np.random.default_rng(42)
    parts = []
    for _ in range(6):
        n = int(0.9 * SR)
        burst = (rng.normal(0, 0.15, n) * np.hanning(n)).astype(np.float32)
        parts += [burst, np.zeros(int(0.5 * SR), np.float32)]
    x = np.concatenate(parts)
    p = str(tmp_path / "vo.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR),
                    "-ac", "1", "-i", "-", p], input=x.tobytes(), check=True)
    return p


def test_build_end_to_end(tiny_spec_path, synth_vo, tmp_path):
    out = str(tmp_path / "out")
    rc = main(["build", tiny_spec_path, "--vo", synth_vo, "--align", "scale",
               "--placeholders", "--out-dir", out, "--workers", "2", "--sheet-frames", "6"])
    assert rc == 0

    master = os.path.join(out, "tiny.mp4")
    share = os.path.join(out, "tiny-share.mp4")
    sheet = os.path.join(out, "tiny-sheet.jpg")
    qa = os.path.join(out, "tiny-qa.json")
    for p in (master, share, sheet, qa):
        assert os.path.exists(p), f"missing output {p}"

    with open(qa) as f:
        report = json.load(f)
    assert report["master"]["width"] == 1080 and report["master"]["height"] == 1920
    assert report["share"]["width"] == 720 and report["share"]["height"] == 1280
    assert report["share"]["profile"] == "Main"
    assert report["share"]["pix_fmt"] == "yuv420p"
    assert report["share"]["mb_per_min"] < 9
    assert report["shots"]["reused"] == []
    assert abs(report["loudness"]["integrated_lufs"] - (-14.0)) < 1.5
    # faststart: moov atom before mdat
    head = open(master, "rb").read(64 * 1024)
    assert head.find(b"moov") != -1 and head.find(b"moov") < head.find(b"mdat")


def test_build_no_vo_demo(tiny_spec_path, tmp_path):
    out = str(tmp_path / "out")
    rc = main(["build", tiny_spec_path, "--no-vo", "--placeholders", "--out-dir", out,
               "--workers", "2", "--sheet-frames", "4"])
    assert rc == 0
    assert os.path.exists(os.path.join(out, "tiny-demo.mp4"))
    assert os.path.exists(os.path.join(out, "tiny-demo-share.mp4"))
