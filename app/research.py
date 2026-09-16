"""Niche/topic research: free Wikipedia grounding + LLM synthesis.

Two entry points:
- suggest_topics(niche): channel-fit video ideas for a niche or channel description.
- research_topic(topic): a fact-grounded research brief that is fed into the
  script generator as source notes (keeps the model from inventing details).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from app.llm import LlmClient, LlmError

logger = logging.getLogger(__name__)

WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "ExplainerStudio/1.0 (open-source research tool)"


class ResearchError(RuntimeError):
    pass


def suggest_topics(niche: str, count: int = 6) -> List[Dict[str, str]]:
    client = LlmClient()
    if not client.enabled:
        raise ResearchError("Set LLM_API_KEY to research topics")
    data = client.chat_json(
        "You are a YouTube strategist for story-explainer and investigative documentary "
        "channels. You propose specific, high-retention video topics with a causal hook. "
        "Return ONLY valid JSON.",
        f"""Channel / niche description:
{niche.strip()}

Propose {count} video ideas that fit this niche. Prefer stories with one surprising
cause, a clear escalation, and a lesson. Avoid topics that need recent statistics.

JSON schema:
{{"ideas": [{{"topic": "...", "title": "clickable title", "hook": "one-sentence causal hook",
"style": "odyssey|dark_vault", "why": "why this works for the niche"}}]}}""",
        temperature=0.9,
    )
    ideas = data.get("ideas")
    if not isinstance(ideas, list) or not ideas:
        raise ResearchError("Model returned no ideas")
    cleaned = []
    for idea in ideas[:count]:
        if isinstance(idea, dict) and idea.get("topic"):
            cleaned.append(
                {
                    "topic": str(idea.get("topic", "")).strip(),
                    "title": str(idea.get("title", "")).strip(),
                    "hook": str(idea.get("hook", "")).strip(),
                    "style": "dark_vault" if idea.get("style") == "dark_vault" else "odyssey",
                    "why": str(idea.get("why", "")).strip(),
                }
            )
    return cleaned


def research_topic(topic: str) -> Dict[str, Any]:
    """Free web grounding (Wikipedia) condensed by the LLM into source notes."""
    sources = wikipedia_extracts(topic)
    client = LlmClient()
    if not client.enabled:
        raise ResearchError("Set LLM_API_KEY to run research")

    source_block = "\n\n".join(
        f"[{s['title']}] {s['extract']}" for s in sources
    ) or "(no encyclopedia sources found — rely on well-established knowledge only)"

    data = client.chat_json(
        "You are a research editor for a documentary channel. Extract only verifiable, "
        "story-usable facts. Never invent statistics, quotes, or dates. Mark disputed "
        "points. Return ONLY valid JSON.",
        f"""TOPIC: {topic.strip()}

ENCYCLOPEDIA EXTRACTS:
{source_block[:9000]}

Produce a research brief for a scriptwriter.

JSON schema:
{{"summary": "3-4 sentence overview",
"facts": ["specific fact with names/numbers", "..."],
"timeline": ["chronological beat", "..."],
"disputed": ["claims that are uncertain or contested"],
"angle_ideas": ["one-sentence causal hooks the story supports"]}}""",
        temperature=0.4,
    )
    return {
        "topic": topic.strip(),
        "summary": str(data.get("summary", "")).strip(),
        "facts": _str_list(data.get("facts")),
        "timeline": _str_list(data.get("timeline")),
        "disputed": _str_list(data.get("disputed")),
        "angle_ideas": _str_list(data.get("angle_ideas")),
        "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
    }


def notes_from_research(research: Dict[str, Any]) -> str:
    """Flatten a research brief into the generator's source-notes field."""
    lines: List[str] = []
    if research.get("summary"):
        lines += ["OVERVIEW:", research["summary"], ""]
    if research.get("facts"):
        lines.append("VERIFIED FACTS:")
        lines += [f"- {fact}" for fact in research["facts"]]
        lines.append("")
    if research.get("timeline"):
        lines.append("TIMELINE:")
        lines += [f"- {beat}" for beat in research["timeline"]]
        lines.append("")
    if research.get("disputed"):
        lines.append("DISPUTED (flag in narration if used):")
        lines += [f"- {claim}" for claim in research["disputed"]]
    return "\n".join(lines).strip()


def wikipedia_extracts(topic: str, limit: int = 3) -> List[Dict[str, str]]:
    """Keyless Wikipedia search + intro extracts. Failure is non-fatal."""
    try:
        with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
            search = client.get(
                WIKI_API,
                params={
                    "action": "query", "list": "search", "srsearch": topic,
                    "srlimit": limit, "format": "json",
                },
            )
            search.raise_for_status()
            hits = (search.json().get("query") or {}).get("search") or []
            if not hits:
                return []
            titles = "|".join(h["title"] for h in hits[:limit])
            extracts = client.get(
                WIKI_API,
                params={
                    "action": "query", "prop": "extracts", "titles": titles,
                    "exintro": 0, "explaintext": 1, "exchars": 2400, "format": "json",
                },
            )
            extracts.raise_for_status()
            pages = ((extracts.json().get("query") or {}).get("pages") or {}).values()
            out = []
            for page in pages:
                if page.get("extract"):
                    title = page.get("title", "")
                    out.append(
                        {
                            "title": title,
                            "extract": page["extract"],
                            "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                        }
                    )
            return out
    except httpx.HTTPError as exc:
        logger.warning("Wikipedia lookup failed (continuing without): %s", exc)
        return []


def _str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()][:20]
