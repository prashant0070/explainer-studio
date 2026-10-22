import numpy as np
from PIL import Image

from explainer import H, W
from explainer.render import caption_chunks, init_render, frame, shot_rows
from explainer.timing import estimate


def test_every_shot_type_renders_a_frame(tiny_spec, tmp_path):
    tm = estimate(tiny_spec)
    init_render(tiny_spec, tm, placeholders=True)
    rows = shot_rows(tiny_spec, tm)
    fps = tiny_spec.output.fps
    for (si, s, e, tr) in rows:
        mid = int((s + e) / 2 * fps)
        buf = frame(mid)
        im = Image.frombytes("RGB", (W, H), buf)
        arr = np.asarray(im)
        assert arr.shape == (H, W, 3)
        # frame must not be blank (background + content always has variance)
        assert arr.std() > 5, f"shot {si} ({tiny_spec.shots[si].type}) rendered blank"


def test_transition_frames_render(tiny_spec):
    tm = estimate(tiny_spec)
    init_render(tiny_spec, tm, placeholders=True)
    fps = tiny_spec.output.fps
    for (si, s, e, tr) in shot_rows(tiny_spec, tm):
        if tr in ("whip", "zoom"):
            frame(int(s * fps) + 1)   # must not raise


def test_shot_rows_cover_full_duration(tiny_spec):
    tm = estimate(tiny_spec)
    init_render(tiny_spec, tm, placeholders=True)
    rows = shot_rows(tiny_spec, tm)
    assert rows[0][1] == 0.0
    for (a, b) in zip(rows, rows[1:]):
        assert a[2] == b[1]           # contiguous
    assert rows[-1][2] == tm["duration"]


def test_caption_chunks_fit_word_budget(tiny_spec):
    tm = estimate(tiny_spec)
    for chunk in caption_chunks(tm):
        assert 1 <= len(chunk) <= 5
