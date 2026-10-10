"""The integrity gate must reject broken links and stale bulk-data pointers."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / "tools/check_ir_integrity.py"


class IntegrityTests(unittest.TestCase):
    def load_gate(self):
        self.assertTrue(TOOL.is_file(), "Independent integrity gate is missing")
        spec = importlib.util.spec_from_file_location("goku_integrity", TOOL)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        return gate

    def test_external_parity_checks_document_and_entity(self):
        gate = self.load_gate()
        doc = {"document_id": "goku.xv2", "things": [{"id": "move:jab"}],
               "evidence": [{"id": "ev:parser", "path": "https://github.com/LazyBone152/XV2-Tools"}],
               "parity": [{"here": "move:jab", "there": "falcon.melee#move:missing"}]}
        host = {"document_id": "falcon.melee", "things": [{"id": "move:jab"}]}
        self.assertTrue(any("move:missing" in e for e in gate.check_references(doc, host)))
        doc["parity"][0]["there"] = "wrong.document#move:jab"
        self.assertTrue(any("wrong.document" in e for e in gate.check_references(doc, host)))
        doc["parity"][0]["there"] = "falcon.melee#move:jab"
        self.assertEqual(gate.check_references(doc, host), [])

    def test_blob_hash_and_json_pointer_are_checked_against_the_file(self):
        gate = self.load_gate()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "data.json"
            path.write_text('{"a/b": [{"~key": 42}]}', encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            blob = {"kind": "sidecar", "path": str(path), "sha256": digest,
                    "note": "JSON Pointer /a~1b/0/~0key; checksum covers the entire sidecar."}
            self.assertEqual(gate.check_files({"data": blob, "joints": [{"index": 0}]}, Path(temp))[0], [])
            blob["note"] = "JSON Pointer /a~1b/9; checksum covers the entire sidecar."
            self.assertTrue(any("pointer" in e for e in gate.check_files({"data": blob}, Path(temp))[0]))
            blob["sha256"] = "0" * 64
            self.assertTrue(any("hash" in e for e in gate.check_files({"data": blob}, Path(temp))[0]))

    def test_event_frame_must_match_decoded_record_not_only_valid_pointer(self):
        gate = self.load_gate()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bac.json"
            path.write_text(json.dumps({"entries": [{"events": [{"typeId": 1, "kind": "Hitbox",
                                                                  "startFrame": 12, "durationFrames": 4}]}]}))
            blob = {"kind": "sidecar", "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            doc = {"resources": {"files": [{"id": "file:example.bac", "engine": {"xv2.pc": {"decoded": blob}}}]},
                   "event": {"op": "hitbox.create", "frame": 13, "raw": {"opcode": 1, "engine_name": "Hitbox"},
                             "args": {"engine": {"xv2.pc": {"source_file": "file:example.bac",
                                                           "decoded_pointer": "/entries/0/events/0", "duration_frames": 4}}}}}
            self.assertTrue(any("startFrame mismatch" in e for e in gate.check_files(doc, Path(temp))[0]))
            doc["event"]["frame"] = 12
            self.assertEqual(gate.check_files(doc, Path(temp))[0], [])

    def test_semantics_rejects_missing_raw_and_invented_source_values(self):
        gate = self.load_gate()
        root = TOOL.parents[3]
        source_ir = TOOL.parents[1] / "ir/goku.xv2.ir.json"
        if not source_ir.is_file():
            self.skipTest("needs generated source IR")
        doc = json.loads(source_ir.read_text(encoding="utf-8"))
        host = json.loads((TOOL.parents[1] / "ir/host.melee.ir.json").read_text())
        package = Path(doc["integration"]["hosts"][0]["engine_detail"]["xv2.pc"]["source_package"])
        if not package.is_dir():
            self.skipTest("needs immutable shallow source package")
        omitted = next(r for r in doc["resources"]["files"] if r.get("local_path"))
        doc["resources"]["files"].remove(omitted)
        gravity = next(a for a in doc["behavior"]["attributes"]["common"] if a["engine_name"] == "gravity")
        gravity["value"] = 0.13
        gravity["provenance"]["confidence"] = "observed"
        errors = gate.check_semantics(doc, host, package, root)
        self.assertTrue(any("Raw file absent" in e and omitted["name"] in e for e in errors))
        self.assertTrue(any("runtime-observed" in e for e in errors))
        self.assertTrue(any("Source attribute falsely populated: gravity" in e for e in errors))

    def test_graph_enters_cannot_drop_a_decoded_child_edge(self):
        gate = self.load_gate()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bcm.json"
            path.write_text(json.dumps({"nodes": [
                {"id": "0", "sourceId": "0", "parent": None, "inputLabels": "0", "inputMask": 0, "sourceFields": {}},
                {"id": "0/0", "sourceId": "1", "parent": "0", "inputLabels": "Attack", "inputMask": 1, "sourceFields": {}}]}))
            blob = {"kind": "sidecar", "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            doc = {"resources": {"files": [{"id": "file:example.bcm", "engine": {"xv2.pc": {"decoded": blob}}}]},
                   "action": {"id": "action:example.bcm/0", "name": "0", "enters": [],
                              "index": {"space": "xv2.bcm.node", "value": 0},
                              "engine": {"xv2.pc": {"source_file": "file:example.bcm", "scope": "example.bcm",
                                                    "decoded_pointer": "/nodes/0", "input_mask": 0, "bac_bindings": {}}}}}
            self.assertTrue(any("graph edges" in e for e in gate.check_files(doc, Path(temp))[0]))
            doc["action"]["enters"] = ["action:example.bcm/0/0"]
            self.assertEqual(gate.check_files(doc, Path(temp))[0], [])


if __name__ == "__main__":
    unittest.main()
