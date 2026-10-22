"""Shot type implementations. Every shot is a code-drawn motion graphic on the
1080x1920 design canvas; `image` shots are user-supplied stills with Ken Burns."""
from __future__ import annotations

import math
import random
from typing import Any, Dict

import numpy as np
from PIL import Image, ImageDraw

from . import H, W
from .draw import (Ctx, cl, eback, eio, eo, ken_burns, lerp, mix, rect, txt)

CX = W // 2


def _color(ctx: Ctx, v: Any, default):
    if v is None:
        return default
    names = {"accent": ctx.style.accent, "accent2": ctx.style.accent2, "text": ctx.style.text,
             "muted": ctx.style.muted, "highlight": ctx.style.highlight,
             "blue": (70, 160, 255), "ice": (110, 200, 255), "green": (90, 220, 140)}
    if isinstance(v, str) and v in names:
        return names[v]
    if isinstance(v, str) and v.lstrip("#"):
        h = v.lstrip("#")
        if len(h) == 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return default


# ---------- title ----------
def title(ctx: Ctx, p: Dict, t, lt, d):
    st = ctx.style
    cv = ctx.base(drift=lt * 30)
    pulse = 0.5 + 0.5 * math.sin(lt * 8)
    rect(cv, (0, 380, W, 1300), mix(st.bg, st.accent2, 0.25), alpha=0.25 + 0.1 * pulse)
    big = str(p.get("title", ""))
    size = 520 if len(big) <= 3 else (380 if len(big) <= 5 else 240)
    s = lerp(1.45, 1.0, eback(lt / 0.28))
    shake = random.Random(int(lt * 30)).uniform(-6, 6) if lt < 0.25 else 0
    txt(cv, (CX + shake, 720), big, ctx.font("display", size), st.accent, scale=s)
    a2 = eo((lt - 0.15) / 0.25)
    txt(cv, (CX, 1040 + 40 * (1 - a2)), str(p.get("subtitle", "")).upper(),
        ctx.font("display", 150 if len(str(p.get("subtitle", ""))) <= 14 else 110), st.text, alpha=a2)
    a3 = eo((lt - 0.4) / 0.3)
    txt(cv, (CX, 1170), str(p.get("kicker", "")).upper(), ctx.font("cond", 62), st.highlight,
        alpha=a3, track=3)
    return cv


# ---------- card (six distinct animations) ----------
def _rays(ctx: Ctx, cv, lt, seed, n=4, col=(255, 120, 90)):
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    fr = int(lt * 30)
    for k in range(4):
        rg = random.Random(seed * 1000 + fr - k)
        for _ in range(n):
            x = rg.uniform(0, W)
            y = rg.uniform(380, 1250)
            ang = rg.uniform(1.0, 2.1)
            L = rg.uniform(80, 260)
            a = int(200 * (1 - k / 4))
            dr.line((x, y, x + L * math.cos(ang), y + L * math.sin(ang)), fill=col + (a,), width=3)
    cv.alpha_composite(lay)


def card(ctx: Ctx, p: Dict, t, lt, d):
    st = ctx.style
    num = str(p.get("number", ""))
    lab = str(p.get("label", "")).upper()
    kick = str(p.get("kicker", "DAY")).upper()
    anim = p.get("animation", "rings")
    big = ctx.font("display", 470 if len(num) < 3 else (400 if len(num) < 4 else 300))
    cv = ctx.base(drift=lt * 40)

    def common(canvas, numcol=st.accent, numxy=(CX, 860), numscale=1.0, numalpha=1.0,
               linecol=st.accent2, labdelay=0.15):
        txt(canvas, (CX, 560), kick, ctx.font("cond", 110), st.text, alpha=eo(lt / 0.2), track=18)
        lw = int(700 * eo((lt - 0.08) / 0.3))
        rect(canvas, (CX - lw // 2, 1075, CX + lw // 2, 1083), linecol)
        txt(canvas, (CX, 1150), lab, ctx.font("cond", 76), st.text,
            alpha=eo((lt - labdelay) / 0.25), track=10)
        txt(canvas, numxy, num, big, numcol, scale=numscale, alpha=numalpha)

    if anim == "rings":          # pressure-wave rings, number scales up
        lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        for k in range(3):
            r = 120 + 900 * eo((lt - k * 0.12) / 0.9)
            a = int(150 * (1 - cl((lt - k * 0.12) / 0.9)))
            if a > 0:
                dr.ellipse((CX - r, 860 - r, CX + r, 860 + r), outline=st.accent + (a,), width=6)
        cv.alpha_composite(lay)
        common(cv, numscale=lerp(0.35, 1.0, eback(lt / 0.32)) + 0.02 * lt)
    elif anim == "slide":        # cold slide: tint drops in, number slides from above
        cold = _color(ctx, p.get("tint"), (110, 200, 255))
        rect(cv, (0, 0, W, H), mix(st.bg, cold, 0.3), alpha=0.25 + eo(lt / d) * 0.45)
        y = lerp(-260, 0, eo(lt / 0.35))
        common(cv, numcol=mix(st.accent, cold, eo((lt - 0.3) / 0.5)), numxy=(CX, 860 + y),
               linecol=cold)
    elif anim == "glitch":       # RGB-split flicker + ray streaks
        _rays(ctx, cv, lt, 7)
        on = lt > 0.28 or int(lt * 30) % 3 != 1
        if lt < 0.28:
            j = random.Random(int(lt * 30)).uniform(-30, 30)
            txt(cv, (CX + j - 10, 860), num, big, (255, 40, 40), alpha=0.6)
            txt(cv, (CX - j + 10, 860), num, big, (40, 200, 255), alpha=0.5)
        common(cv, numalpha=1.0 if on else 0.2)
    elif anim == "wipe":         # left-to-right dust wipe + particles
        lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
        common(lay)
        wx = int(W * eio(lt / 0.3))
        m = Image.new("L", cv.size, 0)
        ImageDraw.Draw(m).rectangle((0, 0, wx, H), fill=255)
        lay.putalpha(Image.fromarray(np.minimum(np.asarray(lay.getchannel("A")), np.asarray(m))))
        cv.alpha_composite(lay)
        rng = random.Random(30)
        dl = Image.new("RGBA", cv.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(dl)
        pc = mix(st.accent, (255, 255, 255), 0.25)
        for _ in range(140):
            x = (rng.uniform(-300, W) + lt * rng.uniform(900, 1700)) % (W + 300) - 150
            y = rng.uniform(420, 1260)
            r = rng.uniform(1.5, 5)
            dr.ellipse((x - r, y - r, x + r, y + r), fill=pc + (int(rng.uniform(60, 170)),))
        cv.alpha_composite(dl)
    elif anim == "bounce":       # number drops in from below with overshoot
        y = lerp(700, 0, eback(lt / 0.42))
        common(cv, numxy=(CX, 860 + y))
    else:                        # odometer roll from `from` to the number
        try:
            frm = int(p.get("from", 0))
            to = int(num)
        except ValueError:
            frm, to = 0, 0
        n = int(round(lerp(frm, to, eio(lt / 0.45)))) if to else 0
        txt(cv, (CX, 560), kick, ctx.font("cond", 110), st.text, alpha=eo(lt / 0.2), track=18)
        lw = int(700 * eo((lt - 0.08) / 0.3))
        rect(cv, (CX - lw // 2, 1075, CX + lw // 2, 1083), st.accent2)
        txt(cv, (CX, 1150), lab, ctx.font("cond", 76), st.text, alpha=eo((lt - 0.3) / 0.25), track=10)
        shown = str(n) if to else num
        txt(cv, (CX, 860), shown, ctx.font("display", 400), st.accent if shown == num else st.text,
            scale=lerp(1.0, 1.06, lt / max(d, 0.5)))
    return cv


# ---------- stat ----------
def stat(ctx: Ctx, p: Dict, t, lt, d):
    st = ctx.style
    cv = ctx.base(drift=lt * 25)
    txt(cv, (CX, 470), str(p.get("heading", "")).upper(), ctx.font("cond", 54), st.muted, track=5)
    rect(cv, (90, 560, W - 90, 1240), mix(st.bg, (255, 255, 255), 0.05), alpha=0.85, r=28)
    k = eo(lt / 0.3)
    vcol = _color(ctx, p.get("color"), st.accent)
    value = str(p.get("value", ""))
    vf = ctx.font("display", 230 if len(value) <= 6 else (170 if len(value) <= 9 else 120))
    txt(cv, (CX, 810), value, vf, vcol, alpha=k, scale=lerp(1.3, 1.0, k))
    txt(cv, (CX, 1010), str(p.get("label", "")).upper(), ctx.font("cond", 64), st.text,
        alpha=eo((lt - 0.2) / 0.25), track=4)
    txt(cv, (CX, 1120), str(p.get("sub", "")).upper(), ctx.font("cond", 46), st.highlight,
        alpha=eo((lt - 0.45) / 0.3), track=3)
    return cv


# ---------- counter (ring progress + count-up) ----------
def counter(ctx: Ctx, p: Dict, t, lt, d):
    st = ctx.style
    cv = ctx.base(drift=lt * 25)
    if p.get("rays"):
        rect(cv, (0, 0, W, H), (40, 0, 0), alpha=0.25)
        _rays(ctx, cv, lt, 1, n=3)
    frm = float(p.get("from", 0))
    to = float(p.get("to", 100))
    prog = eio((lt - 0.15) / max(0.3, d - 0.5))
    val = lerp(frm, to, prog)
    fmt = str(p.get("format", "{:.0f}"))
    cx, cy, R = CX, 800, 290
    dr = ImageDraw.Draw(cv)
    dr.ellipse((cx - R, cy - R, cx + R, cy + R), outline=mix(st.bg, st.accent, 0.3), width=34)
    dr.arc((cx - R, cy - R, cx + R, cy + R), -90, -90 + 360 * prog, fill=st.accent, width=34)
    txt(cv, (cx, cy - 120), str(p.get("over", "")).upper(), ctx.font("mono", 52), st.muted)
    vtxt = fmt.format(val)
    txt(cv, (cx, cy + 5), vtxt, ctx.font("display", 200 if len(vtxt) <= 5 else 150), st.text)
    txt(cv, (cx, cy + 135), str(p.get("unit", "")).upper(), ctx.font("cond", 60), st.accent)
    txt(cv, (CX, 1170), str(p.get("label", "")).upper(),
        ctx.font("display", 84 if len(str(p.get("label", ""))) <= 20 else 60), st.text)
    txt(cv, (CX, 1255), str(p.get("sub", "")).upper(), ctx.font("cond", 44), st.highlight,
        alpha=eo((lt - 0.5) / 0.3), track=3)
    return cv


# ---------- gauge (semi-circular) ----------
def gauge(ctx: Ctx, p: Dict, t, lt, d):
    st = ctx.style
    cv = ctx.base(drift=lt * 20)
    txt(cv, (CX, 450), str(p.get("heading", "")).upper(), ctx.font("cond", 54), st.muted, track=5)
    vmax = float(p.get("max", 100))
    val = float(p.get("value", 0)) * eio(lt / 0.8)
    cx, cy, R = CX, 1060, 340
    dr = ImageDraw.Draw(cv)
    dr.arc((cx - R, cy - R, cx + R, cy + R), 180, 360, fill=mix(st.bg, st.text, 0.25), width=44)
    dr.arc((cx - R, cy - R, cx + R, cy + R), 180, 180 + 180 * cl(val / vmax), fill=st.accent, width=44)
    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        a = math.radians(180 + 180 * frac)
        x1, y1 = cx + (R - 60) * math.cos(a), cy + (R - 60) * math.sin(a)
        x2, y2 = cx + (R - 30) * math.cos(a), cy + (R - 30) * math.sin(a)
        dr.line((x1, y1, x2, y2), fill=st.muted, width=4)
    ang = math.radians(180 + 180 * cl(val / vmax))
    dr.line((cx, cy, cx + (R - 90) * math.cos(ang), cy + (R - 90) * math.sin(ang)),
            fill=st.text, width=10)
    dr.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=st.text)
    fmt = str(p.get("format", "{:.0f}"))
    txt(cv, (cx, cy - R - 140), fmt.format(val) + str(p.get("unit", "")),
        ctx.font("display", 150), st.accent)
    txt(cv, (cx, cy + 90), str(p.get("label", "")).upper(), ctx.font("cond", 56), st.text, track=4)
    txt(cv, (cx, cy + 170), str(p.get("sub", "")).upper(), ctx.font("cond", 42), st.highlight,
        alpha=eo((lt - 0.5) / 0.3), track=3)
    return cv


# ---------- bars (comparison) ----------
def bars(ctx: Ctx, p: Dict, t, lt, d):
    st = ctx.style
    cv = ctx.base(drift=lt * 25)
    txt(cv, (CX, 470), str(p.get("heading", "")).upper(), ctx.font("cond", 54), st.muted, track=5)
    items = p.get("items", [])[:3]
    if not items:
        return cv
    vmax = max(float(i.get("value", 0)) for i in items) or 1.0
    y0 = 1110
    n = len(items)
    bw = 240
    gap = (W - 160 - n * bw) / max(1, n - 1) if n > 1 else 0
    for i, it in enumerate(items):
        x0 = 80 + i * (bw + gap) if n > 1 else CX - bw / 2
        col = _color(ctx, it.get("color"), st.accent if i else (70, 160, 255))
        v = float(it.get("value", 0))
        hgt = max(4, 440 * (v / vmax) * eo(lt / 0.45))
        rect(cv, (x0, y0 - hgt, x0 + bw, y0), col)
        txt(cv, (x0 + bw / 2, y0 + 44), str(it.get("label", "")).upper(),
            ctx.font("cond", 52), col)
        disp = str(it.get("display", it.get("value", "")))
        a = eo((lt - 0.3 - i * 0.15) / 0.2)
        if 440 * (v / vmax) > 120:
            txt(cv, (x0 + bw / 2, y0 - hgt - 50), disp, ctx.font("mono", 46), st.text, alpha=a)
        else:
            txt(cv, (x0 + bw / 2, y0 - 120), disp, ctx.font("display", 110), col,
                alpha=a, scale=lerp(1.3, 1.0, a))
    txt(cv, (CX, 1230), str(p.get("sub", "")).upper(), ctx.font("cond", 44), st.highlight,
        alpha=eo((lt - 0.6) / 0.3), track=3)
    return cv


# ---------- list (sequential reveal) ----------
def list_card(ctx: Ctx, p: Dict, t, lt, d):
    st = ctx.style
    cv = ctx.base(drift=lt * 20)
    txt(cv, (CX, 470), str(p.get("heading", "")).upper(), ctx.font("cond", 54), st.muted, track=5)
    items = p.get("items", [])[:5]
    n = len(items) or 1
    row_h = min(190, 760 // n)
    y0 = 600
    step = max(0.25, (d * 0.7) / n)
    for i, it in enumerate(items):
        k = eo((lt - 0.1 - i * step) / 0.3)
        if k <= 0:
            continue
        y = y0 + i * (row_h + 24) + 30 * (1 - k)
        rect(cv, (80, y, W - 80, y + row_h), mix(st.bg, (255, 255, 255), 0.06), alpha=0.9 * k, r=22)
        col = _color(ctx, it.get("color"), st.accent)
        rect(cv, (80, y, 96, y + row_h), col, alpha=k)
        txt(cv, (140, y + row_h / 2), str(it.get("label", "")).upper(),
            ctx.font("cond", 60), st.text, alpha=k, anchor="lm", track=2)
        txt(cv, (W - 130, y + row_h / 2), str(it.get("value", "")).upper(),
            ctx.font("mono", 52), col, alpha=k, anchor="rm")
    txt(cv, (CX, y0 + n * (row_h + 24) + 60), str(p.get("sub", "")).upper(),
        ctx.font("cond", 44), st.highlight, alpha=eo((lt - 0.2 - n * step) / 0.3), track=3)
    return cv


# ---------- image (Ken Burns still) ----------
def image(ctx: Ctx, p: Dict, t, lt, d, placeholders=False):
    st = ctx.style
    src = str(p.get("src", ""))
    im = ctx.image(p.get("_abs_src", src), placeholders, label=str(p.get("label", "")))
    z = p.get("zoom", [1.0, 1.08])
    focus = p.get("focus", [0.5, 0.45])
    cv = ken_burns(im, lt / max(d, 0.01), float(z[0]), float(z[1]),
                   (float(focus[0]), float(focus[1]))).copy()
    a = eo(lt / 0.25)
    if a < 1:
        dark = Image.new("RGBA", cv.size, (0, 0, 0, int(255 * (1 - a) * 0.7)))
        cv.alpha_composite(dark)
    label = str(p.get("label", ""))
    if label:
        rect(cv, (0, 1130, W, 1310), (0, 0, 0), alpha=0.55)
        txt(cv, (CX, 1195), label.upper(), ctx.font("display", 74), st.text,
            alpha=eo((lt - 0.2) / 0.3))
        txt(cv, (CX, 1270), str(p.get("sublabel", "")).upper(), ctx.font("cond", 44),
            st.highlight, alpha=eo((lt - 0.45) / 0.3), track=3)
    return cv


# ---------- end card ----------
def end(ctx: Ctx, p: Dict, t, lt, d):
    st = ctx.style
    cv = ctx.base(drift=lt * 40)
    rect(cv, (0, 380, W, 1300), mix(st.bg, st.accent2, 0.3), alpha=0.35)
    rng = random.Random(9)
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    pc = mix(st.accent, (255, 255, 255), 0.2)
    for _ in range(90):
        x = (rng.uniform(0, W) + lt * rng.uniform(40, 160)) % W
        y = rng.uniform(400, 1300)
        r = rng.uniform(1, 4)
        dr.ellipse((x - r, y - r, x + r, y + r), fill=pc + (int(rng.uniform(60, 180)),))
    cv.alpha_composite(lay)
    k = eback(lt / 0.3)
    pill = str(p.get("pill", "")).upper()
    if pill:
        pw = max(400, int(ctx.font("display", 96).getlength(pill)) + 120)
        rect(cv, (CX - pw // 2, 560, CX + pw // 2, 690), st.accent2, alpha=cl(k), r=18)
        txt(cv, (CX, 625), pill, ctx.font("display", 96), st.text, alpha=cl(k))
    gl = random.Random(int(lt * 30)).uniform(-14, 14) if lt < 0.35 else 0
    big = str(p.get("title", "")).upper()
    txt(cv, (CX + gl, 880), big, ctx.font("display", 280 if len(big) <= 8 else 180), st.accent,
        alpha=eo((lt - 0.15) / 0.2))
    txt(cv, (CX, 1080), str(p.get("sub", "")).upper(), ctx.font("cond", 70), st.text,
        alpha=eo((lt - 0.5) / 0.3), track=4)
    return cv


SHOT_FNS = {"title": title, "card": card, "stat": stat, "counter": counter, "gauge": gauge,
            "bars": bars, "list": list_card, "image": image, "end": end}
