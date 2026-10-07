"""Which retail screens are still retail: python tools/port/retail_screens.py [--melee PATH] [--json]

Reads mn_PcOpenNative (src/melee/mn/mnmain.c), the table that opens the game's own native screens from the frontend's
FA_NATIVE rows, and says for each entry point whether an Atlas data screen takes it over (a fad_screens[] row in
src/melee/gm/gmfrontend_atlas_data.inc) or it stays retail. tools/port/retail_screens_expected.json is the committed
inventory (test_retail_screens.py compares against it). The Language-row question reads it: the row goes when the last retail TEXT
screen is gone, and Snapshots, Movies and Staff Roll stay retail by the owner's decision, so it never goes; the owner kept the row
on 2026-10-07 and nothing is removed. "step 5" marks an entry point another step already covers; SCENES lists the scenes step 8 looked at.
"""
import json
import os
import re
import sys


def entries(text):
    body = text[text.index("static void mn_PcOpenNative"):]
    body = body[:body.index("not a native screen")]
    out = []
    for km in re.finditer(r"case (MENU_KIND_\w+):(.*?)(?=case MENU_KIND_|\Z)", body, re.S):
        kind, seg = km.group(1), km.group(2)
        for m in re.finditer(r"(?:case (SEL_\w+):|if \(sel == (SEL_\w+)\)\s*\{?)(.*?)return;", seg, re.S):
            calls = re.findall(r"\b(\w+)\(", m.group(3))
            out.append((kind, m.group(1) or m.group(2), calls[-1] if calls else "?"))
    return out


def atlas_covered(text):
    """(kind, sel) pairs named by a fad_screens[] row: { FD_x, "id", "TITLE", MENU_KIND_x, SEL_x, ..."""
    return set(re.findall(r"\{\s*FD_\w+\s*,\s*\"[\w.]+\"\s*,\s*\"[^\"]*\"\s*,\s*(MENU_KIND_\w+)\s*,\s*(SEL_\w+)", text))


# Entry points another Atlas step already covers in the settings door (gmfrontend_atlas_set.inc): their FA_NATIVE rows stay for
# MELEE_ATLAS=0 and for the legacy list, but under Atlas the player reaches the Atlas page instead.
STEP5 = {
    "SEL_VS_RULES": "step 5: VERSUS > RULES (FA_RULES)",
    "SEL_SETTINGS_RUMBLE": "step 5: SETTINGS > GAME > Rumble rows",
    "SEL_SETTINGS_SOUND": "step 5: SETTINGS > AUDIO",
    "SEL_SETTINGS_ERASE": "step 5: the erase screen",
}
# The owner's decision (spec 2): these stay retail behind a native hand-off.
STAYS = {"SEL_DATA_SNAP": "Snapshots", "SEL_DATA_ARCHIVES": "Movies"}
# What an ATLAS entry does not cover.
NOTES = {"SEL_VS_NAME": "the tag list only: making, renaming and deleting a tag hands over to the retail Name Entry (its editor writes the save and cannot be checked without a window)"}


# The scenes step 8 looked at (spec 13.8): what Atlas does with each, and why the rest stay retail. "stays": true means retail by decision, not by omission.
SCENES = [
    {"scene": "GS_TITLE", "atlas": "OVERLAY", "note": "step 2: the host draws over the retail title, which keeps its own exit logic"},
    {"scene": "GS_RESULTS", "atlas": "REPLACE stand-in", "note": "off by default: MELEE_ATLAS_SCENES=5:replace; never online; no 3D winner scene"},
    {"scene": "GS_GAMEOVER", "stays": True, "note": "no-go for step 8: a 3D animated scene whose enter data (DebugGameOverData) has unnamed fields; a candidate for step 10's frame pattern"},
    {"scene": "GS_STAFFROLL", "stays": True, "note": "the owner's decision: the credits roll stays retail and gets no Credits entry"},
    {"scene": "GS_INTRO_NORMAL", "stays": True, "note": "Adventure's intro: 3D and video"},
    {"scene": "GS_INTRO_EASY", "stays": True, "note": "Classic's splash: 3D"},
    {"scene": "GS_REGEND_TOYFALL", "stays": True, "note": "the trophy fall after a 1P mode: 3D"},
    {"scene": "GS_REGEND_CONGRATS", "stays": True, "note": "a THP movie"},
    {"scene": "GS_PRIZE_INTERFACE", "stays": True, "note": "the achievement pop-up: drawn over the scene it appears in"},
]


def inventory(melee):
    mn = open(os.path.join(melee, "src/melee/mn/mnmain.c"), encoding="utf-8", errors="replace").read()
    atl = os.path.join(melee, "src/melee/gm/gmfrontend_atlas_data.inc")
    covered = atlas_covered(open(atl, encoding="utf-8").read()) if os.path.exists(atl) else set()
    return [{"kind": k, "sel": s, "retail_fn": f, "atlas": (k, s) in covered, "step5": STEP5.get(s, ""), "stays": s in STAYS, "note": NOTES.get(s, "")}
            for k, s, f in entries(mn)]


def main(argv):
    root = os.environ.get("GW_MELEE", "")
    melee = next((argv[i + 1] for i, a in enumerate(argv) if a == "--melee"), root)
    rows = inventory(melee)
    if "--json" in argv:
        print(json.dumps({"entries": rows, "scenes": SCENES}, indent=1))
    else:
        print("\n".join("%-20s %-22s %-28s %s" % (r["kind"], r["sel"], r["retail_fn"], "ATLAS" if r["atlas"] else ("step 5" if r["step5"] else "retail")) for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
