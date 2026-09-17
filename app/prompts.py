from __future__ import annotations

from typing import Literal

StyleName = Literal["odyssey", "dark_vault", "science"]

DURATION_TARGETS = {
    "8": {"minutes": 8, "words": 1100, "scenes": 28},
    "12": {"minutes": 12, "words": 1650, "scenes": 40},
    "15": {"minutes": 15, "words": 2100, "scenes": 50},
}

IMAGE_STYLE = (
    "Cinematic painted illustration, 16:9 widescreen, ultra-detailed oil-painting realism, "
    "dramatic chiaroscuro, warm amber torchlight against deep teal-black shadows, "
    "volumetric dust and sea mist, film-still composition, shallow depth of field, "
    "no text, no letters, no watermark, no logo, no modern objects, no UI, "
    "no photoreal faces of living celebrities"
)

SCIENCE_IMAGE_STYLE = (
    "Cinematic painted illustration, 16:9 widescreen, ultra-detailed oil-painting realism, "
    "dramatic chiaroscuro, warm tungsten and amber instrument light against deep teal-black shadows, "
    "volumetric dust, condensation, and night-launch haze, film-still composition, shallow depth of field, "
    "period-accurate laboratories, machines, rockets, reactors, and instruments allowed, "
    "no text, no letters, no watermark, no logo, no UI, "
    "no photoreal faces of living celebrities"
)

ODYSSEY_SYSTEM = """You write YouTube scripts in the cinematic story-explainer format.

Reference pattern (do not copy wording): a video like "The ENTIRE Story of The Odyssey Explained" —
hook-first, spoken, illustrated, cut every few seconds.

VOICE
- Write for the ear. Short sentences. Then a longer one when it lands.
- Conversational and slightly dry. "Yeah, seriously." Rhetorical questions.
- Concrete numbers and names. No academic throat-clearing.
- Dialogue is 2–4 spoken lines, not a play.
- Location beats use "right here" so an editor can cut to a map.

STRUCTURE
1. Hook (first 12–20 seconds): the WHOLE story happened because of ONE surprising cause.
2. Stakes in numbers. Then one driving question.
3. Origin / setup, then disasters that escalate. Never flatten.
4. Lowest point. Then return or reveal.
5. Lesson that pays off the hook. One sentence thesis.
6. Soft CTA only after the lesson.

SCENES
- One scene = 8–18 seconds of narration (about 20–45 words).
- Every scene needs a NEW picture. No talking-head. No text-on-black.
- Visual types: establishing, map, character, action, dialogue, insert, aftermath.
- Image prompts must be self-contained, specific, and match the shared look.

FACTS
- Do not invent modern statistics, quotes, or dates.
- Myths and traditional narratives can be told as the story, but mark scholarly dispute in notes.
- If source notes are provided, prefer them.

Return ONLY valid JSON matching the schema. No markdown."""

DARK_VAULT_SYSTEM = """You write investigative documentary scripts for a channel like The Dark Vault.

VOICE
- Calm, low, precise. Dread from facts, not adjectives.
- Open with a specific case or anomaly, then widen the question.
- Investigation, not sermon. Separate what is known / suspected / uncertain.
- Short spoken sentences. Pause-friendly. No jump-scare writing.

STRUCTURE
1. Cold open (15–30s): one concrete incident that creates a gap the viewer needs closed.
2. The real question of the episode.
3. Evidence in rising intensity. Each section adds a new kind of proof, not a repeat.
4. The uncomfortable middle: the best counter-explanation.
5. What we know / suspect / cannot know.
6. Quiet ending that does not resolve the mystery. Soft CTA after that.

SCENES
- One scene = 8–18 seconds of narration.
- Visuals are cinematic, grounded, documentary: empty rooms, archives, maps, instruments, night interiors.
- No gore, no sexual imagery, no shock faces.

FACTS
- Do not invent statistics, court outcomes, quotes, or names.
- If a claim is unverified, say so in the narration.
- If source notes are provided, prefer them.

Return ONLY valid JSON matching the schema. No markdown."""

SCIENCE_SYSTEM = """You write YouTube scripts in the cinematic story-explainer format, applied to science and technology.

Same job as a myth explainer: hook-first, spoken, illustrated, cut every few seconds.
The "monster" is a machine, a microbe, a measurement, or a committee. The story still has one cause.

VOICE
- Write for the ear. Short sentences. Then a longer one when it lands.
- Conversational and slightly dry. "Yeah. That was the test." Rhetorical questions.
- Concrete numbers, names, dates. No textbook throat-clearing. No "in this video we will".
- Dialogue is 2–4 spoken lines from the historical record or a tight paraphrase, not a play.
- Location beats use "right here" so an editor can cut to a lab, pad, or instrument.

STRUCTURE
1. Hook (first 12–20 seconds): the WHOLE story happened because of ONE decision, error, or bargain.
2. Stakes in numbers. Then one driving question.
3. The idea or machine is born. Then it escalates. Never flatten into a timeline lecture.
4. Lowest point: the night it fails, or the year nobody believes them.
5. Lesson that pays off the hook. One sentence thesis.
6. Soft CTA only after the lesson.

SCENES
- One scene = 8–18 seconds of narration (about 20–45 words).
- Every scene needs a NEW picture. No talking-head. No chalkboard. No UI screenshots.
- Visual types: establishing, instrument close-up, action, aftermath, portrait, insert, night exterior.
- Image prompts must be self-contained, specific, and match the shared look.
- Period-accurate tech is required. Do not modernize a 1946 lab into a 2020s open-plan office.

FACTS
- Do not invent papers, death tolls, quotes, or dates.
- If source notes are provided, prefer them.
- Mark scholarly or technical dispute in the narration when it matters.

Return ONLY valid JSON matching the schema. No markdown."""

JSON_SCHEMA = """{
  "titles": ["primary title", "alt 1", "alt 2"],
  "thumbnail_text": "3-6 punchy words",
  "thumbnail_prompt": "full image prompt, no text in the image itself",
  "hook": "spoken hook, 40-70 words",
  "driving_question": "one sentence",
  "thesis": "the lesson the hook promised",
  "runtime_seconds": 480,
  "word_count": 1100,
  "youtube_description": "2 short paragraphs + chapters placeholder",
  "tags": ["tag1", "tag2"],
  "chapters": [{"time": "0:00", "title": "Hook"}],
  "full_narration": "the complete spoken script, scene narration joined with blank lines",
  "scenes": [
    {
      "id": 1,
      "section": "hook",
      "visual_type": "establishing",
      "narration": "spoken lines for this cut",
      "on_screen_text": "",
      "duration_seconds": 12,
      "image_prompt": "self-contained cinematic prompt"
    }
  ]
}"""


def system_prompt(style: StyleName) -> str:
    if style == "dark_vault":
        return DARK_VAULT_SYSTEM
    if style == "science":
        return SCIENCE_SYSTEM
    return ODYSSEY_SYSTEM


def image_style_for(style: StyleName) -> str:
    return SCIENCE_IMAGE_STYLE if style == "science" else IMAGE_STYLE


def user_prompt(
    topic: str,
    style: StyleName,
    duration_key: str,
    angle: str,
    notes: str,
) -> str:
    target = DURATION_TARGETS[duration_key]
    if style == "dark_vault":
        style_label = "Dark Vault investigative documentary"
    elif style == "science":
        style_label = "Odyssey-style cinematic science-and-tech story explainer"
    else:
        style_label = "Odyssey-style cinematic story explainer"
    look = image_style_for(style)
    extras = []
    if angle.strip():
        extras.append(f"ANGLE / HOOK IDEA:\n{angle.strip()}")
    if notes.strip():
        extras.append(f"SOURCE NOTES (prefer these facts):\n{notes.strip()}")
    extra_block = "\n\n".join(extras)
    extra_block = f"\n\n{extra_block}" if extra_block else ""
    return f"""Create a {style_label} production pack.

TOPIC: {topic.strip()}
TARGET RUNTIME: {target['minutes']} minutes
TARGET WORD COUNT: about {target['words']} spoken words
TARGET SCENE COUNT: about {target['scenes']} scenes (8–18 seconds each)
IMAGE LOOK (append this to every image_prompt): {look}
{extra_block}

JSON schema:
{JSON_SCHEMA}

Rules for image_prompt:
- Start with the subject and action, then lighting, then the shared look string above.
- Keep characters consistent if they recur (same age, clothing, hair).
- Maps: antique parchment, labeled geography implied by landmarks, still no readable text.
- Thumbnail prompt: one iconic frame, face or object large, high contrast, no text.
"""


def normalize_image_prompt(prompt: str, style: StyleName = "odyssey") -> str:
    look = image_style_for(style)
    text = (prompt or "").strip()
    if look.lower() not in text.lower() and IMAGE_STYLE.lower() not in text.lower():
        text = f"{text.rstrip('.')} — {look}"
    return text
