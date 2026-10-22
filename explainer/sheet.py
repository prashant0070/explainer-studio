"""Contact sheet of evenly spaced frames from a rendered video, for quick review."""
from __future__ import annotations

import os
import subprocess
import tempfile

from PIL import Image, ImageDraw

from .timing import media_duration


def contact_sheet(video: str, out_jpg: str, n: int = 24, cols: int = 6) -> str:
    dur = media_duration(video)
    tmp = tempfile.mkdtemp()
    files = []
    for i in range(n):
        t = (i + 0.5) * dur / n
        f = os.path.join(tmp, f"{i:03d}_{t:05.2f}.png")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", video,
                        "-frames:v", "1", "-y", f], check=True)
        files.append(f)
    tw, th = 300, 533
    rows = (len(files) + cols - 1) // cols
    sh = Image.new("RGB", (cols * tw, rows * (th + 30)), (30, 30, 30))
    d = ImageDraw.Draw(sh)
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB").resize((tw, th))
        x, y = (i % cols) * tw, (i // cols) * (th + 30)
        sh.paste(im, (x, y))
        d.text((x + 6, y + th + 6), os.path.basename(f)[:-4], fill=(255, 255, 255))
    sh.save(out_jpg, quality=88)
    return out_jpg
