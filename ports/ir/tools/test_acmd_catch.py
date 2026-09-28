#!/usr/bin/env python3
"""Offline check of the Ultimate CATCH parser and Melee grab-box encoder."""
from pathlib import Path
import os
import unittest

import acmd_parse as AP
import acmd_to_ftcmd as FT
from convert_ultimate_anim import TOOL


DUMP = os.path.join(os.environ.get("GW_GHIDRA_PROJECTS", str(Path.home() / "ghidra-projects")), 'sora_acmd')
NRO = os.path.join(TOOL, "workspace", "extracted", "prebuilt", "nro", "release", "lua2cpp_trail.nro")
AGENT = hex(AP.hash40("trail"))
SCALE = 1.25

# Frame values and box geometry from the decompiled game scripts:
# game_catch:     0x5b268858f__0xaf75802eb.c:108-225 (on 9, clear after wait 2 at 11)
# game_catchdash: 0x5b268858f__0xec82f7fb4.c:108-225 (on 12, clear after wait 2 at 14)
# game_catchturn: 0x5b268858f__0xe7361b7f3.c:108-225 (on 13, clear after wait 2 at 15)
CASES = {
    "game_catch": (9, 11, [
        (0, 3.3, 0, 6.6, 4.6, 0, 6.6, 8.6, "0xe7cc"),
        (1, 1.65, 0, 6.6, 2.95, 0, 6.6, 10.25, "0xe7d0"),
    ]),
    "game_catchdash": (12, 14, [
        (0, 2.6, 0, 6.6, 4.6, 0, 6.6, 10.8, "0xe7cc"),
        (1, 1.3, 0, 6.6, 3.3, 0, 6.6, 12.1, "0xe7d0"),
    ]),
    "game_catchturn": (13, 15, [
        (0, 3.3, 0, 6.6, -4.6, 0, 6.6, -11.6, "0xe7cc"),
        (1, 1.65, 0, 6.6, -2.95, 0, 6.6, -13.25, "0xe7d0"),
    ]),
}


def signed16(v):
    return v - 0x10000 if v & 0x8000 else v


def grab_events(words):
    """Decode the time, five-word hitbox, and clear commands relevant to this test."""
    frame = 0
    events = []
    i = 0
    while i < len(words):
        w = words[i]
        op = w >> 26
        if op == 2:
            frame = w & 0x3FFFFFF
        elif op == 11:
            w1, w2, w3, w4 = words[i + 1:i + 5]
            events.append(("on", frame, (w >> 23) & 7, (w >> 11) & 0xFF,
                           w & 0x3FF, (w1 >> 16) & 0xFFFF, signed16(w1 & 0xFFFF),
                           signed16(w2 >> 16), signed16(w2 & 0xFFFF),
                           (w3 >> 23) & 0x1FF, (w4 >> 18) & 0x1F, w4 & 3))
            i += 4
        elif op == 16:
            events.append(("off", frame))
        elif op == 59:
            i += ((w >> 16) & 15) - 1
        i += 1
    return events


class CatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nro = AP.Nro(NRO)
        cls.hashes = {AP.hash40("top"): "top"}

    def test_dump_grab_scripts(self):
        for script, (on, off, boxes) in CASES.items():
            with self.subTest(script=script):
                path = os.path.join(DUMP, "game", f"{AGENT}__{hex(AP.hash40(script))}.c")
                with open(path, encoding="utf-8") as fp:
                    commands = AP.parse_body(fp.read(), self.nro, self.hashes)
                catches = [c for c in commands if c["cmd"] == "CATCH"]
                clears = [c for c in commands if c["cmd"] == "GrabModule::clear_all"]
                self.assertEqual(len(catches), len(boxes))
                self.assertEqual([c["frame"] for c in catches], [on] * len(boxes))
                self.assertEqual([c["frame"] for c in clears], [off])
                for c, (slot, size, x, y, z, x2, y2, z2, situation) in zip(catches, boxes):
                    n = c["named"]
                    self.assertEqual(n["id"], slot)
                    self.assertEqual(n["bone"], "top")
                    self.assertEqual(n["status"], {"const": "0x80c"})
                    self.assertEqual(n["situation"], {"const": situation})
                    self.assertEqual(tuple(n[k] for k in ("size", "x", "y", "z", "x2", "y2", "z2")),
                                     (size, x, y, z, x2, y2, z2))
                fixture_allowlist = {("command", name):
                                     {"reason": "grab geometry fixture", "approved_by": "test fixture",
                                      "moves": ["<unnamed move>"]}
                                     for name in ("GrabModule::set_rebound", "WorkModule::on_flag",
                                                  "UNCONSUMED_ACMD_ARGS")}
                words, report = FT.translate({"commands": commands}, {"top": 0}, SCALE,
                                             allowlist=fixture_allowlist)
                self.assertEqual(report["hitboxes"], 2 * len(boxes))   # each capsule: both ends
                self.assertEqual(report["grab_boxes"], len(boxes))
                events = grab_events(words)
                self.assertEqual(len(events), 2 * len(boxes) + 1)
                want = []
                for slot, size, x, y, z, x2, y2, z2, situation in boxes:
                    for s_, px, py, pz in ((slot, x, y, z), (slot + 2, x2, y2, z2)):
                        want.append(("on", on, s_, 0, 0, round(size * SCALE * 256), round(px * SCALE * 256),
                                     round(py * SCALE * 256), round(pz * SCALE * 256),
                                     361, 8, 2 if situation == "0xe7cc" else 1))
                self.assertEqual(events[:-1], want)
                self.assertEqual(events[-1], ("off", off))


if __name__ == "__main__":
    unittest.main()
