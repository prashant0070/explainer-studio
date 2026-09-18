# Explainer Studio

An end-to-end, local video production system for cinematic story explainers
(like [The ENTIRE Story of The Odyssey Explained](https://www.youtube.com/watch?v=mJS-QVw8lzY))
and Dark Vault–style investigative documentaries.

**The only paid thing is your LLM key.** Everything else — research grounding,
voiceover, images, stock footage, captions, editing, mastering, and quality
analysis — uses free services and local tools.

## The pipeline

| Stage | What happens | What it costs |
|---|---|---|
| Research | Niche → topic ideas; topic → Wikipedia-grounded fact brief | LLM tokens only |
| Script | Hook-first narration, a cut every 8–18 seconds, image prompt per scene | LLM tokens only |
| Voiceover | Neural narration per scene via `edge-tts`, with word-level timings | Free |
| Visuals | Free stock footage (Pexels/Pixabay free keys) → free AI images (Pollinations, keyless) → offline title cards | Free |
| Captions | Word-timed phrase captions built from the TTS timings, burned in | Free |
| Edit | Ken Burns motion on stills, center-cropped footage, a hard cut per scene, fades | Free (FFmpeg) |
| Master | Music bed with side-chain ducking, −16 LUFS loudness normalize, 1080p30 H.264 | Free (FFmpeg) |
| QC | Duration, resolution, fps, loudness, true peak, black frames, dead air + an LLM verdict | Free / LLM tokens |

## Run it

```bash
cd explainer-studio
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# put your OpenAI-compatible key in .env
uvicorn app.main:app --reload --port 8787
```

You also need **FFmpeg** on your PATH (`brew install ffmpeg` / `sudo apt install ffmpeg`).

Open [http://127.0.0.1:8787](http://127.0.0.1:8787).

1. **Find a topic** — pick **Mythic epics** or **Science & tech**, then hit
   *Analyze the niche*. You get what top channels are doing, Wikipedia search
   demand, and 10 ranked topics in this painted story form. Click one to fill
   the script form.
2. **Generate script** — auto-research grounds the script in Wikipedia facts.
3. **Produce full video** — pick a voice, hit the button, watch the progress
   bar walk through narration → visuals → captions → assembly → master → QC.
4. Review the QC report and play the finished MP4 right in the app.

- **No key yet:** open the Icarus demo and hit *Produce full video* — the demo
  renders end to end without any LLM key.
- **LLM key:** unlock topic research and new scripts.

## Visuals, in priority order

1. Images you already generated with a paid key are reused, never re-billed.
2. `PEXELS_API_KEY` / `PIXABAY_API_KEY` (free keys) → real stock footage per scene.
3. Paid image API (DALL·E 3 / `gpt-image-1`) if `IMAGE_API_KEY` is set — or if
   your `LLM_API_KEY` is an OpenAI key, it is reused automatically. Note:
   Claude/Opus keys cannot generate images; any failure falls back to the free tier.
4. Pollinations.ai (no key at all) → cinematic AI stills with Ken Burns motion.
5. Offline title cards rendered locally → the pipeline never blocks on a network.

## Music (optional)

Drop any royalty-free track into `data/music/` (or `music.mp3` inside a project
folder). It is looped, faded, ducked under the voice automatically. No track =
clean voice-only master.

## Export

Each project saves under `data/projects/<id>/`. The production queue lives in
`data/slate.json` — all 10 science topics and 10 mythic topics, status queued /
in progress / done, so we work through them one by one.

- `final.mp4` — the finished video
- `qc.json` — the quality report
- `captions.ass` — word-timed captions
- `audio/` — per-scene narration + timings
- `script.md`, `youtube.txt`, `project.json`, `images/`

## Honest limits

- Free services (edge-tts, Pollinations) are unofficial free tiers: unlimited in
  cost, but rate-limited in practice — long videos render slower.
- Stock-footage search is keyword-based; expect B-roll-level matches, not
  storyboarded shots. The AI-image path follows the script much more closely.
- The model can still invent details on obscure topics. Auto-research helps;
  pasting verified facts into **Source notes** helps more.
- This is not a YouTube uploader.
