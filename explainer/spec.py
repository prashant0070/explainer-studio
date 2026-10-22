"""Project spec loading and validation (YAML or JSON)."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import yaml

SHOT_TYPES = ("title", "card", "stat", "counter", "gauge", "bars", "list", "image", "end")
TRANSITIONS = ("cut", "whip", "zoom")
CARD_ANIMATIONS = ("rings", "slide", "glitch", "wipe", "bounce", "odometer")


class SpecError(ValueError):
    pass


def _color(v: Any, name: str) -> Tuple[int, int, int]:
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return tuple(int(c) for c in v)  # type: ignore[return-value]
    if isinstance(v, str):
        m = re.fullmatch(r"#?([0-9a-fA-F]{6})", v.strip())
        if m:
            h = m.group(1)
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    raise SpecError(f"{name}: expected a hex color like '#ec7634', got {v!r}")


@dataclass
class Style:
    bg: Tuple[int, int, int] = (9, 9, 13)
    accent: Tuple[int, int, int] = (236, 118, 52)
    accent2: Tuple[int, int, int] = (214, 34, 40)
    text: Tuple[int, int, int] = (245, 245, 245)
    muted: Tuple[int, int, int] = (150, 150, 160)
    highlight: Tuple[int, int, int] = (255, 176, 46)
    font_dir: str = "fonts"
    grain: float = 0.045
    grid: bool = True


@dataclass
class Captions:
    enabled: bool = True
    size: int = 92
    x: int = 510
    y: int = 1400
    safe_width: int = 900
    uppercase: bool = True


@dataclass
class Banner:
    lines: List[str] = field(default_factory=list)
    pill: str = ""


@dataclass
class Timeline:
    labels: List[str] = field(default_factory=list)
    beats: List[str] = field(default_factory=list)


@dataclass
class AudioCfg:
    sfx: bool = True
    music: Optional[str] = None
    music_gain_db: float = -18.0


@dataclass
class Output:
    fps: int = 30
    share: bool = True
    tail: float = 1.2
    crf: int = 18
    share_bitrate_k: int = 700


@dataclass
class Beat:
    id: str
    text: str
    spoken: str = ""

    @property
    def words(self) -> List[str]:
        return self.text.split()


@dataclass
class Punch:
    beat: int
    word: int
    zoom: float
    focus: Tuple[float, float]


@dataclass
class Shot:
    type: str
    beat: int
    word: int
    transition: str = "cut"
    credit: str = ""
    punches: List[Punch] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Spec:
    title: str
    slug: str
    base_dir: str
    style: Style
    captions: Captions
    banner: Optional[Banner]
    timeline: Optional[Timeline]
    audio: AudioCfg
    output: Output
    spoken: Dict[str, str]
    beats: List[Beat]
    shots: List[Shot]

    def beat_index(self, beat_id: str) -> int:
        for i, b in enumerate(self.beats):
            if b.id == beat_id:
                return i
        raise SpecError(f"unknown beat id {beat_id!r}")

    def path(self, rel: str) -> str:
        return rel if os.path.isabs(rel) else os.path.join(self.base_dir, rel)


def _parse_anchor(spec_beats: List[Beat], at: Any, ctx: str) -> Tuple[int, int]:
    if not isinstance(at, str) or "." not in at:
        raise SpecError(f"{ctx}: 'at' must look like 'beatid.wordindex', got {at!r}")
    bid, _, wi = at.rpartition(".")
    try:
        w = int(wi)
    except ValueError:
        raise SpecError(f"{ctx}: word index in {at!r} is not an integer")
    for i, b in enumerate(spec_beats):
        if b.id == bid:
            if not 0 <= w < len(b.words):
                raise SpecError(f"{ctx}: word index {w} out of range for beat {bid!r} "
                                f"({len(b.words)} words)")
            return i, w
    raise SpecError(f"{ctx}: unknown beat id {bid!r}")


def load_spec(path: str) -> Spec:
    with open(path) as f:
        raw = json.load(f) if path.endswith(".json") else yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise SpecError("spec root must be a mapping")

    title = raw.get("title") or ""
    if not title:
        raise SpecError("spec needs a 'title'")
    slug = raw.get("slug") or re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

    sd = raw.get("style", {}) or {}
    style = Style(
        bg=_color(sd.get("bg", "#09090d"), "style.bg"),
        accent=_color(sd.get("accent", "#ec7634"), "style.accent"),
        accent2=_color(sd.get("accent2", "#d62228"), "style.accent2"),
        text=_color(sd.get("text", "#f5f5f5"), "style.text"),
        muted=_color(sd.get("muted", "#96969f"), "style.muted"),
        highlight=_color(sd.get("highlight", "#ffb02e"), "style.highlight"),
        font_dir=sd.get("font_dir", "fonts"),
        grain=float(sd.get("grain", 0.045)),
        grid=bool(sd.get("grid", True)),
    )

    cd = raw.get("captions", {}) or {}
    captions = Captions(
        enabled=bool(cd.get("enabled", True)), size=int(cd.get("size", 92)),
        x=int(cd.get("x", 510)), y=int(cd.get("y", 1400)),
        safe_width=int(cd.get("safe_width", 900)), uppercase=bool(cd.get("uppercase", True)),
    )

    banner = None
    if raw.get("banner"):
        bd = raw["banner"]
        banner = Banner(lines=[str(x) for x in bd.get("lines", [])][:2], pill=str(bd.get("pill", "")))

    ad = raw.get("audio", {}) or {}
    audio = AudioCfg(sfx=bool(ad.get("sfx", True)), music=ad.get("music"),
                     music_gain_db=float(ad.get("music_gain_db", -18.0)))

    od = raw.get("output", {}) or {}
    output = Output(fps=int(od.get("fps", 30)), share=bool(od.get("share", True)),
                    tail=float(od.get("tail", 1.2)), crf=int(od.get("crf", 18)),
                    share_bitrate_k=int(od.get("share_bitrate_k", 700)))

    spoken = {str(k): str(v) for k, v in (raw.get("spoken") or {}).items()}

    beats: List[Beat] = []
    seen = set()
    for i, b in enumerate(raw.get("beats") or []):
        if not isinstance(b, dict) or not b.get("id") or not b.get("text"):
            raise SpecError(f"beats[{i}]: needs 'id' and 'text'")
        if b["id"] in seen:
            raise SpecError(f"beats[{i}]: duplicate id {b['id']!r}")
        seen.add(b["id"])
        beats.append(Beat(id=str(b["id"]), text=str(b["text"]), spoken=str(b.get("spoken", ""))))
    if not beats:
        raise SpecError("spec needs at least one beat")

    timeline = None
    if raw.get("timeline"):
        td = raw["timeline"]
        timeline = Timeline(labels=[str(x) for x in td.get("labels", [])],
                            beats=[str(x) for x in td.get("beats", [])])
        if len(timeline.labels) != len(timeline.beats):
            raise SpecError("timeline: 'labels' and 'beats' must have the same length")
        for bid in timeline.beats:
            if bid not in seen:
                raise SpecError(f"timeline: unknown beat id {bid!r}")

    shots: List[Shot] = []
    for i, s in enumerate(raw.get("shots") or []):
        ctx = f"shots[{i}]"
        if not isinstance(s, dict):
            raise SpecError(f"{ctx}: must be a mapping")
        stype = s.get("type")
        if stype not in SHOT_TYPES:
            raise SpecError(f"{ctx}: unknown type {stype!r} (expected one of {SHOT_TYPES})")
        tr = s.get("transition", "cut")
        if tr not in TRANSITIONS:
            raise SpecError(f"{ctx}: unknown transition {tr!r} (expected one of {TRANSITIONS})")
        bi, wi = _parse_anchor(beats, s.get("at"), ctx)
        punches = []
        for j, p in enumerate(s.get("punch") or []):
            pb, pw = _parse_anchor(beats, p.get("at"), f"{ctx}.punch[{j}]")
            focus = p.get("focus", [0.5, 0.45])
            punches.append(Punch(beat=pb, word=pw, zoom=float(p.get("zoom", 1.0)),
                                 focus=(float(focus[0]), float(focus[1]))))
        if stype == "card":
            anim = s.get("animation", "auto")
            if anim not in CARD_ANIMATIONS + ("auto",):
                raise SpecError(f"{ctx}: unknown card animation {anim!r}")
        params = {k: v for k, v in s.items()
                  if k not in ("type", "at", "transition", "credit", "punch")}
        shots.append(Shot(type=stype, beat=bi, word=wi, transition=tr,
                          credit=str(s.get("credit", "")), punches=punches, params=params))
    if not shots:
        raise SpecError("spec needs at least one shot")
    order = [(s.beat, s.word) for s in shots]
    if order != sorted(order):
        raise SpecError("shots must be listed in chronological order of their anchors")
    if shots[0].beat != 0 or shots[0].word != 0:
        raise SpecError("the first shot must be anchored at the first word of the first beat")

    spec = Spec(title=title, slug=slug, base_dir=os.path.dirname(os.path.abspath(path)),
                style=style, captions=captions, banner=banner, timeline=timeline,
                audio=audio, output=output, spoken=spoken, beats=beats, shots=shots)

    # resolve "auto" card animations into a non-repeating cycle
    cycle = list(CARD_ANIMATIONS)
    k = 0
    for s in spec.shots:
        if s.type == "card" and s.params.get("animation", "auto") == "auto":
            s.params["animation"] = cycle[k % len(cycle)]
            k += 1
    return spec
