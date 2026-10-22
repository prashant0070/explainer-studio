import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TINY_YAML = textwrap.dedent("""\
    title: "Tiny Test Project"
    slug: tiny
    style:
      font_dir: {fonts}
    banner:
      lines: ["TEST SERIES", "TINY PROJECT"]
      pill: "PART 1"
    timeline:
      labels: ["1", "2"]
      beats: [b1, b2]
    output:
      fps: 10
      share: true
    spoken:
      "100": one hundred
    beats:
      - id: b1
        text: "Day 1. A number card and a counter, with 100 units of data."
      - id: b2
        text: "Day 2. Bars, a list, a gauge, a still, a stat, then the end."
    shots:
      - {{ type: title, at: b1.0, title: "100", subtitle: "TINY TEST", kicker: "A KICKER" }}
      - {{ type: card, at: b1.2, transition: whip, number: "1", label: "THE CARD" }}
      - type: counter
        at: b1.5
        from: 0
        to: 100
        unit: "%"
        label: "A COUNTER"
        punch:
          - {{ at: b1.9, zoom: 1.15, focus: [0.5, 0.45] }}
      - {{ type: bars, at: b2.0, transition: zoom, heading: "BARS",
           items: [{{label: A, value: 10, display: "10"}}, {{label: B, value: 3, display: "3"}}] }}
      - {{ type: list, at: b2.2, heading: "LIST",
           items: [{{label: ONE, value: "1"}}, {{label: TWO, value: "2"}}] }}
      - {{ type: gauge, at: b2.4, heading: "GAUGE", value: 38, max: 100, unit: "%" }}
      - {{ type: image, at: b2.6, src: missing-still.jpg, label: "A STILL" }}
      - type: stat
        at: b2.8
        value: "42%"
        label: "A STAT"
        slam:
          at: b2.11
          lines: ["SLAM!"]
      - {{ type: end, at: b2.12, transition: whip, pill: "PART 2", title: "THE END", sub: "BYE" }}
    """)


@pytest.fixture
def tiny_spec_path(tmp_path):
    p = tmp_path / "tiny.yaml"
    p.write_text(TINY_YAML.format(fonts=os.path.join(REPO, "fonts")))
    return str(p)


@pytest.fixture
def tiny_spec(tiny_spec_path):
    from explainer.spec import load_spec
    return load_spec(tiny_spec_path)


@pytest.fixture
def mars_spec():
    from explainer.spec import load_spec
    return load_spec(os.path.join(REPO, "examples", "mars", "project.yaml"))
