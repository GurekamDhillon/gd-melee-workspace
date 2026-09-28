#!/usr/bin/env python3
"""Offline check of Ultimate smash-hold markers and Melee charge commands."""
from pathlib import Path
import os
import unittest

import acmd_parse as AP
import acmd_to_ftcmd as FT
from convert_ultimate_anim import TOOL


DUMP = os.path.join(os.environ.get("GW_GHIDRA_PROJECTS", str(Path.home() / "ghidra-projects")), 'sora_acmd')
NRO = os.path.join(TOOL, "workspace", "extracted", "prebuilt", "nro", "release", "lua2cpp_trail.nro")
AGENT = hex(AP.hash40("trail"))
# Marth PlMs.dat data offsets 0x4ED4/0x4FBC/0x5090: 60 frames, rate 350, colour animation 119.
CHARGE_WORDS = [0xE03C015E, 0x77000000]
CASES = {"game_attacks4": 6, "game_attackhi4": 7, "game_attacklw4": 3}


class SmashChargeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nro = AP.Nro(NRO)

    def test_sora_smash_scripts_emit_charge_at_hold_frame(self):
        for script, frame in CASES.items():
            with self.subTest(script=script):
                path = os.path.join(DUMP, "game", f"{AGENT}__{hex(AP.hash40(script))}.c")
                with open(path, encoding="utf-8") as fp:
                    commands = AP.parse_body(fp.read(), self.nro, {})
                markers = [c for c in commands if c["cmd"] == "START_SMASH_HOLD"]
                self.assertEqual([(c["frame"], c["when"]) for c in markers], [(float(frame), [])])

            with self.assertRaisesRegex(ValueError, "unmapped|cannot be converted"):
                    FT.translate({"commands": commands}, {"top": 0})

    def test_named_ultimate_flag_works_for_other_fighters(self):
        body = """// BODY @ synthetic
lib::L2CValue::L2CValue(aLStack_90,5);
app::sv_animcmd::frame(plVar10,fVar11);
lib::L2CValue::L2CValue(aLStack_90,FIGHTER_STATUS_ATTACK_FLAG_START_SMASH_HOLD);
app::lua_bind::WorkModule__on_flag_impl(module,flag);
"""
        commands = AP.parse_body(body, None, {})
        words, _ = FT.translate({"commands": commands}, {})
        self.assertEqual([(c["frame"], c["cmd"]) for c in commands[-1:]], [(5.0, "START_SMASH_HOLD")])
        self.assertEqual(words, [(2 << 26) | 5, *CHARGE_WORDS, 0])


if __name__ == "__main__":
    unittest.main()
