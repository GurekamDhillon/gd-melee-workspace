"""Host extraction checks; retail integration runs when GW_ISO_VANILLA is set."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / "ports/ir/tools/build_melee_fighter.py"
sys.path.insert(0, str(BUILDER.parent))
spec = importlib.util.spec_from_file_location("melee_host_builder", BUILDER)
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


class HostTests(unittest.TestCase):
    def test_common_attribute_reader_keeps_signed_integer_and_float_types(self):
        # A tiny authored HSD archive; no game bytes are needed for this check.
        data = bytearray(0x220)
        struct.pack_into(">I", data, 0, 0x20)
        struct.pack_into(">i", data, 0x20 + 0x58, -3)
        struct.pack_into(">f", data, 0x20 + 0x5C, 0.25)
        struct.pack_into(">f", data, 0x20 + 0x88, 104.0)
        symbol = b"ftDataFixture\0"
        header = struct.pack(">8I", 32 + len(data) + 12 + len(symbol), len(data), 1, 1, 0, 0, 0, 0)
        archive = host.mex_hsd.Archive(header + data + struct.pack(">3I", 0, 0, 0) + symbol)
        attrs = {a["engine_name"]: a for a in host.read_common_attributes(archive)}
        self.assertEqual((attrs["max_jumps"]["value"], attrs["max_jumps"]["type"]), (-3, "s32"))
        self.assertEqual((attrs["gravity"]["value"], attrs["gravity"]["key"]), (0.25, "air.gravity"))
        self.assertEqual(attrs["weight"]["value"], 104.0)
        archive.data = archive.data[:0x24]
        with self.assertRaisesRegex(ValueError, "truncated"):
            host.read_common_attributes(archive)

    def test_move_groups_use_nonempty_subaction_rows_and_include_air_specials(self):
        rows = [{"id": f"subaction:{index}", "name": name, "empty": empty}
                for index, name, empty in [(4, "Attack11", False), (5, "Attack12", True),
                                            (17, "SpecialSStart", False), (18, "SpecialAirS", False),
                                            (19, "SpecialHi", False), (20, "ThrownF", False)]]
        moves = {m["input"]: m["subactions"] for m in host.build_moves(rows)}
        self.assertEqual(moves, {"jab": ["subaction:4"], "special_s": ["subaction:17", "subaction:18"],
                                 "special_hi": ["subaction:19"]})

    @unittest.skipUnless(os.environ.get("GW_ISO_VANILLA"), "needs local retail disc")
    def test_falcon_build_uses_its_own_symbols_and_resolvable_move_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "host.json"
            result = subprocess.run([sys.executable, str(BUILDER), "falcon", "--out", str(output)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            doc = json.loads(output.read_text())
            checked = subprocess.run([sys.executable, str(BUILDER.with_name("validate.py")), str(output)],
                                     capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertEqual(doc["identity"]["indices"][0]["value"], 2)
        self.assertEqual(doc["assets"]["skeletons"][0]["symbol"], "PlyCaptain5K_Share_joint")
        self.assertEqual({f["name"] for f in doc["resources"]["files"]},
                         {"PlCa.dat", "PlCaNr.dat", "PlCaAJ.dat", "PlCo.dat"})
        self.assertNotIn("ftDataKirby", doc["assets"]["animations"]["indexing"])
        attrs = {a["engine_name"]: a for a in doc["behavior"]["attributes"]["common"]}
        self.assertEqual(attrs["max_jumps"]["value"], 2)
        self.assertEqual(attrs["max_jumps"]["type"], "s32")
        self.assertEqual(attrs["weight"]["value"], 104.0)
        self.assertAlmostEqual(attrs["gravity"]["value"], 0.13)
        rows = {s["id"]: s for s in doc["behavior"]["subactions"]}
        moves = {m["input"]: m for m in doc["behavior"]["moves"]}
        self.assertEqual([rows[r]["name"] for r in moves["jab"]["subactions"]],
                         ["Attack11", "Attack12", "Attack13"])
        self.assertEqual([rows[r]["name"] for r in moves["special_n"]["subactions"]],
                         ["SpecialN", "SpecialAirN"])
        self.assertTrue(all(rows[r]["clip"] for m in moves.values() for r in m["subactions"]))
        self.assertTrue(all(j.get("id") for j in doc["assets"]["skeletons"][0]["joints"]))


if __name__ == "__main__":
    unittest.main()
