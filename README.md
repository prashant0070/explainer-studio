# Explainer Studio

Tools for making faceless explainer videos, in two parts:

1. **`explainer` — the render pipeline (CLI).** Takes a project spec (YAML/JSON) and
   a voice-over file, and builds a finished vertical Short: word-aligned cuts,
   code-drawn motion graphics, word-synced captions, a −14 LUFS mix, a 1080x1920
   master plus a phone-friendly 720x1280 copy, a contact sheet and a QA report.
2. **The studio (web app).** The original FastAPI tool that writes the script and
   scene image pack from a topic using LLM/image APIs. Use it for pre-production;
   its output feeds the spec you give the pipeline.

The pipeline generalizes the one-off build behind the "Survive 100 Days on Mars"
Short; that video is ported as the example project in [`examples/mars/`](examples/mars/).

## Setup

System: **ffmpeg** (with libx264) and Python ≥ 3.10.

```bash
sudo apt install ffmpeg            # or brew install ffmpeg
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                   # numpy, Pillow, PyYAML + the `explainer` CLI
pip install -e '.[align]'          # + faster-whisper for word-accurate VO alignment
pip install -e '.[dev]'            # + pytest
```

Fonts (Anton, Barlow Condensed, JetBrains Mono — all SIL OFL) ship in `fonts/`.

## Quick start

```bash
# captions-only demo on estimated pacing, placeholder art for missing images
explainer build examples/mars/project.yaml --no-vo --placeholders

# the real thing: record the narration (e.g. ElevenLabs), then
explainer build examples/mars/project.yaml --vo vo.mp3
```

Outputs in `out/`:

| File | What |
|---|---|
| `<slug>.mp4` | 1080x1920 master, H.264 High, CRF 18, AAC 192k, faststart |
| `<slug>-share.mp4` | 720x1280, H.264 **Main** L3.1, yuv420p, two-pass ~700 kbps (≈ 5–8 MB/min) — opens on any phone |
| `<slug>-sheet.jpg` | contact sheet of 24 frames for quick review |
| `<slug>-qa.json` | QA report: duration, loudness, stream specs, shot reuse, caption overflow, alignment quality |
| `build/` | intermediates: `timing.json`, tightened VO + cut log, mix WAVs |

Other commands:

```bash
explainer validate project.yaml        # check the spec, print the shot plan, list missing images
explainer stills project.yaml 120 450  # render single frames for QA
```

## How a build works

1. **Tighten** (`--no-tighten` to skip, `--max-gap` to tune): silent gaps longer
   than 0.38 s in the VO are cut down to 0.38 s — silence only, 12 ms crossfades,
   the voice is never stretched, sped up or filtered. Cut log in `build/vo-edits.json`.
2. **Align**: faster-whisper word timestamps are matched to the script (digit and
   spoken forms both match), unmatched words are interpolated, and phrase-start
   words snap to the real energy onset of the voice. Every cut and caption word is
   anchored to those times; cuts land 2 frames before the spoken word. Without
   faster-whisper (`--align scale`), the estimate is stretched to the VO duration.
   With `--no-vo`, pacing is estimated from the text.
3. **Render**: every shot is a code-drawn motion graphic (or a Ken Burns still),
   with hard punch-ins on spoken words inside long shots, whip/zoom transitions,
   karaoke captions kept inside a 900 px safe width, series banner + progress
   timeline overlays, vignette and grain. Multiprocess, ~30–60 fps render speed.
4. **Mix**: original synthesized SFX bed (whooshes on cuts, ticks on data shots,
   impacts) plus an optional music bed, ducked under the voice; two-pass loudnorm
   to **−14 LUFS / −1.5 dBTP** with a peak-limited make-up stage.
5. **Export + QA**: master, share copy, contact sheet, QA JSON (warnings for
   loudness misses, repeated shots, captions scaled below 75%, oversized share files).

## Project spec

See [`examples/mars/project.yaml`](examples/mars/project.yaml) for a complete,
commented example. The shape:

```yaml
title: "My Video"
style: { accent: "#ec7634", font_dir: ../../fonts }   # colors, fonts, grain
banner: { lines: ["SERIES NAME", "EPISODE HOOK?"], pill: "PART 1" }
timeline: { labels: ["1", "2"], beats: [b1, b2] }     # progress strip (optional)
audio: { sfx: true, music: bed.mp3, music_gain_db: -18 }
output: { fps: 30, share: true }
spoken: { "95%": ninety five percent }   # how tokens are read, for timing + matching

beats:                                   # the narration, one caption line per beat
  - id: b1
    text: "Day 1. The air is 95% carbon dioxide."

shots:                                   # anchored to beat words: cuts land on speech
  - type: card                           # day/number card; animations never repeat:
    at: b1.0                             #   rings, slide, glitch, wipe, bounce, odometer
    transition: whip
    number: "1"
    label: "THE AIR"
  - type: counter                        # also: title, stat, gauge, bars, list,
    at: b1.2                             #   image (Ken Burns still), end
    from: 0
    to: 95.1
    unit: "% CO2"
    punch:                               # hard punch-in when the word is spoken
      - { at: b1.4, zoom: 1.16, focus: [0.5, 0.48] }
    slam:                                # full-width text hit on a spoken word
      at: b1.6
      lines: ["HELMET ON.", "ALWAYS."]
    credit: "DATA: NASA GSFC"            # on-screen credit pill
```

Shot types: `title`, `card` (6 distinct animations), `stat`, `counter` (ring
count-up), `gauge`, `bars` (comparison), `list` (sequential reveal), `image`
(user-supplied still with Ken Burns), `end`. All layout happens on a 1080x1920
design canvas; punch-ins only affect the content band (y 386–1322) so they never
push into the banner or captions.

## Copyright safety

- **No third-party media is bundled.** Stills are user-supplied local files (the
  Mars example uses NASA public-domain images the user downloads — see
  [`examples/mars/assets/README.md`](examples/mars/assets/README.md)).
- All graphics are drawn in code; the SFX bed is synthesized in code.
- Fonts are SIL OFL 1.1 (licenses in `fonts/`).
- Use the `credit:` field to keep on-screen attribution for any imagery.

## Tests

```bash
python3 -m pytest tests/
```

Covers spec validation, timing, VO tightening on synthetic audio, a render smoke
test of every shot type, QA checks, and an end-to-end CLI build (both MP4s,
sheet, QA report) with placeholder images and a synthetic VO fixture.

## The studio (script + image pack web app)

The original tool: writes narration with a cut every 8–18 seconds and a cinematic
prompt (or generated still) per cut, in two presets (Odyssey-style story
explainers, Dark Vault investigations). It does not render video — that's the
pipeline's job now.

```bash
pip install -e '.[studio]'
cp .env.example .env     # add an OpenAI-compatible key
uvicorn app.main:app --reload --port 8787
```

Open http://127.0.0.1:8787. Projects save under `data/projects/<id>/`; **Export
zip** gives `script.md`, `youtube.txt`, `project.json` and any generated stills.
Honest limits: image APIs cost money (40–80 stills for a 12-minute video); the
model invents details unless you paste source notes.

## Repo layout

```
explainer/        the render pipeline package + CLI
examples/mars/    the ported Mars Short as an example project spec
fonts/            OFL fonts used by the renderer
tests/            pytest suite
app/, web/        the studio web app (FastAPI + vanilla JS)
```
