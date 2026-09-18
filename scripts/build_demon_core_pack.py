"""Full 12-minute Demon Core production pack — hand-authored from verified sources.

Facts grounded in Wikipedia (Demon core, Louis Slotin, Harry Daghlian) and
established Manhattan Project criticality-accident history.
Voice: science-style Odyssey explainer with dry human humor.
Target: ~10–12 min spoken (~1500–1750 words), ~40 scenes.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.prompts import normalize_image_prompt
from app.slate import mark_project
from app.store import load_project, save_project

LOOK = "science"
SLATE_ID = "sci-02-they-held-a-bomb-core-apart-with-a-screw"
EXISTING_ID = "3f710b18eeae"  # reuse if present so the queue stays linked


def S(section: str, visual: str, seconds: int, narration: str, image: str) -> Dict[str, Any]:
    return {
        "section": section,
        "visual_type": visual,
        "duration_seconds": seconds,
        "narration": narration,
        "image_prompt": image,
    }


SCENES: List[Dict[str, Any]] = [
    S("hook", "instrument close-up", 15,
      "In May of nineteen forty-six, a Canadian physicist held two halves of a bomb apart with a flathead screwdriver. Not metaphorically. Literally. The screwdriver was the only thing between a quiet sphere of plutonium and a room full of people about to get the worst physics demonstration of their lives.",
      "Close-up of a flathead screwdriver wedged between two polished beryllium hemispheres over a small metallic sphere on a lab table, 1940s Los Alamos laboratory, tense shallow focus"),
    S("hook", "portrait", 12,
      "His name was Louis Slotin. Thirty-five years old. Brilliant. Experienced. And, on this particular afternoon, apparently convinced that a tool from a hardware drawer was a reasonable substitute for a safety shim. Yeah. That was the plan.",
      "1940s portrait of a young confident physicist in a white lab coat beside nuclear instruments, amber tungsten light, teal shadows, period-accurate Los Alamos laboratory"),
    S("hook", "action", 13,
      "The whole story happened because the United States built a third atomic core for Japan, Japan surrendered first, and nobody wanted to throw away fourteen pounds of plutonium that already knew how to end a city.",
      "Night exterior of the Los Alamos mesa laboratory complex in 1945, guard posts and low buildings under a cold New Mexico sky, cinematic establishing shot"),
    S("stakes", "insert", 12,
      "So they kept it. Six point two kilograms. Eighty-nine millimeters across. A plutonium–gallium alloy sphere — soft enough to machine into the shape they needed, heavy enough to ruin your entire week if you treated it like a paperweight.",
      "A small silvery-gray plutonium-gallium sphere resting in thick gloved hands over a dark lab cloth, 1945 scientific still life, no readable text"),
    S("stakes", "establishing", 14,
      "It was manufactured in nineteen forty-five by the Manhattan Project. Same family as the cores that went into the bombs used on Japan. This one was lined up for a possible third shot in the Pacific. Then the war ended. The core did not get the memo that the emergency was over.",
      "1945 Pacific embarkation suggestion: crates and military transport silhouettes at dusk, contrasted with a small sealed core container, cinematic period scene"),
    S("stakes", "action", 12,
      "Los Alamos kept it for testing. Potential later use. Scientific curiosity. The usual reasons institutions give when they have a leftover apocalypse and a schedule.",
      "Interior of a Los Alamos storage and experiment bay, lead-lined containers, instrument racks, amber hanging lamps, teal shadows"),
    S("setup", "establishing", 14,
      "Here's the driving question. How do some of the smartest people alive build a weapon that can erase a city… and then decide the best way to test the leftover heart of it is with bricks, bare hands, and a screwdriver?",
      "Wide shot of a sparse 1940s nuclear laboratory at Omega Site, bare walls, instrument racks, a single assembly table under a hanging lamp"),
    S("setup", "insert", 13,
      "Criticality is not a vibe. It is a threshold. Surround a near-critical core with a neutron reflector — dense metal that bounces neutrons back in — and the chain reaction can feed itself. Cross that line and the room stops being a laboratory. It becomes a radiation event with furniture.",
      "Painted cutaway suggestion of a plutonium sphere inside a reflective metal shell with subtle blue glow, scientific cinematic illustration without diagrams or text"),
    S("setup", "instrument close-up", 12,
      "They called these experiments 'tickling the dragon's tail.' Which is already the kind of nickname that should make a grown adult put the coffee down and go home. If your lab slang involves poking a dragon, the dragon is winning the branding war.",
      "Physicists around a criticality assembly table at night, neutron counters and cables, one man leaning over reflective metal hemispheres, 1940s Omega Site atmosphere"),
    S("setup", "portrait", 14,
      "The first man to lose that bet was not Slotin. It was Harry Daghlian. Twenty-four years old. Armenian-American. Quiet. Careful. The kind of physicist who stays late because the measurement is almost finished — not because he wants a legend attached to his name.",
      "Young 1940s physicist alone at night in a remote lab, stack of tungsten carbide bricks beside a small metal core, amber lamp light, contemplative mood"),
    S("daghlian", "establishing", 15,
      "August twenty-first, nineteen forty-five. Omega Site, out in the Los Alamos backcountry. The war is over by days, not years. Daghlian is building a stack of tungsten carbide bricks around the core to see how close it sits to criticality. Alone. After hours. Because 'don't do nuclear physics by yourself at night' was still somehow a soft suggestion.",
      "Night scene: physicist carefully stacking dark tungsten carbide bricks in a ring around a small sphere on a table, remote desert lab, single overhead lamp"),
    S("daghlian", "action", 12,
      "He reaches for another brick. He drops it. It lands wrong. The reflecting mass closes around the core. The assembly goes supercritical. There is a blue flash. Not a metaphor. A flash.",
      "Sudden blue-white flash illuminating a 1940s lab table as a brick falls onto a reflective assembly around a plutonium core, frozen instant of accident"),
    S("daghlian", "action", 13,
      "He knocks the brick away with his bare hand. The reaction stops. Good news: the dragon goes back to sleep. Bad news: the dragon already bit him. He has just absorbed a dose his body will spend the next twenty-five days failing to outrun.",
      "Empty criticality table after an accident, scattered tungsten carbide bricks, overturned instruments, eerie quiet amber and teal light"),
    S("daghlian", "aftermath", 14,
      "A security guard nearby also receives a significant dose. Distance matters. Physics is ruthless about seating charts. Daghlian is hospitalized. His hand — the one that pushed the brick — becomes a map of what invisible damage looks like when it finally becomes visible.",
      "1940s hospital corridor at night, empty gurney light spilling from a doorway, somber documentary atmosphere, no gore"),
    S("daghlian", "aftermath", 15,
      "Harry Daghlian dies on September fifteenth, nineteen forty-five. Acute radiation syndrome. He is the first known fatal criticality accident victim in history. Twenty-four years old. Killed by a brick, a late night, and a sphere that did exactly what the equations predicted.",
      "Quiet New Mexico dawn outside a hospital building, empty road, memorial atmosphere without monuments or text"),
    S("escalation", "establishing", 13,
      "You would think — and this is me editorializing, not a peer-reviewed paper — that after one person dies tickling the same dragon, everyone would invent remote controls and never touch the thing again. You would be giving institutions too much credit.",
      "Los Alamos desert night, empty road toward a lit laboratory building, wind and dust, cinematic establishing shot"),
    S("escalation", "instrument close-up", 14,
      "They did write better procedures. On paper. The safe method used spacers and shims so reflecting shells could not slam shut. The unsafe method was whatever Louis Slotin was currently doing with his hands while explaining how safe it was.",
      "Lab table showing proper metal safety shims and spacers beside beryllium hemispheres, contrasted with a lone screwdriver, 1946 scientific still life"),
    S("escalation", "portrait", 15,
      "Slotin was not a rookie. Winnipeg. University of Manitoba. Doctorate in London. Chicago cyclotron work. Manhattan Project criticality experiments. He had spent years learning exactly how close you can get to a chain reaction before the universe files a complaint.",
      "Montage-like cinematic still: young physicist across eras — library, cyclotron hall, desert lab — ending at Los Alamos instruments"),
    S("escalation", "dialogue", 13,
      "Colleagues warned him. The hand-assembly trick — holding hemispheres apart by feel — was going to kill him. Secondary accounts even float a grim prediction from Enrico Fermi that Slotin would be dead within a year if he kept it up. Whether every word of that warning is word-perfect, the meaning is not disputed: people told him to stop.",
      "Two physicists in a 1940s lab in tense conversation beside a criticality assembly, one gesturing at safety shims, documentary mood"),
    S("escalation", "action", 12,
      "He kept doing it anyway. Confidence is a hell of a drug. Especially when the last ten times you got away with it. The dragon does not care about your streak.",
      "Confident physicist demonstrating a criticality assembly to watching colleagues, hands near metal hemispheres, tense group scene"),
    S("slotin", "establishing", 13,
      "May twenty-first, nineteen forty-six. Same core. Different afternoon. Slotin is running a demonstration for visitors — scientists who came to watch a bomb core almost wake up. Think of it as the world's worst open house.",
      "Group of 1940s scientists standing around a criticality experiment table in a Los Alamos lab, daylight through high windows, Slotin at the center"),
    S("slotin", "instrument close-up", 16,
      "Two beryllium hemispheres. Neutron reflectors. Lower half under the core. Upper half held above it. The gap is the difference between a demonstration and a funeral. Official procedure says: keep that gap with shims. Slotin is keeping it with a screwdriver.",
      "Extreme close-up of beryllium hemispheres around a plutonium core with a screwdriver tip visible in the gap, shallow depth of field, dramatic laboratory lighting"),
    S("slotin", "insert", 12,
      "Let me say that again, slowly, for the people in the back. A screwdriver. On a fissile assembly. As the safety system. If you are picturing a cartoon 'oops,' stop. This is a grown adult choosing the hardware-store method on purpose.",
      "A worn flathead screwdriver lying alone on a lab bench under a harsh lamp, the object of the dare, cinematic still life"),
    S("slotin", "action", 11,
      "The screwdriver slips. The upper hemisphere drops. The core goes prompt supercritical. A blue flash fills the room. The radiation pulse is effectively instant.",
      "Moment of slip: screwdriver falling from between closing metal hemispheres, motion blur, blue flash erupting, 1946 lab accident"),
    S("slotin", "action", 14,
      "Slotin yanks the shell apart with his bare hands. That move almost certainly saves everyone else in the room from a worse dose. It does not save him. Heroic. Also: the kind of heroism you only need because the shims were in a drawer.",
      "Physicist flinging open a beryllium hemisphere as a blue flash fills a 1940s laboratory, colleagues recoiling, cinematic action still"),
    S("slotin", "aftermath", 14,
      "He has just taken a lethal dose. Estimates put it around a thousand rads — the kind of number where the body stops negotiating. Others are irradiated too. Alvin Graves, standing close, is seriously hurt and survives. Distance is everything. Physics does not do equal shares.",
      "Empty lab after criticality accident, hemispheres apart on the table, overturned stool, lingering blue haze suggestion, quiet aftermath"),
    S("slotin", "insert", 13,
      "Slotin tastes metal. His hand burns. He starts telling people where they were standing — because he already understands the geometry of what just happened. He is doing triage with his last good hours of clarity.",
      "Close-up of a physicist's hand above a metal assembly, subtle heat-haze suggestion, 1940s hospital-bound tension, no gore, cinematic"),
    S("slotin", "aftermath", 14,
      "They take him to the hospital. Nine days later, on May thirtieth, nineteen forty-six, Louis Slotin dies of acute radiation syndrome. He is thirty-five. He is the second man killed by the same sphere.",
      "1946 hospital room window at dusk, empty chair, medical instruments of the era on a side table, somber teal and amber light, no gore"),
    S("aftermath", "establishing", 12,
      "After that, the core finally gets the nickname that sticks: the demon core. Not because demons are real. Because two fatal accidents is enough branding for any piece of metal.",
      "The same small plutonium sphere alone on a dark lead-lined container lid in a storage vault, ominous cinematic still life"),
    S("aftermath", "instrument close-up", 13,
      "Los Alamos stops letting people tickle dragons by hand. Criticality work moves toward remote methods. Which is the scientific way of saying: we have officially learned that screwdrivers are not neutron-safety equipment.",
      "1940s–50s remote handling equipment and shielded controls for nuclear experiments, cables and manipulators, period-accurate laboratory"),
    S("aftermath", "establishing", 12,
      "The core itself is later melted down and recycled into other weapon material. The demon does not get a museum pedestal. It gets dissolved into the arsenal. History is not always poetic. Sometimes it is inventory.",
      "Industrial mid-century processing facility suggestion with furnace glow and heavy machinery silhouettes, no readable labels"),
    S("aftermath", "insert", 13,
      "And that is the part people skip when they turn this into a campfire ghost story. The core was never haunted. It was a manufactured subcritical mass that became supercritical when humans stacked the wrong geometry around it. Twice.",
      "Technical still life: plutonium sphere, tungsten carbide brick, beryllium hemisphere, and screwdriver arranged like evidence on a dark table"),
    S("aftermath", "portrait", 12,
      "The United States called Slotin a hero for pulling the shell apart and shielding the others. That is fair. It is also incomplete. Heroes are easier to celebrate than procedures are to follow.",
      "1946 government commendation atmosphere suggestion: folded flag-era office desk with a physicist's personal effects, somber and restrained, no readable text"),
    S("lesson", "portrait", 14,
      "So what is the lesson? Not 'nuclear physics is cursed.' Not 'plutonium is haunted.' The lesson is colder. The most dangerous thing in that room was not the plutonium. The plutonium was doing exactly what the equations said it would do.",
      "Open notebook with equations beside a screwdriver and metal hemispheres, 1940s desk lamp, the tools of a fatal demonstration"),
    S("lesson", "action", 14,
      "The dangerous thing was competence without a brake. Daghlian stayed late alone with a stack of bricks. Slotin skipped the shims for a live audience. Two different men. Same core. Same refusal to treat a near-critical assembly like it could end them.",
      "Split cinematic composition suggestion: night brick-stacking on one side, daytime screwdriver demonstration on the other, same small sphere centered"),
    S("lesson", "instrument close-up", 12,
      "A screwdriver is a tool for screws. It is not a neutron-reflector gap. If your safety plan depends on hand steadiness and luck, you do not have a safety plan. You have a dare with better lighting.",
      "Extreme close-up of screwdriver tip scratched and worn, resting on cold metal, dramatic chiaroscuro"),
    S("lesson", "establishing", 15,
      "Harry Daghlian was twenty-four. Louis Slotin was thirty-five. Between them, they proved — at the cost of their lives — that criticality does not care how clever you are, how many bombs you helped build, or how many times you got away with it before.",
      "New Mexico desert at dawn near Los Alamos, empty mesa road, quiet memorial atmosphere without monuments or text"),
    S("lesson", "aftermath", 13,
      "The thesis is simple enough to fit on a warning sign. The invention was brilliant. The procedure was not a plan. And the dragon never needed to be evil. It only needed someone to tickle it one more time.",
      "Empty criticality assembly table under a single lamp, hemispheres parted, screwdriver set aside, final thesis frame"),
    S("cta", "aftermath", 12,
      "The entire story of the demon core is not a ghost story. It is a workplace story with neutrons. And if that made you grip the arm of your chair a little tighter — yeah. That was the point.",
      "Wide cinematic Los Alamos night landscape, distant lab lights under a dark teal sky, closing atmosphere shot"),
    S("cta", "establishing", 11,
      "If you want the next one — the chemist who poisoned the air twice, or the night they launched the shuttle anyway — it is waiting in the queue. Subscribe, or don't. The equations will not mind either way.",
      "Fade toward black over empty desert horizon at night, last amber rim of light on the mesa"),
]


def build_pack(project_id: str | None = None) -> Dict[str, Any]:
    scenes = []
    for index, raw in enumerate(SCENES, start=1):
        scenes.append(
            {
                "id": index,
                "section": raw["section"],
                "visual_type": raw["visual_type"],
                "narration": raw["narration"],
                "on_screen_text": "",
                "duration_seconds": raw["duration_seconds"],
                "image_prompt": normalize_image_prompt(raw["image_prompt"], LOOK),
                "image_path": None,
            }
        )
    full = "\n\n".join(s["narration"] for s in scenes)
    words = len(full.split())
    runtime = sum(s["duration_seconds"] for s in scenes)
    pack: Dict[str, Any] = {
        "topic": "The Demon Core",
        "style": "science",
        "duration_key": "12",
        "slate_id": SLATE_ID,
        "titles": [
            "They Held a Bomb Core Apart With a Screwdriver",
            "The ENTIRE Story of the Demon Core Explained",
            "Tickling the Dragon's Tail — Twice",
        ],
        "thumbnail_text": "THE SCREWDRIVER SLIPPED",
        "thumbnail_prompt": normalize_image_prompt(
            "A flathead screwdriver slipping between two closing beryllium hemispheres "
            "over a small plutonium core, blue flash erupting, 1946 Los Alamos lab, "
            "extreme tension, face of sphere large in frame",
            LOOK,
        ),
        "thumbnail_path": None,
        "hook": scenes[0]["narration"],
        "driving_question": (
            "How do some of the smartest people alive test a leftover bomb core "
            "with bricks and a screwdriver?"
        ),
        "thesis": (
            "The plutonium obeyed the equations. The men treated a dare like a procedure."
        ),
        "runtime_seconds": runtime,
        "word_count": words,
        "youtube_description": (
            "They held a bomb core apart with a screwdriver. That is not a metaphor.\n\n"
            "The demon core was a 6.2 kg plutonium–gallium sphere built in 1945 for a "
            "possible third atomic bomb. Japan surrendered. Los Alamos kept the core "
            "for criticality tests — and it killed two physicists.\n\n"
            "Harry Daghlian died after a tungsten carbide brick dropped during a solo "
            "night experiment on August 21, 1945. Louis Slotin died after a screwdriver "
            "slipped between beryllium hemispheres on May 21, 1946.\n\n"
            "This is the entire story: verified facts, dry humor, and why a screwdriver "
            "is not a safety plan.\n\n"
            "Chapters in the description. Sources: Demon core; Louis Slotin; Harry Daghlian "
            "(historical accounts of the Los Alamos criticality accidents)."
        ),
        "tags": [
            "demon core",
            "louis slotin",
            "harry daghlian",
            "los alamos",
            "manhattan project",
            "nuclear history",
            "criticality accident",
            "science explained",
            "entire story explained",
            "tickling the dragons tail",
        ],
        "chapters": [
            {"time": "0:00", "title": "The screwdriver"},
            {"time": "1:20", "title": "A leftover bomb"},
            {"time": "3:00", "title": "Tickling the dragon"},
            {"time": "4:20", "title": "Harry Daghlian"},
            {"time": "6:40", "title": "They kept going"},
            {"time": "8:00", "title": "Louis Slotin"},
            {"time": "10:20", "title": "The demon gets a name"},
            {"time": "11:20", "title": "The real lesson"},
        ],
        "full_narration": full,
        "scenes": scenes,
        "research": {
            "topic": "The Demon Core",
            "summary": (
                "A subcritical plutonium–gallium core (6.2 kg, 89 mm) made in 1945 "
                "for a possible third atomic bomb was retained at Los Alamos after "
                "Japan's surrender. Two criticality accidents — Daghlian (21 Aug 1945) "
                "and Slotin (21 May 1946) — killed both physicists via acute radiation "
                "syndrome. Hands-on experiments of that type were curtailed; the core "
                "material was later recycled."
            ),
            "facts": [
                "Core: plutonium–gallium alloy, ~6.2 kg (14 lb), ~89 mm (3.5 in) diameter; Manhattan Project, 1945.",
                "Prepared for a possible third wartime bomb; retained for testing after Japan surrendered.",
                "Harry K. Daghlian Jr.: accident 21 Aug 1945 at Omega Site; dropped a tungsten carbide brick onto the assembly; died 15 Sep 1945 (25 days later).",
                "Louis Slotin: accident 21 May 1946 during a demonstration; screwdriver between beryllium hemispheres slipped; died 30 May 1946 (9 days later).",
                "Both accidents used neutron-reflecting tampers that drove the core supercritical; a blue flash was reported.",
                "Others in the Slotin room were irradiated; proximity determined dose. Alvin Graves was among the seriously exposed survivors.",
                "Nickname 'demon core' followed the fatal accidents.",
                "Afterward, such hands-on criticality demonstrations were replaced by safer remote methods; core material was later recycled into other weapons material.",
            ],
            "timeline": [
                "1945 — Core manufactured; Japan surrenders; core kept for testing.",
                "21 Aug 1945 — Daghlian criticality accident at Omega Site.",
                "15 Sep 1945 — Daghlian dies of acute radiation syndrome.",
                "21 May 1946 — Slotin criticality accident during a demonstration.",
                "30 May 1946 — Slotin dies of acute radiation syndrome.",
                "Later — Hands-on methods curtailed; core material recycled.",
            ],
            "disputed": [
                "Exact dose figures and some eyewitness dialogue vary by secondary account.",
                "The widely repeated 'Fermi will be dead within a year' warning is popular lore in secondary sources; treat as reported anecdote, not a lab log entry.",
            ],
            "angle_ideas": [
                "The whole story happened because a screwdriver replaced the shims.",
                "The plutonium never misbehaved — the procedure did.",
            ],
            "sources": [
                {"title": "Demon core", "url": "https://en.wikipedia.org/wiki/Demon_core"},
                {"title": "Louis Slotin", "url": "https://en.wikipedia.org/wiki/Louis_Slotin"},
                {"title": "Harry Daghlian", "url": "https://en.wikipedia.org/wiki/Harry_Daghlian"},
            ],
        },
    }
    if project_id:
        pack["id"] = project_id
    return pack


if __name__ == "__main__":
    existing = load_project(EXISTING_ID)
    pack = build_pack(EXISTING_ID if existing else None)
    saved = save_project(pack)
    mark_project(SLATE_ID, saved["id"], status="in_progress")
    print("id:", saved["id"])
    print("scenes:", len(saved["scenes"]))
    print("words:", saved["word_count"])
    print("runtime_seconds:", saved["runtime_seconds"])
    print("minutes:", round(saved["runtime_seconds"] / 60, 1))
    # spoken estimate at ~140 wpm conversational
    print("spoken_min_at_140wpm:", round(saved["word_count"] / 140, 1))
