#!/usr/bin/env python3
"""Unit tests for tree.py: python tools/combos/test_tree.py"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tree as T  # noqa: E402

HEADER = {k: "x" for k in T.HEADER_KEYS}
HEADER.update(attacker="fox", victim="falco", stage="fd", rules="000005fb")


def edge(move, result="true", **kw):
    e = {"move": move, "result": result, "inputs": [{"f": 1, "buttons": 256}], "confirmed": 1}
    if result == "true":
        e.update(hit_frame=3, damage=4.0, victim_hitstun=7)
    e.update(kw)
    return e


def result_with(*edges, path="@root"):
    return {"format": 1, "header": {"attacker": "fox", "victim": "falco", "stage": "fd", "rules": "000005fb"},
            "nodes": {path: {"situation": {}, "edges": list(edges)}}}


class TreeTests(unittest.TestCase):
    def test_validate_rejects_bad_result_and_missing_fields(self):
        t = T.new_tree(HEADER)
        t["nodes"]["@root"] = {"situation": {}, "edges": [{"move": "jab", "result": "maybe", "confirmed": 1}]}
        with self.assertRaises(T.TreeError):
            T.validate(t)
        t["nodes"]["@root"]["edges"] = [{"move": "jab", "result": "true", "confirmed": 1}]
        with self.assertRaises(T.TreeError):
            T.validate(t)

    def test_merge_new_then_confirm(self):
        t = T.new_tree(HEADER)
        same, new, conf = T.merge(t, result_with(edge("jab")))
        self.assertEqual((same, new, len(conf)), (0, 1, 0))
        same, new, conf = T.merge(t, result_with(edge("jab")))
        self.assertEqual((same, new, len(conf)), (1, 0, 0))
        self.assertEqual(t["nodes"]["@root"]["edges"][0]["confirmed"], 2)

    def test_merge_conflict_keeps_stored_value(self):
        t = T.new_tree(HEADER)
        T.merge(t, result_with(edge("jab")))
        same, new, conf = T.merge(t, result_with(edge("jab", "broke", broke_frame=5)))
        self.assertEqual(len(conf), 1)
        self.assertEqual(conf[0]["field"], "result")
        stored = t["nodes"]["@root"]["edges"][0]
        self.assertEqual(stored["result"], "true")
        self.assertEqual(stored["confirmed"], 1)
        self.assertEqual(len(stored["conflicts"]), 1)
        _, _, conf = T.merge(t, result_with(edge("jab", damage=4.02)))
        self.assertEqual(len(conf), 0)
        _, _, conf = T.merge(t, result_with(edge("jab", damage=5.0)))
        self.assertEqual(len(conf), 1)

    def test_merge_refuses_other_context(self):
        t = T.new_tree(HEADER)
        r = result_with(edge("jab"))
        r["header"]["stage"] = "bf"
        with self.assertRaises(T.TreeError):
            T.merge(t, r)

    def test_failures_are_kept(self):
        t = T.new_tree(HEADER)
        T.merge(t, result_with(edge("walk", "refused"), edge("dash", "whiff")))
        self.assertEqual(sorted(e["result"] for e in t["nodes"]["@root"]["edges"]), ["refused", "whiff"])

    def test_export_lua_is_a_lua_table_with_keys(self):
        t = T.new_tree(HEADER)
        T.merge(t, result_with(edge("jab"), edge("walk", "refused")))
        text = T.export_lua(t)
        self.assertTrue(text.startswith("-- generated"))
        self.assertIn('["@root"]', text)
        self.assertIn('["key"] = "jab"', text)
        self.assertIn('["result"] = "refused"', text)
        self.assertNotIn("conflicts", text)

    def test_read_results_jsonl(self):
        lines = ['{"header":{"attacker":"fox","victim":"falco","stage":"fd","rules":"000005fb"}}',
                 '{"path":"@root","situation":{},"edge":' + json.dumps(edge("jab")) + "}"]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join(lines) + "\n")
        try:
            r = T.read_results(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(r["nodes"]["@root"]["edges"][0]["move"], "jab")
        t = T.new_tree(HEADER)
        self.assertEqual(T.merge(t, r)[1], 1)

    def test_committed_trees_validate(self):
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tree")
        for name in os.listdir(d):
            if name.endswith(".json"):
                T.load(os.path.join(d, name))


if __name__ == "__main__":
    unittest.main()
