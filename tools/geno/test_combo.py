"""tools.geno.combo: the combo graph checks (geno 11)."""
import unittest
from pathlib import Path

from tools.geno import combo


def diag(path, message, source=None):
    return {"path": path, "message": message}


def fighter(routes, strings=(), lua=None):
    f = {"define": {"key": "t"}, "states": [{"name": "Light2"}, {"name": "Heavy"}],
         "combo": {"max_links": 3, "routes": routes, "strings": list(strings)}}
    if lua:
        f["lua"] = lua
    return f


class ComboChecks(unittest.TestCase):
    def run_checks(self, f, geno=11):
        errors, warnings = [], []
        combo.checks({"geno": geno, "fighters": [f]}, f, "$.f", Path("."), errors, warnings, diag)
        return errors, warnings

    def test_clean_graph_and_string(self):
        f = fighter([{"from": "jab1", "to": "geno:Light2", "input": "light"},
                     {"from": "geno:Light2", "to": "geno:Heavy", "input": "heavy"}],
                    [{"name": "s", "steps": ["jab1", "geno:Light2", "geno:Heavy"]}])
        self.assertEqual(self.run_checks(f), ([], []))

    def test_version_unknown_state_and_missing_string_route(self):
        f = fighter([{"from": "jab1", "to": "geno:Nope", "input": "light"}],
                    [{"name": "s", "steps": ["jab1", "geno:Heavy"]}])
        errors, _ = self.run_checks(f, geno=10)
        text = " ".join(e["message"] for e in errors)
        self.assertIn('needs "geno": 11', text)
        self.assertIn("no state named 'Nope'", text)
        self.assertIn("no route from 'jab1' to 'geno:Heavy'", text)

    def test_shadow_loop_gate_and_length(self):
        f = fighter([{"from": "jab1", "to": "geno:Light2", "input": "light", "priority": 5},
                     {"from": "jab1", "to": "geno:Heavy", "input": "light"},
                     {"from": "geno:Light2", "to": "geno:Light2", "input": "light", "when": {"slot": "armed"}}],
                    [{"name": "long", "steps": ["jab1", "geno:Light2", "geno:Light2", "geno:Light2", "geno:Light2"]}])
        errors, warnings = self.run_checks(f)
        self.assertTrue(any("shadowed" in w["message"] for w in warnings))
        self.assertTrue(any("loop" in w["message"] for w in warnings))
        self.assertTrue(any("lua.state" in e["message"] for e in errors))
        self.assertTrue(any("max_links is 3" in e["message"] for e in errors))

    def test_attach_refused(self):
        f = {"attach": "mario", "combo": {"routes": []}}
        errors, _ = self.run_checks(f)
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
