"""Virality prediction for a produced explainer (all local, free).

Answers one question: "Is this video going to go viral, or not?" It scores the
signals that actually drive reach on YouTube — the hook, the title, the
thumbnail line, the cut cadence (retention), the curiosity gap, packaging/SEO,
and, once rendered, the technical QC — into a single 0-100 score with a verdict
band and concrete fixes.

Everything here is deterministic and keyless so it works with no API key, in the
same spirit as the rest of the pipeline. When an LLM key is configured we also
ask for a short editorial second opinion (non-fatal if unavailable).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.llm import LlmClient, LlmError

logger = logging.getLogger(__name__)

# Words that create a curiosity gap or emotional pull in a hook.
_TENSION_WORDS = (
    "but", "until", "because", "not", "never", "no one", "nobody", "wrong",
    "secret", "hidden", "actually", "real reason", "the truth", "mistake",
    "died", "killed", "failed", "forgot", "ignored", "too", "only", "almost",
    "nearly", "should", "never told", "what nobody",
)

# Power words that make a title over-index in the browse feed.
_TITLE_POWER = (
    "entire", "story", "explained", "secret", "truth", "why", "how", "never",
    "real reason", "the day", "the night", "actually", "nobody", "no one",
    "what happened", "the man who", "the woman who", "insane", "genius",
    "disaster", "mystery", "hidden", "before", "inside",
)

_THUMB_PUNCH = (
    "he", "she", "they", "it", "ignored", "warning", "died", "too late",
    "never", "wrong", "secret", "hidden", "the end", "one rule", "gone",
    "lost", "last", "final", "first", "why", "how",
)

_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "it",
    "he", "she", "they", "his", "her", "their", "was", "were", "that", "this",
    "with", "at", "by", "as", "did", "not", "but", "then", "him", "them",
}


def predict(project: Dict[str, Any], qc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Score a project's viral potential. Returns a report dict."""
    qc = qc or project.get("qc")

    titles: List[str] = [t for t in (project.get("titles") or []) if str(t).strip()]
    title_scores = sorted(
        ((t, _score_title(t)) for t in titles),
        key=lambda pair: pair[1],
        reverse=True,
    )
    best_title, best_title_score = (title_scores[0] if title_scores else ("", 0))

    factors: List[Dict[str, Any]] = []
    factors.append(_hook_factor(project))
    factors.append(
        _factor(
            "title", 0.22, best_title_score,
            f'"{_clip(best_title, 60)}" leads {len(titles)} option(s)'
            if best_title else "No title written yet",
            "Lead with a curiosity gap: a surprising claim the viewer must click to resolve.",
        )
    )
    factors.append(_thumbnail_factor(project))
    factors.append(_pacing_factor(project))
    factors.append(_curiosity_factor(project))
    factors.append(_packaging_factor(project))
    prod = _production_factor(qc)
    if prod is not None:
        factors.append(prod)

    total_weight = sum(f["weight"] for f in factors) or 1.0
    score = round(sum(f["score"] * f["weight"] for f in factors) / total_weight)
    verdict, label = _band(score)

    ranked = sorted(factors, key=lambda f: f["score"])
    suggestions = [f["tip"] for f in ranked if f["score"] < 70][:3]
    if not suggestions:
        suggestions = ["Strong across the board — ship it and test the top two titles."]

    summary = f"{score}/100 · " + " · ".join(
        f"{f['name']} {f['score']}" for f in factors
    )

    report: Dict[str, Any] = {
        "score": score,
        "verdict": verdict,
        "label": label,
        "summary": summary,
        "factors": factors,
        "best_title": best_title,
        "title_scores": [
            {"title": t, "score": s} for t, s in title_scores
        ],
        "suggestions": suggestions,
    }

    review = _llm_review(report, project)
    if review:
        report["llm_review"] = review
    return report


# --------------------------------------------------------------------- factors


def _hook_factor(project: Dict[str, Any]) -> Dict[str, Any]:
    hook = str(project.get("hook") or "").strip()
    if not hook:
        first = (project.get("scenes") or [{}])[0]
        hook = str(first.get("narration") or "").strip()
    words = hook.split()
    n = len(words)

    # Spoken hooks land best around 40-70 words (~12-20s of narration).
    length_score = _window(n, lo=40, hi=70, floor=12, ceil=110)

    low = hook.lower()
    tension = sum(1 for w in _TENSION_WORDS if w in low)
    tension_score = min(100, tension * 22)
    specifics = 100 if re.search(r"\d", hook) else 45
    question = 100 if "?" in hook else 55
    # First sentence should be short and punchy.
    first_sentence = re.split(r"(?<=[.!?])\s", hook)[0] if hook else ""
    punch = _window(len(first_sentence.split()), lo=4, hi=16, floor=1, ceil=40)

    score = round(
        0.34 * length_score
        + 0.30 * tension_score
        + 0.14 * specifics
        + 0.10 * question
        + 0.12 * punch
    )
    detail = f"{n} words, {tension} tension cue(s)" + (
        ", has a number" if specifics == 100 else ", no concrete number"
    )
    return _factor(
        "hook", 0.26, score, detail,
        "Sharpen the first 12-20s: one surprising cause, a short punchy opener, and a concrete number.",
    )


def _score_title(title: str) -> int:
    t = str(title or "").strip()
    if not t:
        return 0
    chars = len(t)
    length_score = _window(chars, lo=30, hi=62, floor=10, ceil=100)
    low = t.lower()
    power = sum(1 for w in _TITLE_POWER if w in low)
    power_score = min(100, 30 + power * 26)
    number_score = 100 if re.search(r"\d", t) else 60
    # ALL-CAPS shouting reads as spam; a little emphasis is fine.
    letters = [c for c in t if c.isalpha()]
    caps_ratio = sum(1 for c in letters if c.isupper()) / max(1, len(letters))
    caps_score = 55 if caps_ratio > 0.6 else 100
    return round(
        0.34 * length_score
        + 0.40 * power_score
        + 0.14 * number_score
        + 0.12 * caps_score
    )


def _thumbnail_factor(project: Dict[str, Any]) -> Dict[str, Any]:
    text = str(project.get("thumbnail_text") or "").strip()
    words = text.split()
    n = len(words)
    if not text:
        return _factor(
            "thumbnail", 0.14, 30, "No thumbnail line set",
            "Add a 3-6 word thumbnail line that creates a question ('HE IGNORED THE WARNING').",
        )
    length_score = _window(n, lo=3, hi=6, floor=1, ceil=12)
    low = text.lower()
    punch = sum(1 for w in _THUMB_PUNCH if w in low)
    punch_score = min(100, 45 + punch * 25)
    score = round(0.55 * length_score + 0.45 * punch_score)
    return _factor(
        "thumbnail", 0.14, score, f'"{_clip(text, 40)}" ({n} words)',
        "Keep the thumbnail to 3-6 punchy words that open a curiosity gap.",
    )


def _pacing_factor(project: Dict[str, Any]) -> Dict[str, Any]:
    scenes = project.get("scenes") or []
    durations = [float(s.get("duration_seconds") or 0) for s in scenes if s.get("duration_seconds")]
    if not durations:
        return _factor(
            "pacing", 0.16, 40, "No scene timings yet",
            "Cut every 8-18s — a new picture per beat keeps retention high.",
        )
    in_band = sum(1 for d in durations if 8 <= d <= 18)
    band_score = round(100 * in_band / len(durations))
    avg = sum(durations) / len(durations)
    avg_score = _window(avg, lo=9, hi=15, floor=4, ceil=30)
    score = round(0.6 * band_score + 0.4 * avg_score)
    return _factor(
        "pacing", 0.16, score,
        f"{len(durations)} cuts, avg {avg:.1f}s, {in_band}/{len(durations)} in the 8-18s band",
        "Tighten slow scenes: aim for a fresh visual every 8-18 seconds.",
    )


def _curiosity_factor(project: Dict[str, Any]) -> Dict[str, Any]:
    dq = str(project.get("driving_question") or "").strip()
    thesis = str(project.get("thesis") or "").strip()
    hook = str(project.get("hook") or "").strip()

    dq_score = 100 if dq.endswith("?") else (65 if dq else 25)
    thesis_score = 90 if thesis else 30
    # Payoff: does the closing thesis echo words planted in the hook?
    payoff = _overlap(hook, thesis)
    payoff_score = min(100, 45 + payoff * 18)
    score = round(0.4 * dq_score + 0.3 * thesis_score + 0.3 * payoff_score)
    detail = ("driving question set" if dq else "no driving question") + (
        ", thesis pays off the hook" if payoff >= 2 else ", weak hook↔thesis payoff"
    )
    return _factor(
        "curiosity", 0.12, score, detail,
        "State one driving question early and pay it off with a thesis that echoes the hook.",
    )


def _packaging_factor(project: Dict[str, Any]) -> Dict[str, Any]:
    tags = project.get("tags") or []
    desc = str(project.get("youtube_description") or "")
    chapters = project.get("chapters") or []
    tag_score = _window(len(tags), lo=6, hi=15, floor=0, ceil=30)
    desc_score = _window(len(desc.split()), lo=25, hi=120, floor=0, ceil=400)
    chapter_score = 100 if len(chapters) >= 3 else (60 if chapters else 20)
    score = round(0.4 * tag_score + 0.35 * desc_score + 0.25 * chapter_score)
    return _factor(
        "packaging", 0.06, score,
        f"{len(tags)} tags, {len(chapters)} chapters, {len(desc.split())}-word description",
        "Add 8-12 tags, a 2-paragraph description, and at least 3 chapters for search + session time.",
    )


def _production_factor(qc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not qc:
        return None
    verdict = str(qc.get("verdict") or "").lower()
    base = {"pass": 92, "warn": 68, "fail": 35}.get(verdict, 55)
    return _factor(
        "production", 0.06, base,
        f"QC {verdict.upper() or '?'} · {_clip(str(qc.get('summary') or ''), 60)}",
        "Fix QC warnings (loudness, dead air, black frames) — technical drag hurts retention.",
    )


# ----------------------------------------------------------------------- helpers


def _factor(name: str, weight: float, score: int, detail: str, tip: str) -> Dict[str, Any]:
    score = int(max(0, min(100, score)))
    status = "pass" if score >= 70 else ("warn" if score >= 45 else "fail")
    return {
        "name": name,
        "weight": weight,
        "score": score,
        "status": status,
        "detail": detail,
        "tip": tip,
    }


def _band(score: int) -> Tuple[str, str]:
    if score >= 80:
        return "high", "High viral potential"
    if score >= 65:
        return "strong", "Strong — likely to over-index"
    if score >= 45:
        return "medium", "Medium — solid, not a breakout"
    return "low", "Low — needs a sharper hook and title"


def _window(value: float, lo: float, hi: float, floor: float, ceil: float) -> int:
    """100 inside [lo, hi], sloping linearly to 0 at floor/ceil outside it."""
    if lo <= value <= hi:
        return 100
    if value < lo:
        if value <= floor:
            return 0
        return round(100 * (value - floor) / (lo - floor))
    if value >= ceil:
        return 0
    return round(100 * (ceil - value) / (ceil - hi))


def _overlap(a: str, b: str) -> int:
    wa = {w for w in re.findall(r"[a-z]{4,}", a.lower()) if w not in _STOP}
    wb = {w for w in re.findall(r"[a-z]{4,}", b.lower()) if w not in _STOP}
    return len(wa & wb)


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _llm_review(report: Dict[str, Any], project: Dict[str, Any]) -> Optional[str]:
    client = LlmClient()
    if not client.enabled:
        return None
    factor_lines = [
        f"- {f['name']}: {f['score']}/100 — {f['detail']}" for f in report.get("factors", [])
    ]
    try:
        return client.chat(
            "You are a YouTube growth strategist. Given a video's packaging signals and a "
            "computed virality score, write 3-5 sentences: will it go viral or not, the single "
            "biggest lever to raise the score, and one concrete rewrite (hook or title). Plain text.",
            f"Best title: {report.get('best_title')}\n"
            f"Hook: {project.get('hook')}\n"
            f"Computed score: {report.get('score')}/100 ({report.get('label')})\n"
            f"Factors:\n" + "\n".join(factor_lines),
            temperature=0.5,
        ).strip()
    except LlmError as exc:
        logger.warning("LLM virality review unavailable: %s", exc)
        return None
