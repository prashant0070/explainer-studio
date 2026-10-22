import copy

from explainer.qa import caption_overflow, shot_reuse
from explainer.timing import estimate


def test_no_reuse_in_examples(tiny_spec, mars_spec):
    assert shot_reuse(tiny_spec) == []
    assert shot_reuse(mars_spec) == []


def test_shot_reuse_detects_duplicates(tiny_spec):
    dup = copy.deepcopy(tiny_spec.shots[1])
    tiny_spec.shots.append(dup)
    flagged = shot_reuse(tiny_spec)
    assert len(flagged) == 1
    assert "card" in flagged[0]


def test_caption_overflow_flags_monster_chunk(tiny_spec):
    tm = estimate(tiny_spec)
    # graft an absurdly wide one-word caption chunk into the timing
    tm["lines"][0]["words"][:0] = [{"w": "EXTRAORDINARILYUNBREAKABLEWORD", "s": 0.0, "e": 0.1}]
    over = caption_overflow(tiny_spec, tm)
    assert any(o["hard"] for o in over)


def test_normal_captions_do_not_hard_overflow(mars_spec):
    tm = estimate(mars_spec)
    assert all(not o["hard"] for o in caption_overflow(mars_spec, tm))
