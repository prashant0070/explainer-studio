"""Drawing primitives shared by all shots: fonts, easing, text with tracking,
rounded rects, the generated background, vignette/grain, and placeholder stills."""
from __future__ import annotations

import math
import os
from typing import Dict, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import H, W

Color = Tuple[int, int, int]

# role -> candidate font files (first found in the font dir wins)
FONT_FILES = {
    "display": ["Anton-Regular.ttf"],
    "cond": ["BarlowCondensed-ExtraBold.ttf", "BarlowCondensed-Bold.ttf"],
    "condsemi": ["BarlowCondensed-SemiBold.ttf", "BarlowCondensed-Bold.ttf"],
    "mono": ["JetBrainsMono.ttf", "JetBrainsMono-VariableFont_wght.ttf"],
}
_SYSTEM_FALLBACKS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


class Ctx:
    """Per-process render context: style colors, font cache, asset cache."""

    def __init__(self, style, font_dir: str):
        self.style = style
        self.font_dir = font_dir
        self._fonts: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}
        self.assets: Dict[str, object] = {}

    def font(self, role: str, size: int) -> ImageFont.FreeTypeFont:
        key = (role, size)
        if key not in self._fonts:
            path = None
            for name in FONT_FILES.get(role, []):
                p = os.path.join(self.font_dir, name)
                if os.path.exists(p):
                    path = p
                    break
            if path is None:
                path = next((p for p in _SYSTEM_FALLBACKS if os.path.exists(p)), None)
            if path is None:
                raise FileNotFoundError(f"no font found for role {role!r} in {self.font_dir}")
            f = ImageFont.truetype(path, size)
            if role == "mono":
                try:
                    f.set_variation_by_name("ExtraBold")
                except Exception:
                    pass
            self._fonts[key] = f
        return self._fonts[key]

    # ---- cached generated assets ----
    def bg_base(self) -> Image.Image:
        if "bg" not in self.assets:
            bg = self.style.bg
            acc = self.style.accent
            y = np.linspace(0, 1, H)[:, None]
            x = np.linspace(-1, 1, W)[None, :]
            r = np.sqrt(x ** 2 + ((y - 0.45) * 1.6) ** 2)
            glow = np.exp(-r * 2.2)
            base = np.stack([bg[0] + (acc[0] - bg[0]) * 0.1 * glow,
                             bg[1] + (acc[1] - bg[1]) * 0.08 * glow,
                             bg[2] + (acc[2] - bg[2]) * 0.06 * glow], -1)
            self.assets["bg"] = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
        return self.assets["bg"]  # type: ignore[return-value]

    def grid(self) -> Image.Image:
        if "grid" not in self.assets:
            g = Image.new("RGBA", (W + 120, H + 120), (0, 0, 0, 0))
            d = ImageDraw.Draw(g)
            for x in range(0, W + 120, 60):
                d.line([(x, 0), (x, H + 120)], fill=(255, 255, 255, 10))
            for y in range(0, H + 120, 60):
                d.line([(0, y), (W + 120, y)], fill=(255, 255, 255, 10))
            self.assets["grid"] = g
        return self.assets["grid"]  # type: ignore[return-value]

    def vignette(self) -> np.ndarray:
        if "vig" not in self.assets:
            y = np.linspace(-1, 1, H)[:, None]
            x = np.linspace(-1, 1, W)[None, :]
            v = 1 - 0.55 * np.clip((x ** 2 * 0.9 + y ** 2 * 0.6) - 0.15, 0, 1)
            self.assets["vig"] = v[..., None].astype(np.float32)
        return self.assets["vig"]  # type: ignore[return-value]

    def grain(self):
        if "grain" not in self.assets:
            rng = np.random.default_rng(7)
            self.assets["grain"] = [
                np.array(Image.fromarray(rng.normal(128, 40, (H // 2, W // 2)).clip(0, 255)
                                         .astype(np.uint8)).resize((W, H), Image.BILINEAR),
                         np.float32)[..., None] / 255 - 0.5
                for _ in range(6)]
        return self.assets["grain"]

    def image(self, path: str, placeholders: bool, label: str = "") -> Image.Image:
        key = "img:" + path
        if key not in self.assets:
            if os.path.exists(path):
                im = Image.open(path).convert("RGB")
            elif placeholders:
                im = placeholder_still(os.path.basename(path), label, self.style)
            else:
                raise FileNotFoundError(
                    f"image not found: {path} (pass --placeholders to render labelled "
                    "placeholder art instead)")
            self.assets[key] = cover(im, W, H).convert("RGBA")
        return self.assets[key]  # type: ignore[return-value]

    def base(self, drift: float = 0.0, grid: Optional[bool] = None) -> Image.Image:
        cv = self.bg_base().copy()
        if grid if grid is not None else self.style.grid:
            g = self.grid()
            off = int(drift) % 60
            cv.alpha_composite(g.crop((off, off, off + W, off + H)))
        return cv


# ---------- easing ----------
def cl(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return max(a, min(b, x))


def eo(x: float) -> float:
    x = cl(x)
    return 1 - (1 - x) ** 3


def eio(x: float) -> float:
    x = cl(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def eback(x: float) -> float:
    x = cl(x)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(c1: Color, c2: Color, t: float) -> Color:
    return tuple(int(lerp(a, b, cl(t))) for a, b in zip(c1, c2))  # type: ignore[return-value]


# ---------- primitives ----------
def txt(cv: Image.Image, xy, s: str, font, fill: Color = (245, 245, 245), alpha: float = 1.0,
        scale: float = 1.0, anchor: str = "mm", stroke: int = 0, sfill: Color = (0, 0, 0),
        track: int = 0) -> None:
    if alpha <= 0.01 or not s:
        return
    if track:
        widths = [font.getlength(ch) for ch in s]
        tw = sum(widths) + track * (len(s) - 1)
        asc, desc = font.getmetrics()
        lay = Image.new("RGBA", (int(tw) + 2 * stroke + 4, asc + desc + 2 * stroke + 4), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        x = stroke + 2
        for ch, w_ in zip(s, widths):
            d.text((x, stroke + 2), ch, font=font, fill=fill + (255,),
                   stroke_width=stroke, stroke_fill=sfill)
            x += w_ + track
    else:
        bb = font.getbbox(s, stroke_width=stroke)
        lay = Image.new("RGBA", (bb[2] - bb[0] + 4, bb[3] - bb[1] + 4), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((-bb[0] + 2, -bb[1] + 2), s, font=font, fill=fill + (255,),
                                 stroke_width=stroke, stroke_fill=sfill)
    if scale != 1.0:
        lay = lay.resize((max(1, int(lay.width * scale)), max(1, int(lay.height * scale))),
                         Image.BICUBIC)
    if alpha < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    x, y = xy
    w_, h_ = lay.size
    ox = {"l": 0, "m": w_ / 2, "r": w_}[anchor[0]]
    oy = {"t": 0, "m": h_ / 2, "b": h_}[anchor[1]]
    cv.alpha_composite(lay, (int(x - ox), int(y - oy)))


def rect(cv: Image.Image, box, fill: Color, alpha: float = 1.0, r: int = 0) -> None:
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    a = int(255 * cl(alpha))
    if r:
        d.rounded_rectangle(box, r, fill=fill + (a,))
    else:
        d.rectangle(box, fill=fill + (a,))
    cv.alpha_composite(lay)


def cover(im: Image.Image, w: int, h: int) -> Image.Image:
    """Scale + center-crop to fill w x h."""
    k = max(w / im.width, h / im.height)
    im = im.resize((max(w, int(im.width * k + 0.5)), max(h, int(im.height * k + 0.5))),
                   Image.LANCZOS)
    x0 = (im.width - w) // 2
    y0 = (im.height - h) // 2
    return im.crop((x0, y0, x0 + w, y0 + h))


def placeholder_still(name: str, label: str, style) -> Image.Image:
    """Deterministic labelled placeholder art for missing stills."""
    seed = sum(ord(c) for c in name)
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    a = rng.uniform(1.5, 4.0, 3)
    p = rng.uniform(0, 6.28, 3)
    f = (np.sin(x * a[0] * 3 + p[0]) + np.sin(y * a[1] * 3 + p[1])
         + np.sin((x + y) * a[2] * 3 + p[2])) / 3
    c1, c2 = np.array(style.bg, np.float32), np.array(style.accent, np.float32)
    img = c1[None, None] + (c2 - c1)[None, None] * (0.25 + 0.3 * (f[..., None] * 0.5 + 0.5))
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    im = im.filter(ImageFilter.GaussianBlur(2))
    d = ImageDraw.Draw(im)
    for i in range(14):
        xx, yy = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(30, 220)
        d.ellipse((xx - r, yy - r, xx + r, yy + r), outline=(255, 255, 255, 30), width=2)
    try:
        f1 = ImageFont.truetype(_SYSTEM_FALLBACKS[0], 54)
        f2 = ImageFont.truetype(_SYSTEM_FALLBACKS[0], 34)
    except OSError:
        f1 = f2 = ImageFont.load_default()  # type: ignore[assignment]
    d.text((W // 2, H // 2 - 40), "PLACEHOLDER", font=f1, fill=(255, 255, 255), anchor="mm")
    d.text((W // 2, H // 2 + 30), name, font=f2, fill=(230, 230, 230), anchor="mm")
    if label:
        d.text((W // 2, H // 2 + 90), label[:60], font=f2, fill=(200, 200, 200), anchor="mm")
    return im


def ease_shake(lt: float, until: float = 0.25, amp: float = 6.0) -> float:
    import random
    return random.Random(int(lt * 30)).uniform(-amp, amp) if lt < until else 0.0


def ken_burns(im: Image.Image, t01: float, z0: float, z1: float,
              focus: Tuple[float, float]) -> Image.Image:
    """Slow zoom/pan over a cover-fitted still."""
    z = lerp(z0, z1, eio(t01))
    cw, ch = W / z, H / z
    fx, fy = focus[0] * W, focus[1] * H
    x0 = cl(fx - cw / 2, 0, W - cw)
    y0 = cl(fy - ch / 2, 0, H - ch)
    return im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def arrow_angle_polys(cx: float, cy: float, R: float, ang_deg: float):
    """Two arc-arrow heads used by recycle-style loops."""
    out = []
    for k in range(2):
        a0 = ang_deg + k * 180
        e = math.radians(a0 + 140)
        ex, ey = cx + R * math.cos(e), cy + R * math.sin(e)
        tx, ty = -math.sin(e), math.cos(e)
        nx, ny = math.cos(e), math.sin(e)
        out.append((a0, [(ex + tx * 30, ey + ty * 30), (ex + nx * 24, ey + ny * 24),
                         (ex - nx * 24, ey - ny * 24)]))
    return out
