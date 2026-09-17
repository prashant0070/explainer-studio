"""Niche Intel: what top channels do, what went viral, what people search, 10 topics.

Demand signal is Wikipedia pageviews (keyless, free). Channel patterns for the
cinematic story-explainer niche are curated from public 2025–2026 performance
and then adapted by the LLM when a key is present.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from app.llm import LlmClient, LlmError

logger = logging.getLogger(__name__)

WIKI_PV = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "en.wikipedia/all-access/all-agents/{article}/monthly/{start}/{end}"
)
USER_AGENT = "ExplainerStudio/1.0 (open-source research tool)"
PV_START, PV_END = "2025080100", "2026083100"


# Public, cited channel patterns for THIS product's niche. Numbers are
# approximate snapshots from Aug–Sep 2026 indexing (Social Blade / vidIQ /
# YouTube page metadata) — used as briefing, never invented per-run.
CHANNEL_PATTERNS = [
    {
        "channel": "Dreamoria",
        "pattern": "3-hour 'ENTIRE Story of [mythology]' sleep documentaries",
        "proof": "The ENTIRE Story of Greek Mythology — ~5.6M views",
        "takeaway": "Omnibus 'entire mythology' titles print views, but they win on duration-for-sleep, not retention. Our cut is 8–15 min with a causal hook — same title grammar, different job.",
    },
    {
        "channel": "See U in History / Mythology",
        "pattern": "Animated recap of one epic, thumbnail of a monster or a fall",
        "proof": "The Epic of Gilgamesh — 3.75M views (68× channel average)",
        "takeaway": "Gilgamesh is the sleeper hit of the niche. Greek recaps still work; Sumerian/Mesopotamian is where outliers live.",
    },
    {
        "channel": "Deep Dive History",
        "pattern": "Premium-voiced 'The Entire Story' of one epic, chaptered, no jokes",
        "proof": "THE EPIC OF GILGAMESH — The Entire Story — 567K views in ~1 month (Jul 2026)",
        "takeaway": "New channels can still mint a Gilgamesh video. The format is not exhausted — the Odyssey copies are.",
    },
    {
        "channel": "Bedtime & Historian / similar sleep channels",
        "pattern": "Calm Odyssey retell, 10-year journey, no thesis",
        "proof": "The Odyssey Explained | Complete Story — 304K in ~1 month",
        "takeaway": "Odyssey still searches. It does not differentiate. We only touch it with a NEW causal angle, never a retell.",
    },
    {
        "channel": "Wendigoon / The Why Files (Dark Vault lane)",
        "pattern": "One incident, rising evidence, uncomfortable counter-explanation, no jump scares",
        "proof": "Yuba County Five 2.7M; Petscop 1.7M; Church Rock 1.3M — 4.7M-sub channel, 300–600K views/day",
        "takeaway": "Investigation beats lecture. Open on a concrete case, then widen. Historical disasters and unsolved vanishings convert.",
    },
]

DEMAND_CANDIDATES = [
    "Epic_of_Gilgamesh",
    "Aeneid",
    "Beowulf",
    "Ramayana",
    "Mahabharata",
    "Journey_to_the_West",
    "Ragnarök",
    "Inanna",
    "Late_Bronze_Age_collapse",
    "Year_Without_a_Summer",
    "Dancing_plague_of_1518",
    "Shahnameh",
    "Popol_Vuh",
    "Cú_Chulainn",
    "Kalevala",
    "Sundiata_Keita",
    "Göbekli_Tepe",
    "Franklin's_lost_expedition",
    "Voynich_manuscript",
    "Hypatia",
    "Taiping_Rebellion",
    "Nika_riots",
    "Doggerland",
    "Erysichthon",
    "Odyssey",
    "Iliad",
    "Norse_mythology",
]

# Ranked for THIS studio: high search × cinematic hook × not a dead Odyssey clone.
TEN_TOPICS: List[Dict[str, Any]] = [
    {
        "rank": 1,
        "topic": "The Epic of Gilgamesh",
        "title": "He Became Immortal's Opposite — The ENTIRE Story of Gilgamesh",
        "hook": "The oldest story on earth exists because the gods built a wild man to humble a tyrant — then killed the friend, and sent a king walking to the end of the world for a plant he would lose in his sleep.",
        "style": "odyssey",
        "demand": "1.63M Wikipedia views in 12 months, rising (143K in Aug 2026). See U in History's Gilgamesh is 68× their average. A July 2026 'entire story' upload did 567K in a month. Search is hot; English cinematic 12-minute versions are thin.",
        "why": "Highest-upside epic in the niche that is not Odyssey. Flood tablet, Humbaba, Ishtar's rejection, Utnapishtim, the snake — every scene is a painting.",
        "gap": "Overserved as a 40-min lecture. Underserved as a hook-first 12-minute cut.",
    },
    {
        "rank": 2,
        "topic": "The Aeneid — what happened to the Trojans who lived",
        "title": "Rome Exists Because One Trojan Refused to Die",
        "hook": "The Odyssey is the winner's way home. The Aeneid is the loser's: a man carrying his father out of a burning city founds an empire because he would not stay and burn with Troy.",
        "style": "odyssey",
        "demand": "909K Wikipedia views, sharply up (141K in Aug 2026 vs ~90K a year earlier). Odyssey itself is 9M — saturated. Aeneas rides the same search cluster with almost no 'ENTIRE Story of' clones.",
        "why": "Viewers who watched an Odyssey explainer are one click from 'what about the other side?' Dido, the underworld, the shield of Rome — visual as Homer.",
        "gap": "School summaries exist. A cinematic causal-hook version does not.",
    },
    {
        "rank": 3,
        "topic": "Beowulf",
        "title": "The Dragon Woke Because a Slave Stole a Cup",
        "hook": "Beowulf did not die fighting Grendel. He died as an old king because a terrified slave lifted one gold cup from a barrow, and a dragon that had slept three hundred years remembered it was owed.",
        "style": "odyssey",
        "demand": "1.13M Wikipedia views, steady ~88K/month. Always-on classroom + fantasy search. English 'entire story' videos skew academic or 3-hour sleep, not hook-first.",
        "why": "Three monsters, three ages of one man, one stolen cup. The ending is the lesson the format was built for.",
        "gap": "Everyone knows Grendel. Almost nobody leads with the cup.",
    },
    {
        "rank": 4,
        "topic": "The Ramayana",
        "title": "A Kingdom Fell Because a King Kept One Promise to a Jealous Wife",
        "hook": "Fourteen years of exile, a kidnapped queen, and a war that burned Lanka happened because an aging king would not break a vow he should never have made.",
        "style": "odyssey",
        "demand": "1.30M Wikipedia views, rising (138K in Aug 2026). Massive global search; English cinematic explainers are far thinner than Hindi/Tamil ones. Diaspora + mythology YouTube is hungry.",
        "why": "Sita, Hanuman, Ravana, the golden deer — every beat is a 16:9 painting. Causal hook is Kaikeyi's boon, not 'good vs evil'.",
        "gap": "Devotional retells dominate. A dry, Odyssey-voiced causal cut is rare in English.",
    },
    {
        "rank": 5,
        "topic": "Journey to the West — why Heaven couldn't kill the Monkey King",
        "title": "They Gave Him a Pilgrimage Because They Couldn't Kill Him",
        "hook": "Sun Wukong stormed heaven, erased his name from the book of the dead, and survived the furnace of the immortal. The journey for the scriptures was not a reward. It was the only prison that fit.",
        "style": "odyssey",
        "demand": "797K Wikipedia views, flat-high. Black Myth: Wukong (2024–26) dumped a new audience onto the 16th-century novel. Searchers want the original story, not the game.",
        "why": "Game traffic + 500-year-old plot + a trickster who cannot die. Visuals write themselves.",
        "gap": "Game lore videos own the query. The actual novel, told as one causal story, is open.",
    },
    {
        "rank": 6,
        "topic": "Ragnarök",
        "title": "The Gods Walked Into the End of the World on Purpose",
        "hook": "Odin hung on the world-tree for nine nights to learn the runes, and what he learned was the date of his own death. Ragnarök is not a surprise. It is an appointment the gods kept.",
        "style": "odyssey",
        "demand": "527K Wikipedia views. Norse search is perennial (Thor, Loki, God of War). 'Entire story of Ragnarök' is crowded with listicles; the 'they knew' angle is not.",
        "why": "Fenrir, Jörmungandr, Baldur's mistletoe, the ship of nails — peak cinematic. The hook is knowledge, not spectacle.",
        "gap": "Marvel and God of War ate the surface. The Poetic Edda's fatalism is still unused.",
    },
    {
        "rank": 7,
        "topic": "Inanna's descent to the underworld",
        "title": "The Queen of Heaven Walked Into Hell Naked on Purpose",
        "hook": "At each of seven gates they took a piece of her power — crown, beads, breastplate — until the goddess of love hung as a corpse on a hook. She had come to take her sister's throne.",
        "style": "odyssey",
        "demand": "Inanna/Ishtar sits under Gilgamesh's search umbrella but has almost no English 'entire story' videos. Sumerian revival is riding Gilgamesh's spike.",
        "why": "Seven gates = seven scenes. Stripping, death, the fly, Dumuzi's substitution — a complete 8-minute tragedy.",
        "gap": "Academic tellings only. This is the rare myth that is already structured like our scene list.",
    },
    {
        "rank": 8,
        "topic": "The Late Bronze Age collapse",
        "title": "Every Palace From Greece to Egypt Burned in One Generation",
        "hook": "In the same lifetime, Mycenae, Ugarit, Hattusa and a dozen other palaces went dark. The last clay tablets from Ugarit say the ships are on the horizon. Then the writing stops.",
        "style": "dark_vault",
        "demand": "Sea Peoples + Late Bronze Age collapse is a steady education query with spikes whenever a new paper lands. Wendigoon-adjacent audience already watches collapse content.",
        "why": "Maps, burning palaces, unread Linear B, a letter that never arrived. Investigation voice, not sermon. The honest ending is: we still do not know which cause was first.",
        "gap": "Documentaries run 50 minutes and hedge. A 12-minute 'here is the last letter' cut does not exist in this style.",
    },
    {
        "rank": 9,
        "topic": "The Year Without a Summer — Tambora, 1816",
        "title": "A Volcano in Indonesia Invented Frankenstein",
        "hook": "Mount Tambora killed so much sunlight that 1816 had no summer. Crops failed from China to New England. In a rain-trapped villa on Lake Geneva, Mary Shelley sat down and invented a man who should not have been alive.",
        "style": "dark_vault",
        "demand": "Year Without a Summer + Tambora is a reliable curiosity query; Frankenstein search is enormous and seasonal. The causal chain between them is rarely the title.",
        "why": "Ash, red snow, famine, Byron, the villa, the creature. One cause, one lesson, cinematic weather.",
        "gap": "Climate explainers and Frankenstein biographies are separate videos. The join is the video.",
    },
    {
        "rank": 10,
        "topic": "The dancing plague of 1518",
        "title": "The Doctors Ordered Them to Dance, and They Danced Until They Died",
        "hook": "In Strasbourg, a woman started dancing in the street and would not stop. Within a month, hundreds had joined. The physicians' prescription was more dancing. Some of them danced themselves to death.",
        "style": "dark_vault",
        "demand": "Evergreen weird-history search (ergot, mass psychogenic illness, 'unexplained'). Short, complete, visually grotesque in a painterly way — perfect 8-minute Dark Vault.",
        "why": "One city, one month, one medical mistake. Opens cold, never resolves cleanly (ergot vs. hysteria vs. stress), which is the Dark Vault ending.",
        "gap": "List-video fodder ('10 weirdest plagues'). A single-incident investigation with a thesis is open.",
    },
]


class IntelError(RuntimeError):
    pass


def analyze_niche(niche: str, count: int = 10) -> Dict[str, Any]:
    """Return patterns, demand, and ranked topics for a niche description."""
    demand = _demand_snapshot(DEMAND_CANDIDATES)
    briefing = {
        "niche": niche.strip() or "cinematic story explainers and investigative documentaries",
        "patterns": CHANNEL_PATTERNS,
        "search": {
            "method": "English Wikipedia pageviews, Aug 2025–Aug 2026 (proxy for what people look up)",
            "headline": (
                "Odyssey is the monster query (9.0M views, still rising). "
                "Iliad 3.1M, Gilgamesh 1.63M and rising, Ramayana 1.30M rising, "
                "Beowulf 1.13M, Aeneid 0.91M rising fast, Journey to the West 0.80M, "
                "Ragnarök 0.53M. The Odyssey slot is crowded. The next-epic slots are not."
            ),
            "rows": demand[:16],
        },
        "what_clicks": [
            "Title grammar: 'The ENTIRE Story of X Explained' + a causal subtitle, not a summary subtitle.",
            "Thumbnail: one figure in trouble, amber/teal, no text-heavy maps.",
            "First 15 seconds: the whole story happened because of ONE mistake or bargain.",
            "Cuts every 8–18 seconds. New picture every cut.",
            "Sleep-omnibus (2–3h) wins raw views; 8–15 min hook-first wins subscriber conversion for a new channel.",
            "Do not retell the Odyssey unless the angle is genuinely new. The copies are already up.",
        ],
        "topics": list(TEN_TOPICS)[:count],
    }

    client = LlmClient()
    if client.enabled and niche.strip():
        try:
            briefing["topics"] = _llm_topics(client, niche, demand, count) or briefing["topics"]
        except (LlmError, IntelError) as exc:
            logger.warning("LLM niche synthesis skipped: %s", exc)

    return briefing


def _demand_snapshot(slugs: List[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    headers = {"User-Agent": USER_AGENT}
    try:
        with httpx.Client(timeout=8.0, headers=headers) as client:
            for slug in slugs[:12]:
                try:
                    url = WIKI_PV.format(
                        article=quote(slug, safe="_"), start=PV_START, end=PV_END
                    )
                    response = client.get(url)
                    if response.status_code == 429:
                        break
                    if response.status_code != 200:
                        continue
                    items = response.json().get("items") or []
                    if not items:
                        continue
                    views = sum(int(i.get("views") or 0) for i in items)
                    last = int(items[-1].get("views") or 0)
                    first = int(items[0].get("views") or 0)
                    if last > first * 1.15:
                        trend = "up"
                    elif last < first * 0.85:
                        trend = "down"
                    else:
                        trend = "flat"
                    rows.append(
                        {
                            "topic": slug.replace("_", " "),
                            "views_12m": views,
                            "last_month": last,
                            "trend": trend,
                        }
                    )
                except httpx.HTTPError:
                    continue
    except httpx.HTTPError as exc:
        logger.warning("Wikipedia pageviews unavailable: %s", exc)
    rows.sort(key=lambda r: -r["views_12m"])
    return rows


def _llm_topics(
    client: LlmClient, niche: str, demand: List[Dict[str, Any]], count: int
) -> Optional[List[Dict[str, Any]]]:
    demand_lines = "\n".join(
        f"- {r['topic']}: {r['views_12m']} views/year, last month {r['last_month']}, trend {r['trend']}"
        for r in demand[:20]
    ) or "(no pageview data this run)"
    pattern_lines = "\n".join(
        f"- {p['channel']}: {p['pattern']} ({p['proof']})" for p in CHANNEL_PATTERNS
    )
    data = client.chat_json(
        "You are a YouTube strategist for cinematic story-explainer and investigative "
        "documentary channels. Prefer stories with one surprising cause, a visual "
        "escalation, and a lesson. Never invent view counts. Return ONLY valid JSON.",
        f"""NICHE: {niche.strip()}

WHAT TOP CHANNELS ARE DOING:
{pattern_lines}

WHAT PEOPLE ARE LOOKING UP (Wikipedia pageviews, last 12 months):
{demand_lines}

Propose {count} video topics. Rank by (search demand × how well it fits the niche ×
how unsaturated the 'entire story explained' slot is). Skip a straight Odyssey retell.

JSON schema:
{{"ideas": [{{"rank": 1, "topic": "...", "title": "clickable title",
"hook": "one-sentence causal hook", "style": "odyssey|dark_vault",
"demand": "why this is being searched/clicked", "why": "why it fascinates",
"gap": "what existing videos miss"}}]}}""",
        temperature=0.7,
    )
    ideas = data.get("ideas")
    if not isinstance(ideas, list) or not ideas:
        return None
    cleaned: List[Dict[str, Any]] = []
    for index, idea in enumerate(ideas[:count], start=1):
        if not isinstance(idea, dict) or not idea.get("topic"):
            continue
        cleaned.append(
            {
                "rank": index,
                "topic": str(idea.get("topic", "")).strip(),
                "title": str(idea.get("title", "")).strip(),
                "hook": str(idea.get("hook", "")).strip(),
                "style": "dark_vault" if idea.get("style") == "dark_vault" else "odyssey",
                "demand": str(idea.get("demand", "")).strip(),
                "why": str(idea.get("why", "")).strip(),
                "gap": str(idea.get("gap", "")).strip(),
            }
        )
    return cleaned or None
