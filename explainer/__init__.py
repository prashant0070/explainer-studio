"""explainer — a spec-driven pipeline for vertical (1080x1920) explainer Shorts.

Takes a YAML/JSON project spec plus an optional voice-over file, word-aligns the
narration, renders code-drawn motion graphics with word-synced captions, mixes and
normalizes audio to -14 LUFS, and exports a master MP4, a phone-friendly share MP4,
a contact sheet and a QA report.
"""

__version__ = "0.1.0"

# Design space. All layout coordinates in shots/render assume this canvas.
W, H = 1080, 1920
