"""Which retail screens are still retail: python tools/port/retail_screens.py [--melee PATH] [--json] [--check]

Reads mn_PcOpenNative (src/melee/mn/mnmain.c), the table that opens the game's own native screens from the frontend's
FA_NATIVE rows, and says for each entry point whether an Atlas data screen takes it over (a fad_screens[] row in
src/melee/gm/gmfrontend_atlas_data.inc) or it stays retail. tools/port/retail_screens_expected.json is the committed
inventory; --check compares against it (the Language-row question reads it: the row goes when the last retail TEXT screen is
gone, and Snapshots, Movies and Staff Roll stay retail by the owner's decision).
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


def inventory(melee):
    mn = open(os.path.join(melee, "src/melee/mn/mnmain.c"), encoding="utf-8", errors="replace").read()
    atl = os.path.join(melee, "src/melee/gm/gmfrontend_atlas_data.inc")
    covered = atlas_covered(open(atl, encoding="utf-8").read()) if os.path.exists(atl) else set()
    return [{"kind": k, "sel": s, "retail_fn": f, "atlas": (k, s) in covered, "step5": STEP5.get(s, ""), "stays": s in STAYS}
            for k, s, f in entries(mn)]


def main(argv):
    root = os.environ.get("GW_MELEE", "")
    melee = next((argv[i + 1] for i, a in enumerate(argv) if a == "--melee"), root)
    rows = inventory(melee)
    if "--json" in argv:
        print(json.dumps(rows, indent=1))
    else:
        print("\n".join("%-20s %-22s %-28s %s" % (r["kind"], r["sel"], r["retail_fn"], "ATLAS" if r["atlas"] else ("step 5" if r["step5"] else "retail")) for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
