"""Frame renderer: shot timeline anchored to word timings, hard punch-ins on
spoken words, word-synced karaoke captions, banner/timeline overlays, transitions,
grade and grain. Streams raw frames into ffmpeg/libx264."""
from __future__ import annotations

import multiprocessing as mp
import os
import subprocess
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

from . import H, W
from .draw import Ctx, cl, eback, eo, lerp, rect, txt
from .shots import SHOT_FNS, _color
from .spec import Spec

BAND = (386, 1322)   # punch-ins only affect this content band (never banner or captions)

_G: Dict = {}


def wt(li: int, wi: int) -> float:
    ws = _G["tm"]["lines"][li]["words"]
    return ws[min(wi, len(ws) - 1)]["s"]


def shot_rows(spec: Spec, tm: Dict) -> List[Tuple[int, float, float, str]]:
    """[(shot index, start, end, transition)] — every cut lands 0.06 s before its word."""
    rows = []
    for i, s in enumerate(spec.shots):
        ws = tm["lines"][s.beat]["words"]
        start = 0.0 if i == 0 else max(0.0, ws[min(s.word, len(ws) - 1)]["s"] - 0.06)
        rows.append([i, start, 0.0, s.transition])
    for i in range(len(rows)):
        rows[i][2] = rows[i + 1][1] if i + 1 < len(rows) else tm["duration"]
    return [tuple(r) for r in rows]  # type: ignore[return-value]


def caption_chunks(tm: Dict) -> List[List[Tuple[str, float, float]]]:
    out: List[List[Tuple[str, float, float]]] = []
    for line in tm["lines"]:
        cur: List[Tuple[str, float, float]] = []
        ln = 0
        for wi, w in enumerate(line["words"]):
            cur.append((w["w"], w["s"], w["e"]))
            ln += len(w["w"]) + 1
            if ln > 15 or w["w"].endswith((".", ",", ":", "?", "!")) or wi == len(line["words"]) - 1:
                out.append(cur)
                cur = []
                ln = 0
    return out


def init_render(spec: Spec, tm: Dict, placeholders: bool = False) -> None:
    ctx = Ctx(spec.style, spec.path(spec.style.font_dir))
    _G.update(spec=spec, tm=tm, ctx=ctx, placeholders=placeholders,
              rows=shot_rows(spec, tm), chunks=caption_chunks(tm))
    # resolve image paths relative to the spec once
    for s in spec.shots:
        if s.type == "image":
            s.params["_abs_src"] = spec.path(str(s.params.get("src", "")))
    # timeline overlay: beat index of each marker
    tl = spec.timeline
    _G["tl_starts"] = ([tm["lines"][spec.beat_index(b)]["s"] for b in tl.beats] if tl else [])


def _punch_framing(shot, t: float) -> Tuple[float, float, float]:
    z, fx, fy, t0 = 1.0, W / 2, 820.0, -9.0
    pz, pfx, pfy = 1.0, W / 2, 820.0
    for p in shot.punches:
        bt = wt(p.beat, p.word) - 0.04
        if t >= bt:
            pz, pfx, pfy = z, fx, fy
            z, fx, fy, t0 = p.zoom, p.focus[0] * W, p.focus[1] * H, bt
    k = eo((t - t0) / 0.1)
    return lerp(pz, z, k), lerp(pfx, fx, k), lerp(pfy, fy, k)


def _punch(ctx: Ctx, cv: Image.Image, z: float, fx: float, fy: float) -> Image.Image:
    if z <= 1.001:
        return cv
    cw, ch = W / z, H / z
    x0 = cl(fx - cw / 2, 0, W - cw)
    y0 = cl(fy - ch / 2, 0, H - ch)
    zz = cv.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    if "band" not in ctx.assets:
        y = np.arange(H, dtype=np.float32)
        m = np.clip((y - BAND[0]) / 40, 0, 1) * np.clip((BAND[1] - y) / 70, 0, 1)
        ctx.assets["band"] = Image.fromarray((np.repeat(m[:, None], W, 1) * 255).astype(np.uint8))
    return Image.composite(zz, cv, ctx.assets["band"])  # type: ignore[arg-type]


def _slam(ctx: Ctx, cv: Image.Image, shot, t: float) -> None:
    sl = shot.params.get("slam")
    if not sl:
        return
    spec: Spec = _G["spec"]
    bid, _, wi = str(sl.get("at", "")).rpartition(".")
    th = wt(spec.beat_index(bid), int(wi)) - 0.05
    if t < th:
        return
    k = eo((t - th) / 0.3)
    st = ctx.style
    rect(cv, (0, 400, W, 1260), (0, 0, 0), alpha=0.86 * k)
    lines = [str(x) for x in sl.get("lines", [])][:2]
    col = _color(ctx, sl.get("color"), st.accent)
    if lines:
        txt(cv, (W // 2, 760), lines[0].upper(), ctx.font("display", 150), st.text,
            alpha=k, scale=lerp(1.2, 1.0, k))
    if len(lines) > 1:
        txt(cv, (W // 2, 920), lines[1].upper(), ctx.font("display", 150), col,
            alpha=eo((t - th - 0.25) / 0.25))


def _credit(ctx: Ctx, cv: Image.Image, s: str, y: int = 1290) -> None:
    size = 30
    f = ctx.font("condsemi", size)
    while f.getlength(s) > 860 and size > 22:
        size -= 1
        f = ctx.font("condsemi", size)
    w_ = f.getlength(s)
    rect(cv, (48, y - 22, 48 + w_ + 24, y + 22), (0, 0, 0), alpha=0.62, r=10)
    txt(cv, (60, y), s, f, (214, 214, 222), anchor="lm")


def _overlays(ctx: Ctx, cv: Image.Image, t: float) -> None:
    spec: Spec = _G["spec"]
    st = ctx.style
    if spec.banner and spec.banner.lines:
        d = ImageDraw.Draw(cv)
        d.rectangle((0, 118, W, 318), fill=(0, 0, 0))
        d.rectangle((0, 112, W, 312), fill=st.accent2)
        lines = spec.banner.lines
        if len(lines) == 1:
            txt(cv, (W // 2, 212), lines[0].upper(), ctx.font("display", 74), st.text)
        else:
            txt(cv, (W // 2, 166), lines[0].upper(), ctx.font("display", 74), st.text)
            txt(cv, (W // 2, 256), lines[1].upper(), ctx.font("display", 74), st.text)
        if spec.banner.pill:
            pw = int(ctx.font("display", 38).getlength(spec.banner.pill)) + 60
            d.rounded_rectangle((40, 330, 40 + max(170, pw), 384), 12, fill=st.text)
            txt(cv, (40 + max(170, pw) // 2, 357), spec.banner.pill.upper(),
                ctx.font("display", 38), st.accent2)
    tl = spec.timeline
    if tl and tl.labels:
        starts = _G["tl_starts"]
        cur = -1
        for i, s0 in enumerate(starts):
            if t >= s0 - 0.1:
                cur = i
        d = ImageDraw.Draw(cv)
        x0, x1, y = 300, 1030, 357
        n = len(tl.labels)
        d.line((x0, y, x1, y), fill=(80, 80, 90), width=4)
        for i in range(n):
            x = lerp(x0, x1, i / max(1, n - 1))
            on = i <= cur
            if on and i > 0:
                d.line((lerp(x0, x1, (i - 1) / max(1, n - 1)), y, x, y), fill=st.accent, width=6)
            r = 13 if i == cur else 9
            d.ellipse((x - r, y - r, x + r, y + r), fill=st.accent if on else (80, 80, 90))
        for i, lab in enumerate(tl.labels):
            x = lerp(x0, x1, i / max(1, n - 1))
            txt(cv, (x, y - 30), lab, ctx.font("mono", 22), st.text if i == cur else st.muted)


def _captions(ctx: Ctx, cv: Image.Image, t: float) -> None:
    spec: Spec = _G["spec"]
    cc = spec.captions
    if not cc.enabled:
        return
    chunks = _G["chunks"]
    act = None
    dur = _G["tm"]["duration"]
    for i, c in enumerate(chunks):
        nxt = chunks[i + 1][0][1] if i + 1 < len(chunks) else dur
        if c[0][1] - 0.05 <= t < min(nxt, c[-1][2] + 0.6):
            act = c
    if not act:
        return
    st = ctx.style
    f = ctx.font("display", cc.size)
    words = [w for w, _, _ in act]
    shown = [w.upper() if cc.uppercase else w for w in words]
    widths = [f.getlength(w + " ") for w in shown]
    tw = sum(widths) - f.getlength(" ")
    pop = lerp(1.12, 1.0, eo((t - act[0][1]) / 0.12))
    lay = Image.new("RGBA", (int(tw) + 40, cc.size + 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x = 20
    for (w_, s_, _), disp, wd in zip(act, shown, widths):
        col = st.highlight if s_ - 0.03 <= t else st.text
        d.text((x, 20), disp, font=f, fill=col + (255,), stroke_width=8, stroke_fill=(0, 0, 0, 255))
        x += wd
    if pop != 1:
        lay = lay.resize((int(lay.width * pop), int(lay.height * pop)), Image.BICUBIC)
    if lay.width > cc.safe_width:
        lay = lay.resize((cc.safe_width, int(lay.height * cc.safe_width / lay.width)), Image.BICUBIC)
    cv.alpha_composite(lay, (cc.x - lay.width // 2, cc.y - lay.height // 2))


def frame(fi: int) -> bytes:
    spec: Spec = _G["spec"]
    ctx: Ctx = _G["ctx"]
    fps = spec.output.fps
    t = fi / fps
    rows = _G["rows"]
    si, s, e, tr = rows[-1]
    for si, s, e, tr in rows:
        if s <= t < e:
            break
    shot = spec.shots[si]
    lt, d = t - s, e - s
    fn = SHOT_FNS[shot.type]
    if shot.type == "image":
        cv = fn(ctx, shot.params, t, lt, d, placeholders=_G["placeholders"]).convert("RGBA")
    else:
        cv = fn(ctx, shot.params, t, lt, d).convert("RGBA")
    cv = _punch(ctx, cv, *_punch_framing(shot, t))
    _slam(ctx, cv, shot, t)
    if shot.credit:
        _credit(ctx, cv, shot.credit)
    if tr == "whip" and lt < 0.2:
        k = 1 - eo(lt / 0.2)
        off = int(k * W * 0.22)
        sm = cv.resize((W // 24, H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
        cv = Image.blend(cv, sm, k * 0.6)
        cv = cv.transform(cv.size, Image.AFFINE, (1, 0, -off, 0, 1, 0),
                          fillcolor=spec.style.bg + (255,))
    elif tr == "zoom" and lt < 0.22:
        z = lerp(1.12, 1.0, eo(lt / 0.22))
        big = cv.resize((int(W * z), int(H * z)), Image.BILINEAR)
        cv = big.crop(((big.width - W) // 2, (big.height - H) // 2,
                       (big.width - W) // 2 + W, (big.height - H) // 2 + H))
    _overlays(ctx, cv, t)
    _captions(ctx, cv, t)
    arr = np.asarray(cv.convert("RGB")).astype(np.float32) / 255
    arr = arr * ctx.vignette()
    if spec.style.grain > 0:
        arr = arr + ctx.grain()[fi % 6] * spec.style.grain
    arr = np.clip((arr - 0.5) * 1.04 + 0.5, 0, 1)
    return (arr * 255).astype(np.uint8).tobytes()


def render_video(spec: Spec, tm: Dict, out_path: str, placeholders: bool = False,
                 workers: Optional[int] = None, log=print) -> None:
    init_render(spec, tm, placeholders)
    fps = spec.output.fps
    n = int(tm["duration"] * fps)
    workers = workers or min(6, os.cpu_count() or 1)
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", str(spec.output.crf),
         "-pix_fmt", "yuv420p", out_path], stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        ctxm = mp.get_context("fork")
    except ValueError:
        ctxm = mp.get_context()
    if workers > 1:
        with ctxm.Pool(workers) as pool:
            for i, b in enumerate(pool.imap(frame, range(n), chunksize=4)):
                proc.stdin.write(b)
                if i % 150 == 0:
                    log(f"  frame {i}/{n}")
    else:
        for i in range(n):
            proc.stdin.write(frame(i))
            if i % 150 == 0:
                log(f"  frame {i}/{n}")
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg video encode failed")


def render_stills(spec: Spec, tm: Dict, frames: List[int], out_dir: str,
                  placeholders: bool = False) -> List[str]:
    init_render(spec, tm, placeholders)
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for fi in frames:
        p = os.path.join(out_dir, f"f{fi:05d}.png")
        Image.frombytes("RGB", (W, H), frame(fi)).save(p)
        paths.append(p)
    return paths
