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
    7: [
        # Reconciled 2026-10-07 against what steps 2 to 5 built (the plan's names in brackets). Hard needs first; a 5th element marks a SOFT
        # need: it prints SOFT and names the task that builds it (the exit status is unchanged).
        ("pc/platform/gw_ui_registry.h", r"\bat_reg_children\b", "step 2", "N1 the registry (the plan said at_registry_entries_of)"),
        ("src/melee/gm/gmfrontend_atlas.inc", r"\bfa_submit\b", "step 2", "N2 the adapter submits an engine-owned screen (the plan said FA_ATLAS)"),
        ("pc/platform/gw_script_ui_set.inc", r"\bgw_Ui_SetOpen\b", "step 5", "N2 an engine-owned native screen with its own tick, mouse and event ring (the plan said gw_ui_native_*)"),
        ("pc/platform/gw_ui_screen.h", r"\bn_tabs\b", "step 5", "N3 tabs in the screen record (AtScreen.tabs[], AtView.tab)"),
        ("pc/platform/gw_script_ui.inc", r"\bl_ui_hud\b", "step 3", "N4 gd.ui.hud"),
        ("pc/platform/gw_ui_hud.h", r"\bAT_HP_STRIP\b", "step 3", "N4 the strip part"),
        ("pc/platform/gw_ui_screen.h", r"\bbackdrop\b", "step 3", "N5 a screen over the world", "Task 5b"),
        ("pc/platform/gw_ui_screen.h", r"AT_VAL_STEPPER", "step 5", "N6 the stepper value", "Task 5a"),
        ("pc/platform/gw_ui_parts.c", r"with_text", "step 3", "N7 explainer WITH tags are drawn (with_text is parsed; the plan said with_tag)", "Task 5c"),
        ("pc/platform/gw_script_ui.inc", r'"token"', "this plan", "N8 gd.ui.token", "Task 5e"),
        ("pc/platform/gw_script_ui.inc", r'"entries"', "step 2", "N9 gd.ui.entries and activate", "Task 5f"),
        ("pc/platform/gw_ui_screen.c", r'"tabs"', "step 5", "N10 tabs from Lua", "Task 5d"),
    ],
    # Step 8 (retail screens rebuilt from data). Reconciled 2026-10-07 against what steps 2 to 6 built: the adapter's submit is
    # still fa_submit, the REPLACE hook is gmFrontend_AtlasStandIn, the scene table calls Ui_ScenePolicy. The data screens ride
    # the native settings door (gw_Ui_SetOpen, step 5) instead of the plan's gw_Ui_Begin list: see gmfrontend_atlas_data.inc.
    8: [
        ("src/melee/gm/gmfrontend_atlas.inc", r"\bfa_submit\b", "step 2", "N1 the adapter submits a screen each frame"),
        ("src/melee/gm/gmfrontend_atlas.inc", r"gmFrontend_AtlasStandIn", "step 2", "N2 the REPLACE hook"),
        ("src/melee/gm/gm_1A3F.c", r"Ui_ScenePolicy", "step 2", "N2 the scene table hook"),
        ("pc/platform/gw_ui_policy.c", r"AT_POLICY_REPLACE", "step 2", "N2 the policy table"),
        ("pc/platform/gw_script_ui_set.inc", r"\bgw_Ui_SetOpen\b", "step 5", "N3 an engine-owned native list screen (rows, tabs, events)"),
        ("pc/platform/gw_ui_screen.h", r"#define AT_MAX_ITEMS 64", "step 5", "N4 AT_MAX_ITEMS 64"),
    ],
}

# Soft needs: printed when missing, never fail the exit. (file, regex, owner, why)
SOFT = {
    8: [
        ("pc/platform/gw_ui_item.h", r"at_item_apply", "step 5", "N3 value rows"),
        ("pc/platform/gw_ui_screen.h", r"\btabs\b", "steps 4,5", "N5 tabs"),
        ("pc/platform/gw_kit.h", r"gw_Kit_TexAddHsd", "step 4", "N6 disc-art decode"),
        ("pc/platform/gw_ui_parts.h", r"at_part_port_card", "step 4", "N7 port card"),
    ],
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
    for e in G[a.step]:
        rel, rx, owner, why = e[:4]
        soft = e[4] if len(e) > 4 else None
        path = os.path.join(root, rel)
        text = open(path, encoding="utf-8", errors="replace").read() if os.path.exists(path) else None
        if text is None or not re.search(rx, text):
            if soft:
                print("SOFT     %-46s %-8s %s (built by %s)" % (rel, owner, why, soft))
            else:
                print("MISSING  %-46s %-8s %s (%s)" % (rel, owner, why, rx))
                missing += 1
    for rel, rx, owner, why in SOFT.get(a.step, []):
        path = os.path.join(root, rel)
        text = open(path, encoding="utf-8", errors="replace").read() if os.path.exists(path) else None
        if text is None or not re.search(rx, text):
            print("SOFT   %-46s %-8s %s" % (rel, owner, why))
    print("gate step %d: %d missing" % (a.step, missing))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
