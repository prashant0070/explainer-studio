"""explainer CLI.

  explainer build project.yaml --vo voice.mp3       # full build, VO-timed
  explainer build project.yaml --no-vo              # captions-only demo, estimated pacing
  explainer validate project.yaml                   # check the spec and report the plan
  explainer stills project.yaml 120 450             # single frames for QA

Outputs land in <out-dir>/: <slug>.mp4 (1080x1920 master), <slug>-share.mp4
(720x1280 phone copy), <slug>-sheet.jpg (contact sheet), <slug>-qa.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time


def _build(args) -> int:
    from . import align as align_mod
    from . import timing as timing_mod
    from .audio import build_mix
    from .encode import mux, normalize, share_encode
    from .qa import build_report, summarize
    from .render import render_video
    from .sheet import contact_sheet
    from .spec import load_spec
    from .tighten import tighten

    t0 = time.time()
    spec = load_spec(args.spec)
    out_dir = args.out_dir or "out"
    work = os.path.join(out_dir, "build")
    os.makedirs(work, exist_ok=True)

    vo = None
    if not args.no_vo and args.vo:
        if not os.path.exists(args.vo):
            print(f"error: VO file not found: {args.vo}", file=sys.stderr)
            return 2
        vo = args.vo

    # 1. timing
    extras = {}
    if vo:
        if not args.no_tighten:
            rep = tighten(vo, os.path.join(work, "vo-tight.wav"), args.max_gap,
                          edits_json=os.path.join(work, "vo-edits.json"))
            print(f"tightened {len(rep['cuts'])} gaps, removed {rep['removed_s']} s of silence "
                  f"({rep['in_s']} s -> {rep['out_s']} s)")
            vo = os.path.join(work, "vo-tight.wav")
            extras["vo_tighten"] = {k: rep[k] for k in ("removed_s", "in_s", "out_s", "max_gap")}
        mode = args.align
        if mode == "auto":
            mode = "whisper" if align_mod.whisper_available() else "scale"
            if mode == "scale":
                print("note: faster-whisper not installed — falling back to duration-scaled "
                      "timing (pip install 'faster-whisper' for word-accurate cuts)")
        if mode == "whisper":
            tm = align_mod.align(spec, vo, model_name=args.whisper_model)
            print(f"aligned VO: match {tm['match_ratio']}, duration {tm['duration']} s, "
                  f"unmatched {tm['unmatched']}")
            if tm["match_ratio"] < 0.7:
                print("WARNING: VO does not match the script well — update the beat texts "
                      "to what was actually read")
        else:
            tm = timing_mod.scale_to_vo(spec, vo)
            print(f"scaled estimate to VO duration: {tm['duration']} s")
    else:
        tm = timing_mod.estimate(spec)
        print(f"no VO: estimated pacing, duration {tm['duration']} s")
    timing_mod.save(tm, os.path.join(work, "timing.json"))

    # 2. video (frames -> libx264)
    video_only = os.path.join(work, "video.mp4")
    print(f"rendering {int(tm['duration'] * spec.output.fps)} frames at {spec.output.fps} fps…")
    render_video(spec, tm, video_only, placeholders=args.placeholders, workers=args.workers)

    # 3. audio: SFX/music bed + VO -> -14 LUFS
    mix = build_mix(spec, tm, os.path.join(work, "mix.wav"), vo_path=vo or "")
    gain = normalize(mix, os.path.join(work, "mix-norm.wav"))
    print(f"loudness make-up gain {gain} dB")

    # 4. master + share + sheet + QA
    suffix = "" if vo else "-demo"
    master = os.path.join(out_dir, f"{spec.slug}{suffix}.mp4")
    mux(video_only, os.path.join(work, "mix-norm.wav"), master)
    share = ""
    if spec.output.share:
        share = os.path.join(out_dir, f"{spec.slug}{suffix}-share.mp4")
        _, mb = share_encode(master, share, spec.output.share_bitrate_k,
                             passlog_prefix=os.path.join(work, "x264pass"))
        print(f"share copy {share} ({mb} MB)")
    sheet = os.path.join(out_dir, f"{spec.slug}{suffix}-sheet.jpg")
    contact_sheet(master, sheet, n=args.sheet_frames)

    report = build_report(spec, tm, master, share, extras=extras)
    qa_path = os.path.join(out_dir, f"{spec.slug}{suffix}-qa.json")
    with open(qa_path, "w") as f:
        json.dump(report, f, indent=1)
    print(summarize(report))
    print(f"DONE in {time.time() - t0:.0f} s\n  master {master}\n  "
          + (f"share  {share}\n  " if share else "") + f"sheet  {sheet}\n  qa     {qa_path}")
    return 1 if (args.strict and report["warnings"]) else 0


def _validate(args) -> int:
    from .render import caption_chunks, shot_rows
    from .spec import load_spec
    from .timing import estimate

    spec = load_spec(args.spec)
    tm = estimate(spec)
    rows = shot_rows(spec, tm)
    print(f"OK: {spec.title!r} — {len(spec.beats)} beats, {len(spec.shots)} shots, "
          f"{len(caption_chunks(tm))} caption chunks, estimated {tm['duration']} s")
    for (si, s, e, tr), shot in zip(rows, spec.shots):
        beat = spec.beats[shot.beat]
        print(f"  {s:6.2f}-{e:6.2f}  {shot.type:<8} {tr:<5} @ {beat.id}.{shot.word}")
    missing = [s.params.get("src") for s in spec.shots
               if s.type == "image" and not os.path.exists(spec.path(str(s.params.get("src"))))]
    if missing:
        print("missing images (supply them or build with --placeholders):")
        for m in missing:
            print(f"  - {m}")
    return 0


def _stills(args) -> int:
    from .render import render_stills
    from .spec import load_spec
    from .timing import estimate, load

    spec = load_spec(args.spec)
    tm_path = os.path.join(args.out_dir or "out", "build", "timing.json")
    tm = load(tm_path) if os.path.exists(tm_path) else estimate(spec)
    out = os.path.join(args.out_dir or "out", "stills")
    paths = render_stills(spec, tm, [int(f) for f in args.frames], out,
                          placeholders=args.placeholders)
    print("\n".join(paths))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="explainer",
                                 description="Spec-driven vertical explainer video builder")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build the video end to end")
    b.add_argument("spec", help="project spec (.yaml or .json)")
    b.add_argument("--vo", default="", help="voice-over audio file (mp3/wav/m4a)")
    b.add_argument("--no-vo", action="store_true", help="captions-only demo on estimated pacing")
    b.add_argument("--no-tighten", action="store_true", help="keep the VO's original pauses")
    b.add_argument("--max-gap", type=float, default=0.38, help="max silent gap kept in the VO (s)")
    b.add_argument("--align", choices=("auto", "whisper", "scale"), default="auto",
                   help="word alignment: whisper (word-accurate), scale (duration only)")
    b.add_argument("--whisper-model", default="", help="faster-whisper model (default small.en)")
    b.add_argument("--out-dir", default="out")
    b.add_argument("--placeholders", action="store_true",
                   help="render labelled placeholder art for missing images")
    b.add_argument("--workers", type=int, default=None, help="render processes (default auto)")
    b.add_argument("--sheet-frames", type=int, default=24)
    b.add_argument("--strict", action="store_true", help="exit nonzero if QA finds warnings")
    b.set_defaults(fn=_build)

    v = sub.add_parser("validate", help="check a spec and print the shot plan")
    v.add_argument("spec")
    v.set_defaults(fn=_validate)

    s = sub.add_parser("stills", help="render single frames for QA")
    s.add_argument("spec")
    s.add_argument("frames", nargs="+", help="frame numbers")
    s.add_argument("--out-dir", default="out")
    s.add_argument("--placeholders", action="store_true")
    s.set_defaults(fn=_stills)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
