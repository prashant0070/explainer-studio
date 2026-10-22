import pytest

from explainer.spec import SpecError, load_spec


def test_tiny_spec_loads(tiny_spec):
    assert tiny_spec.title == "Tiny Test Project"
    assert len(tiny_spec.beats) == 2
    assert len(tiny_spec.shots) == 9
    assert tiny_spec.shots[0].type == "title"
    assert tiny_spec.shots[2].punches[0].zoom == 1.15


def test_mars_example_loads(mars_spec):
    assert mars_spec.slug == "mars-100-days"
    assert len(mars_spec.beats) == 8
    assert mars_spec.banner and mars_spec.banner.pill == "PART 1"
    assert mars_spec.timeline and len(mars_spec.timeline.labels) == 6


def test_auto_card_animations_do_not_repeat(mars_spec):
    anims = [s.params["animation"] for s in mars_spec.shots if s.type == "card"]
    assert len(anims) == len(set(anims)), f"card animations repeat: {anims}"


def _write(tmp_path, body):
    p = tmp_path / "bad.yaml"
    p.write_text(body)
    return str(p)


def test_rejects_unknown_shot_type(tmp_path):
    p = _write(tmp_path, """
title: Bad
beats: [{id: b, text: "hello world"}]
shots: [{type: nope, at: b.0}]
""")
    with pytest.raises(SpecError, match="unknown type"):
        load_spec(p)


def test_rejects_bad_anchor(tmp_path):
    p = _write(tmp_path, """
title: Bad
beats: [{id: b, text: "two words"}]
shots: [{type: title, at: b.9, title: X}]
""")
    with pytest.raises(SpecError, match="out of range"):
        load_spec(p)


def test_rejects_out_of_order_shots(tmp_path):
    p = _write(tmp_path, """
title: Bad
beats: [{id: b, text: "one two three four"}]
shots:
  - {type: title, at: b.0, title: X}
  - {type: end, at: b.3, title: Y}
  - {type: stat, at: b.1, value: Z}
""")
    with pytest.raises(SpecError, match="chronological"):
        load_spec(p)
