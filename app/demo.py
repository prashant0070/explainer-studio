from __future__ import annotations

from typing import Any, Dict

from app.prompts import IMAGE_STYLE, normalize_image_prompt

# Original sample — same format as the Odyssey explainer, not a copy of that script.
DEMO_PROJECT: Dict[str, Any] = {
    "id": "demo-icarus",
    "topic": "The fall of Icarus",
    "style": "odyssey",
    "duration_key": "8",
    "titles": [
        "The ENTIRE Story of Icarus Explained",
        "He Didn't Fall Because He Flew Too High",
        "The Warning Icarus Ignored for 8 Minutes",
    ],
    "thumbnail_text": "HE IGNORED THE WARNING",
    "thumbnail_prompt": normalize_image_prompt(
        "A teenage boy in wax-and-feather wings mid-fall above a dark Aegean sea, "
        "sun flaring behind him, feathers peeling off in gold light, terrified upward gaze"
    ),
    "thumbnail_path": None,
    "hook": (
        "Icarus did not die because he wanted the sun. He died because his father "
        "built an escape that only worked if a teenager followed one rule — and then "
        "left him alone in open sky. Yeah. That was the plan."
    ),
    "driving_question": "How does the smartest inventor in Crete design a prison break that kills his own son?",
    "thesis": "The invention was brilliant. The instruction was not a plan.",
    "runtime_seconds": 96,
    "word_count": 248,
    "youtube_description": (
        "The fall of Icarus is usually told as a lecture about ambition. "
        "The older story is colder: a prison, a set of wings, and one rule that could not survive sunlight.\n\n"
        "If you'd rather listen than watch, links are in the description."
    ),
    "tags": ["icarus", "greek mythology", "explained", "daedalus", "story explainer"],
    "chapters": [
        {"time": "0:00", "title": "The real reason he fell"},
        {"time": "0:20", "title": "The prison"},
        {"time": "0:45", "title": "The wings"},
        {"time": "1:10", "title": "The rule"},
    ],
    "full_narration": "",
    "scenes": [
        {
            "id": 1,
            "section": "hook",
            "visual_type": "action",
            "narration": "Icarus did not die because he wanted the sun. He died because the escape only worked if a teenager followed one rule.",
            "on_screen_text": "",
            "duration_seconds": 12,
            "image_prompt": normalize_image_prompt(
                "Boy falling from a blinding sky toward a wine-dark sea, wax dripping from feathered wings"
            ),
            "image_path": None,
        },
        {
            "id": 2,
            "section": "hook",
            "visual_type": "character",
            "narration": "Yeah. That was the plan. Build wings. Jump off a tower. Tell your son not to fly too high. Then hope.",
            "on_screen_text": "",
            "duration_seconds": 10,
            "image_prompt": normalize_image_prompt(
                "Aging inventor Daedalus in a stone workshop, holding a half-built wing, exhausted and brilliant"
            ),
            "image_path": None,
        },
        {
            "id": 3,
            "section": "origin",
            "visual_type": "establishing",
            "narration": "They were locked in the Labyrinth on Crete — right here — the maze Daedalus himself had designed for a king who no longer trusted him.",
            "on_screen_text": "CRETE",
            "duration_seconds": 12,
            "image_prompt": normalize_image_prompt(
                "Aerial antique map of Crete as a dark island in a bronze sea, a palatial maze glowing at the center"
            ),
            "image_path": None,
        },
        {
            "id": 4,
            "section": "origin",
            "visual_type": "insert",
            "narration": "The sea was watched. The roads were watched. The sky was the only door nobody had thought to lock.",
            "on_screen_text": "",
            "duration_seconds": 10,
            "image_prompt": normalize_image_prompt(
                "Minoan tower above cliffs, patrol boats in the cove below, empty sky above the battlements"
            ),
            "image_path": None,
        },
        {
            "id": 5,
            "section": "build",
            "visual_type": "insert",
            "narration": "Daedalus gathered feathers. He melted wax. He built two pairs of wings that could carry a man if the sun stayed polite.",
            "on_screen_text": "",
            "duration_seconds": 12,
            "image_prompt": normalize_image_prompt(
                "Close table of feathers, bronze tools, and a bowl of amber wax in firelight, wings taking shape"
            ),
            "image_path": None,
        },
        {
            "id": 6,
            "section": "build",
            "visual_type": "dialogue",
            "narration": "\"Stay in the middle air. Too low, the spray soaks the feathers. Too high, the sun melts the wax. Do you understand?\" \"I understand.\"",
            "on_screen_text": "",
            "duration_seconds": 14,
            "image_prompt": normalize_image_prompt(
                "Father tying wings onto a teenage son's shoulders on a windy tower, dawn light, tense eye contact"
            ),
            "image_path": None,
        },
        {
            "id": 7,
            "section": "fall",
            "visual_type": "action",
            "narration": "Icarus understood. Then the air worked. The prison shrank. And the one rule that held the whole machine together started to feel optional.",
            "on_screen_text": "",
            "duration_seconds": 13,
            "image_prompt": normalize_image_prompt(
                "Icarus climbing toward a huge sun, wings wide, Crete tiny below, joy turning reckless"
            ),
            "image_path": None,
        },
        {
            "id": 8,
            "section": "lesson",
            "visual_type": "aftermath",
            "narration": "The wings were perfect. The warning was not a design. Sometimes the smartest person in the room builds a door and forgets that a child will run through it.",
            "on_screen_text": "",
            "duration_seconds": 13,
            "image_prompt": normalize_image_prompt(
                "Daedalus circling alone over dark water, one white feather on the waves, empty horizon"
            ),
            "image_path": None,
        },
    ],
}

DEMO_PROJECT["full_narration"] = "\n\n".join(scene["narration"] for scene in DEMO_PROJECT["scenes"])
DEMO_PROJECT["word_count"] = len(DEMO_PROJECT["full_narration"].split())
DEMO_PROJECT["runtime_seconds"] = sum(scene["duration_seconds"] for scene in DEMO_PROJECT["scenes"])

# Keep the style string referenced so imports stay meaningful if the look changes.
assert IMAGE_STYLE in DEMO_PROJECT["thumbnail_prompt"]
