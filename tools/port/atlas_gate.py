"""Gate: has every earlier Atlas step delivered what this step needs?

    python tools/port/atlas_gate.py --step 6 [--melee PATH]

Each requirement is (file under the game checkout, regex, owner, why). A missing one is printed and the exit status is 1.
When a name differs from the one a plan wrote, the earlier step's real name goes into this table AND into the plan's
"Needs" table in the same commit; do not weaken a regex to make the gate pass.
"""
import argparse
import os
import re
import sys

G = {
    6: [
        # N1: a screen submitted from game-side C, drawn, ticked and hit-tested without a script. Reconciled 2026-10-07:
        # step 2 built the menu adapter (fa_submit / Ui_PollEvent) and step 5 the native settings door (an engine-owned
        # slot with its own keyboard, mouse and event ring: gw_Ui_SetOpen), which is the pattern the room door follows.
        ("src/melee/gm/gmfrontend_atlas.inc", r"\bfa_submit\b", "step 2", "N1 the game-side adapter submits a screen"),
        ("src/melee/gm/gmfrontend_atlas.inc", r"\bUi_PollEvent\b", "step 2", "N1/N8 events come back to the game side"),
        ("pc/platform/gw_script_ui_set.inc", r"\bgw_Ui_SetOpen\b", "step 5", "N1 an engine-owned native screen with its own tick, mouse and event ring"),
        ("pc/platform/gw_script_ui_set.inc", r"gw_Mouse_ScriptRead", "step 2", "N8 the native mouse source for game-side screens"),
        # N3: the registry (at_reg_children, not at_registry_entries)
        ("pc/platform/gw_ui_registry.h", r"\bat_reg_children\b", "step 2", "N3 the registry"),
        # N5: the port card (at_part_sel_card; AtPortCard is the HUD's own, different shape)
        ("pc/platform/gw_ui_parts.h", r"\bat_part_sel_card\b", "step 4", "N5 the port card part"),
        # N6: stage cells that can show struck, banned, picked
        ("pc/platform/gw_ui_screen.h", r"\bAT_CELL_BANNED\b", "step 4", "N6 cell flags for strike marks"),
        # N7: the one character select with an online (lobby) profile
        ("pc/platform/gw_ui_css_profile.h", r"\bAT_MT_LOBBY\b", "step 4", "N7 the lobby's mode profile"),
        # N4: value rows through the adapter
        ("src/melee/gm/gmfrontend_atlas_table.h", r"\bFE_CHOICE\b", "step 5", "N4 value rows through the table walker"),
        ("src/melee/gm/gmfrontend_atlas_table.h", r"\bFE_SLIDER\b", "step 5", "N4 sliders with a format"),
    ],
    7: [],  # filled by the step 7 plan, Task 0
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, required=True)
    ap.add_argument("--melee", default=os.environ.get("GW_MELEE", ""))
    a = ap.parse_args(argv)
    root = a.melee
    if not root or not os.path.isdir(root):
        print("gate: set GW_MELEE or pass --melee")
        return 2
    if a.step not in G:
        print("gate: no table for step %d" % a.step)
        return 2
    missing = 0
    for rel, rx, owner, why in G[a.step]:
        path = os.path.join(root, rel)
        text = open(path, encoding="utf-8", errors="replace").read() if os.path.exists(path) else None
        if text is None or not re.search(rx, text):
            print("MISSING  %-46s %-8s %s (%s)" % (rel, owner, why, rx))
            missing += 1
    print("gate step %d: %d missing" % (a.step, missing))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
