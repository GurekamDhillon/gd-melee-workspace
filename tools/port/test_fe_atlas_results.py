"""Static guards on the Atlas Results stand-in (the far_* functions of src/melee/gm/gmfrontend_atlas_data.inc). No game, no disc.

    GW_MELEE=<game checkout> python -m unittest tools/port/test_fe_atlas_results.py     (from the workspace root)

The stand-in is a REPLACE of the retail results scene, reached only through MELEE_ATLAS_SCENES=5:replace and never in a netplay session. Replacing a scene
drops what it draws and must keep what it DOES: the comment block `RESULTS SIDE EFFECTS` above far_enter lists every call of gm_Scene_Results_OnEnter and
its procs classified audio, state or presentation, read from gmresult.c and gmresultplayer.c. This reads that list and checks that every audio and state
name occurs in the stand-in's code (Review Focus 7), that the exit runs fn_801701AC, that each of the four ports is read for START and a pad error
(Review Focus 8), and that no merged menu intent is used.
"""
import os
import re
import unittest

ROOT = os.environ.get("GW_MELEE") or os.path.join(os.path.dirname(__file__), "..", "..", "melee")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as f:
        return f.read()


def function_body(text, signature):
    i = text.index(signature)
    j = text.index("\n}\n", i)
    return text[i:j]


class Results(unittest.TestCase):
    def setUp(self):
        self.t = read("src/melee/gm/gmfrontend_atlas_data.inc")
        block = self.t[self.t.index("RESULTS SIDE EFFECTS:"):]
        block = block[:block.index("*/")]
        self.effects = re.findall(r"^\s*\*\s+(\w+)\s+(audio|state|presentation)\b", block, re.M)
        self.code = self.t[self.t.index("static int far_frames;"):]

    def test_the_table_exists_and_is_classified(self):
        self.assertGreaterEqual(len(self.effects), 8)
        classes = {c for _, c in self.effects}
        self.assertEqual(classes, {"audio", "state", "presentation"})

    def test_every_audio_and_state_call_is_repeated(self):
        code_only = re.sub(r"/\*.*?\*/", "", self.code, flags=re.S)
        for name, cls in self.effects:
            if cls in ("audio", "state"):
                self.assertRegex(code_only, r"\b%s\b" % re.escape(name), "%s (%s) is dropped by the stand-in" % (name, cls))

    def test_presentation_calls_are_not_made(self):
        code_only = re.sub(r"/\*.*?\*/", "", self.code, flags=re.S)
        for name, cls in self.effects:
            if cls == "presentation":
                self.assertNotRegex(code_only, r"\b%s\b" % re.escape(name), "%s is presentation: the stand-in must not call it" % name)

    def test_the_exit_clears_what_retail_clears(self):
        self.assertIn("fn_801701AC();", function_body(self.t, "static void far_exit("))

    def test_start_and_pad_errors_are_read_for_all_four_ports(self):
        body = function_body(self.t, "static void far_frame(")
        self.assertRegex(body, r"for \(i = 0; i < 4; i\+\+\)")
        self.assertIn("HSD_PadCopyStatus[i].err", body)
        self.assertIn("PAD_BUTTON_START", body)
        self.assertIn("Ui_ResConfirm(i, 2)", body)
        self.assertIn("Ui_ResConfirm(i, 1)", body)

    def test_no_merged_menu_intent(self):
        body = function_body(self.t, "static void far_frame(") + function_body(self.t, "static void far_enter(")
        self.assertNotIn("Ui_SetIntent", body)
        self.assertNotIn("Ui_Intent", body)
        self.assertNotIn("mn_80229624", body)

    def test_the_screen_opens_inside_the_scene_loop(self):
        enter = function_body(self.t, "static void far_enter(")
        self.assertNotIn("Ui_DataOpen", enter, "the host closes a screen with the scene it was opened in; on_enter runs before that scene is current")
        self.assertIn("Ui_DataOpen(\"data.results\"", function_body(self.t, "static void far_frame("))

    def test_the_stand_in_is_reachable_only_by_the_scene_policy_and_not_online(self):
        atlas = read("src/melee/gm/gmfrontend_atlas.inc")
        self.assertIn("kind == GS_RESULTS ? fad_results_standin() : NULL", atlas)
        policy = read("pc/platform/gw_ui_policy.c")
        self.assertNotRegex(policy, r"AT_SCENE_RESULTS|\{\s*5\s*,\s*AT_POLICY_REPLACE", "no policy row: results stays retail until the owner has looked")
        self.assertIn("Ui_NetplayActive()", function_body(self.t, "static GameScene* fad_results_standin("))

    def test_the_exit_is_the_retail_one(self):
        self.assertIn("gm_801A4B60();", function_body(self.t, "static void far_frame("))


if __name__ == "__main__":
    unittest.main()
