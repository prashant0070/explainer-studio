# Explainer Studio

A local tool that writes a YouTube **script** and **scene image pack** in the style of cinematic story explainers like [The ENTIRE Story of The Odyssey Explained](https://www.youtube.com/watch?v=mJS-QVw8lzY).

It does not render a finished video. It gives you the production pack editors actually use: spoken narration, a cut every 8–18 seconds, and a cinematic prompt (or generated still) for each cut.

## What it matches from that video

| Beat | What the tool writes |
|---|---|
| First 15 seconds | One causal hook: the whole story happened because of *one* mistake |
| Voice | Short spoken sentences, dry asides, rhetorical questions |
| Maps | “Right here” location cuts |
| Dialogue | 2–4 line exchanges, not a play |
| Pictures | New 16:9 painted frame per scene — amber light, teal shadow, no text in the image |
| Ending | A lesson that pays off the hook, then a soft CTA |

There is a second preset, **Dark Vault investigation**, for the calmer documentary voice you already use.

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

Open [http://127.0.0.1:8787](http://127.0.0.1:8787).

- **No key yet:** open the Icarus demo to see the format.
- **LLM key:** generate a full script + scene prompts from a topic.
- **Image key:** render the thumbnail and the first 8 stills (DALL·E 3 / `gpt-image-1`).

`IMAGE_API_KEY` can be omitted; the app reuses `LLM_API_KEY` for images.

## Export

Each project saves under `data/projects/<id>/`. **Export zip** includes:

- `script.md` — titles, hook, full narration, scene list
- `youtube.txt` — description, chapters, tags
- `project.json` — machine-readable pack
- `images/` — any stills you generated

Drop the stills on a timeline, record the narration (or send it to ElevenLabs), and cut on scene boundaries.

## Honest limits

- Image APIs cost money. A 12-minute cut like the Odyssey video can need 40–80 stills. Start with 8, then generate the rest in batches.
- The model will invent details if you do not paste source notes. For Dark Vault topics, put verified facts in **Source notes**.
- This is not a YouTube uploader and not a video renderer.
