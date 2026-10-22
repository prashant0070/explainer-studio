# Example project: Survive 100 Days on Mars

Port of the one-off Mars pipeline that produced the original 65 s Short, expressed
as a generic `project.yaml`. Facts and credits come from that build's SOURCES
research (NASA fact sheets, Hassler et al. 2014, UNSCEAR 2024).

## 1. Get the images

See [assets/README.md](assets/README.md) — four NASA public-domain stills the user
downloads themself (nothing third-party is bundled). Or skip them and build with
`--placeholders`.

## 2. Record the voice-over

Read the beats from `project.yaml` top to bottom (one take, read as written) into
your TTS or recording tool of choice (the original used ElevenLabs), and save it
as e.g. `vo.mp3`. Pause briefly after each "Day N." so the day card hits.

## 3. Build

```bash
# full build: tighten pauses, word-align, render, mix to -14 LUFS, export both MP4s
explainer build examples/mars/project.yaml --vo vo.mp3 --out-dir out/mars

# captions-only demo on estimated pacing (no VO needed)
explainer build examples/mars/project.yaml --no-vo --placeholders --out-dir out/mars
```

Outputs: `mars-100-days.mp4` (1080x1920 master), `mars-100-days-share.mp4`
(720x1280 phone copy, ~6 MB/min), `mars-100-days-sheet.jpg` (contact sheet),
`mars-100-days-qa.json` (QA report).
