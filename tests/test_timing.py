import subprocess

import numpy as np
import pytest

from explainer.timing import estimate, media_duration, scale_to_vo


def test_estimate_monotonic(tiny_spec):
    tm = estimate(tiny_spec)
    assert tm["source"] == "estimate"
    assert tm["duration"] > 0
    last = -1.0
    for line in tm["lines"]:
        for w in line["words"]:
            assert w["s"] >= last
            assert w["e"] >= w["s"]
            last = w["s"]
    assert tm["duration"] > tm["lines"][-1]["e"]


def test_estimate_word_count_matches_beats(tiny_spec):
    tm = estimate(tiny_spec)
    for beat, line in zip(tiny_spec.beats, tm["lines"]):
        assert [w["w"] for w in line["words"]] == beat.words


@pytest.fixture
def silent_vo(tmp_path):
    p = str(tmp_path / "vo.wav")
    sr = 48000
    t = np.arange(8 * sr) / sr
    x = (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(sr),
                    "-ac", "1", "-i", "-", p], input=x.tobytes(), check=True)
    return p


def test_scale_to_vo(tiny_spec, silent_vo):
    tm = scale_to_vo(tiny_spec, silent_vo)
    dur = media_duration(silent_vo)
    assert abs(tm["duration"] - (dur + tiny_spec.output.tail)) < 0.05
    # last word should end just before the VO does
    assert tm["lines"][-1]["e"] <= dur
    assert tm["lines"][-1]["e"] > dur - 0.5
