#!/usr/bin/env python3
"""Offline checks for animation-length changes in kept host scripts."""
import struct
import json
import tempfile
import unittest
from pathlib import Path

from walkloop import rewrite_host_loop, validate_geno_overlays, validate_script


class ScriptMemory:
    def __init__(self, words, start=0x46D4, pointers=()):
        self.data = bytearray(start + 4 * len(words))
        for i, word in enumerate(words):
            struct.pack_into(">I", self.data, start + 4 * i, word)
        self.relocs = {start + 4 * i for i in pointers}

    def u32(self, offset):
        return struct.unpack_from(">I", self.data, offset)[0]

    def put(self, offset, word):
        struct.pack_into(">I", self.data, offset, word)

    def ptr(self, offset, target):
        self.put(offset, target)
        self.relocs.add(offset)

    def alloc(self, data):
        offset = len(self.data)
        self.data.extend(data)
        return offset


WALK_MIDDLE = [
    0x7C000018, 0x08000016,
    0xD8020000, 0x000001C1, 0x00006E40, 0xAC026000,
    0x08000023, 0xD8000000, 0x000001C1, 0x00006E40,
    0xAC026000, 0x1C000000, 0x000046D4,
]


class WalkLoopTest(unittest.TestCase):
    def test_exact_marth_walkmiddle_scales_steps_and_waits_for_sora_loop(self):
        mem = ScriptMemory(WALK_MIDDLE, pointers=(12,))
        self.assertEqual(len(validate_script(mem, 0x46D4)), 1)
        rewritten, detail = rewrite_host_loop(mem, 0x46D4, 35, 50)
        self.assertNotEqual(rewritten, 0x46D4)
        self.assertEqual(detail["scaled_syncs"], [(22, 31), (35, 50)])
        self.assertEqual(detail["waits_inserted"], 1)
        self.assertEqual(mem.u32(rewritten + 4), 0x0800001F)
        self.assertEqual(mem.u32(rewritten + 24), 0x08000032)
        self.assertEqual(mem.u32(rewritten + 44), 0x20000000)
        self.assertEqual(mem.u32(rewritten + 48), 0x1C000000)
        self.assertEqual(mem.u32(rewritten + 52), rewritten)
        self.assertEqual(validate_script(mem, rewritten), [])
        self.assertEqual(mem.u32(0x46D4 + 4), 0x08000016)

    def test_forward_goto_into_back_loop_is_rewritten(self):
        base = 0x46D4
        mem = ScriptMemory([0x1C000000, base + 12, 0,
                            0x0800000A, 0x1C000000, base + 12], pointers=(1, 5))
        self.assertEqual(len(validate_script(mem, base)), 1)
        rewritten, detail = rewrite_host_loop(mem, base, 20, 40)
        self.assertEqual(detail["scaled_syncs"], [(10, 20)])
        self.assertEqual(validate_script(mem, rewritten), [])

    def test_waited_loop_is_left_alone(self):
        base = 0x46D4
        mem = ScriptMemory([0x08000016, 0x20000000, 0x1C000000, base], pointers=(3,))
        self.assertEqual(validate_script(mem, base), [])
        rewritten, detail = rewrite_host_loop(mem, base, 35, 50)
        self.assertEqual(rewritten, base)
        self.assertEqual(detail["waits_inserted"], 0)

    def test_counted_loop_gets_a_wait_before_its_back_edge(self):
        base = 0x46D4
        mem = ScriptMemory([0x0C000002, 0x0800000A, 0x10000000, 0])
        self.assertEqual(len(validate_script(mem, base)), 1)
        rewritten, detail = rewrite_host_loop(mem, base, 20, 40)
        self.assertEqual(detail["scaled_syncs"], [(10, 20)])
        self.assertEqual(mem.u32(rewritten + 8), 0x20000000)
        self.assertEqual(validate_script(mem, rewritten), [])

    def test_one_way_backward_transfer_is_not_a_loop(self):
        base = 0x46D4
        mem = ScriptMemory([0x0800000A, 0, 0x1C000000, base], pointers=(3,))
        self.assertEqual(validate_script(mem, base + 8), [])

    def test_generated_script_without_wait_is_rejected(self):
        base = 0x46D4
        mem = ScriptMemory([0x08000016, 0x1C000000, base], pointers=(2,))
        findings = validate_script(mem, base)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["jump"], base + 4)
        self.assertEqual(findings[0]["target"], base)

    def test_geno_file_overlay_is_checked_for_unwaited_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sora_sp_8.txt").write_text("# overlay\n0x08000016 0x1C000000 0x00000000\n")
            (root / "geno.json").write_text(json.dumps({"fighters": [{"subactions": [
                {"index": 8, "file": "sora_sp_8.txt"}]}]}))
            findings = validate_geno_overlays(root / "geno.json")
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["row"], 8)
            self.assertEqual(findings[0]["jump"], 4)


if __name__ == "__main__":
    unittest.main()
