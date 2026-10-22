"""QA report: duration, loudness, stream specs, shot reuse, caption overflow."""
from __future__ import annotations

import json
import os
import subprocess
from typing import Dict, List

from .draw import Ctx
from .encode import measure_loudness
from .render import caption_chunks, shot_rows
from .spec import Spec


def _stream_info(path: str) -> Dict:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_name,profile,width,height,pix_fmt,avg_frame_rate:format=duration,size",
         "-of", "json", path])
    data = json.loads(out)
    v = next((s for s in data.get("streams", []) if s.get("width")), {})
    fmt = data.get("format", {})
    return {"codec": v.get("codec_name"), "profile": v.get("profile"),
            "width": v.get("width"), "height": v.get("height"), "pix_fmt": v.get("pix_fmt"),
            "duration_s": round(float(fmt.get("duration", 0)), 2),
            "size_mb": round(int(fmt.get("size", 0)) / 1e6, 2)}


def shot_reuse(spec: Spec) -> List[str]:
    """Flags shots whose type and visual parameters are identical (slideshow feel)."""
    seen: Dict[str, int] = {}
    dupes = []
    for i, s in enumerate(spec.shots):
        params = {k: v for k, v in s.params.items() if not k.startswith("_")}
        sig = json.dumps({"type": s.type, "params": params}, sort_keys=True, default=str)
        if sig in seen:
            dupes.append(f"shot {i} ({s.type}) repeats shot {seen[sig]} with identical parameters")
        else:
            seen[sig] = i
    return dupes


def caption_overflow(spec: Spec, tm: Dict) -> List[Dict]:
    """Caption chunks wider than the safe width get auto-scaled at render time;
    report them, and flag hard overflows where the scale drops below 0.75."""
    ctx = Ctx(spec.style, spec.path(spec.style.font_dir))
    f = ctx.font("display", spec.captions.size)
    out = []
    for chunk in caption_chunks(tm):
        text = " ".join(w for w, _, _ in chunk)
        shown = text.upper() if spec.captions.uppercase else text
        w = f.getlength(shown) + 8 * 2 * 2 + 40  # stroke + padding, matches the renderer
        if w > spec.captions.safe_width:
            scale = round(spec.captions.safe_width / w, 3)
            out.append({"text": text, "width_px": int(w), "scaled_to": scale,
                        "hard": scale < 0.75})
    return out


def build_report(spec: Spec, tm: Dict, master: str, share: str = "",
                 extras: Dict = None) -> Dict:
    rows = shot_rows(spec, tm)
    lens = [round(e - s, 2) for _, s, e, _ in rows]
    report = {
        "title": spec.title,
        "timing_source": tm.get("source"),
        "duration_s": tm["duration"],
        "shots": {"count": len(rows), "min_len_s": min(lens), "max_len_s": max(lens),
                  "reused": shot_reuse(spec)},
        "captions": {"overflow": caption_overflow(spec, tm)},
        "master": _stream_info(master),
        "loudness": measure_loudness(master),
    }
    if "match_ratio" in tm:
        report["alignment"] = {"match_ratio": tm["match_ratio"],
                               "unmatched_words": tm.get("unmatched", []),
                               "snapped_onsets": tm.get("snapped_onsets", 0)}
    if share and os.path.exists(share):
        si = _stream_info(share)
        mins = max(si["duration_s"], 1) / 60
        si["mb_per_min"] = round(si["size_mb"] / mins, 2)
        report["share"] = si
    if extras:
        report.update(extras)
    # verdicts
    warnings = []
    L = report["loudness"]
    if abs(L["integrated_lufs"] - (-14.0)) > 1.0:
        warnings.append(f"loudness {L['integrated_lufs']} LUFS is off the -14 target")
    if L["true_peak_dbtp"] > -0.5:
        warnings.append(f"true peak {L['true_peak_dbtp']} dBTP is above -0.5")
    warnings += report["shots"]["reused"]
    for c in report["captions"]["overflow"]:
        if c["hard"]:
            warnings.append(f"caption scaled below 75%: \"{c['text']}\"")
    if report.get("share", {}).get("mb_per_min", 0) > 9:
        warnings.append(f"share copy is {report['share']['mb_per_min']} MB/min (target 5-8)")
    report["warnings"] = warnings
    return report


def summarize(report: Dict) -> str:
    L = report["loudness"]
    lines = [
        f"QA — {report['title']}",
        f"  duration {report['duration_s']} s · timing {report['timing_source']}",
        f"  master  {report['master']['width']}x{report['master']['height']} "
        f"{report['master']['codec']}/{report['master']['profile']} "
        f"{report['master']['pix_fmt']} · {report['master']['size_mb']} MB",
    ]
    if "share" in report:
        s = report["share"]
        lines.append(f"  share   {s['width']}x{s['height']} {s['codec']}/{s['profile']} "
                     f"{s['pix_fmt']} · {s['size_mb']} MB ({s['mb_per_min']} MB/min)")
    lines.append(f"  loudness {L['integrated_lufs']} LUFS · peak {L['true_peak_dbtp']} dBTP "
                 f"· LRA {L['lra']}")
    if "alignment" in report:
        a = report["alignment"]
        lines.append(f"  alignment match {a['match_ratio']} · unmatched "
                     f"{len(a['unmatched_words'])} · snapped onsets {a['snapped_onsets']}")
    n_over = len(report["captions"]["overflow"])
    lines.append(f"  shots {report['shots']['count']} "
                 f"({report['shots']['min_len_s']}-{report['shots']['max_len_s']} s) · "
                 f"reused {len(report['shots']['reused'])} · caption auto-scales {n_over}")
    if report["warnings"]:
        lines.append("  WARNINGS:")
        lines += [f"   - {w}" for w in report["warnings"]]
    else:
        lines.append("  all checks passed")
    return "\n".join(lines)
