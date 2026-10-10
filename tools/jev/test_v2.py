import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import confidence
import coverage
import check_claims
import runparse
import triage_run

PASS_LOG = """[frame=1 ms=10] gw: mods: C:\\x\\mods - 2 mod(s), enabled set from enabled.txt
[frame=1 ms=10] gw: mods:   goku-xv2                 fighter 0.2.0    on
[frame=2 ms=20] gw: scene: MELEE_SCENE="mode=lab;p1=geno:goku-xv2/hu;stage=fd"
[frame=700 ms=4000] script [pad_script] GROUNDTRACE RESULT PASS DONE
[frame=701 ms=4010] aurora[warning] aurora::gpu: Device lost: Device was destroyed.
[frame=701 ms=4020] melee-pc: aurora teardown faulted inside Dawn (0xC0000005); ignored at exit
gw: launcher final reason=OK code=0
"""
TIMEOUT_SETUP = """[frame=0 ms=0] gw: turbo: refused without a pad script or LAB batch export
[frame=2 ms=20] gw: scene: MELEE_SCENE: rejected "p1=geno:goku-xv2/hu" -- a number in a character or stage field must name its index space
[frame=9 ms=90] gw: heartbeat retrace=100 presented=10
[frame=19 ms=190] gw: heartbeat retrace=200 presented=20
gw: launcher final reason=TIMEOUT code=124
"""


class RunParse(unittest.TestCase):
    def test_pass_run_with_benign_teardown_fault_is_pass(self):
        p = runparse.parse_text(PASS_LOG)
        self.assertEqual((p["class"], p["decided"], p["fault_count"]), ("pass", True, 0))

    def test_result_without_verdict_and_clean_exit_is_not_a_bug(self):
        p = runparse.parse_text("script [pad_script] LANDCHECK RESULT cases=40 sinking=0\ngw: launcher final reason=OK code=0\n")
        self.assertEqual(p["class"], "clean_no_verdict")

    def test_fail_line_wins_over_pass(self):
        p = runparse.parse_text("COMBOTEST RESULT: PASS (2 cells)\nKITEST RESULT: FAIL kicharge\nmelee-pc: exit 0\n")
        self.assertEqual((p["class"], p["results"]["counts"]), ("test_fail", {"pass": 1, "fail": 1}))

    def test_tests_summary_line(self):
        self.assertEqual(runparse.parse_text("TESTS: pass=12 fail=0\nmelee-pc: exit 0\n")["class"], "pass")
        self.assertEqual(runparse.parse_text("TESTS: pass=11 fail=1\n")["class"], "test_fail")
        self.assertEqual(runparse.parse_text("TESTS: TIMEOUT\n")["class"], "test_fail")

    def test_turbo_refused_scene_rejected_timeout_is_harness_setup(self):
        p = runparse.parse_text(TIMEOUT_SETUP)
        self.assertEqual((p["class"], p["decided"]), ("harness_setup", True))
        self.assertIn("scene_rejected", p["setup"])
        self.assertIn("turbo_refused", p["setup"])
        self.assertTrue(p["exit"]["timeout"])

    def test_missing_expected_mod_is_setup(self):
        log = "gw: mods: C:\\m - 1 mod(s), enabled set from enabled.txt\ngw: mods:   envoy                    script  0.5.0    on\nmelee-pc: exit 0\n"
        p = runparse.parse_text(log, expect_mods=["goku-xv2"])
        self.assertEqual((p["class"], p["cause"]), ("harness_setup", "mod_missing"))
        self.assertEqual(p["mods"]["missing"], ["goku-xv2"])

    def test_disk_full_and_sandbox(self):
        self.assertEqual(runparse.parse_text("write failed: No space left on device\n")["cause"], "disk_full")
        self.assertEqual(runparse.parse_text("error: sandbox is active or retained a launch marker; choose a new sandbox name\n")["cause"], "sandbox_failure")

    def test_turbo_refused_alone_with_pass_stays_pass(self):
        p = runparse.parse_text("gw: turbo: refused without a pad script or LAB batch export\nGRABCHECK case=a side=1 PASS free\nmelee-pc: exit 0\n")
        self.assertEqual(p["class"], "pass")

    def test_timeout_without_signals_is_decided_but_cause_open(self):
        p = runparse.parse_text("gw: launcher final reason=TIMEOUT code=124\n")
        self.assertEqual((p["class"], p["cause"]), ("timeout", "unexplained"))

    def test_assertion_is_fault_with_signature(self):
        log = "a\nb\n[frame=3 ms=1] assertion \"Geno_DefinePlanInt(kind, 0, 0)\" failed in pc\\geno/geno_define_data.inc on line 215.\nmelee-pc: exit 1\n"
        p = runparse.parse_text(log)
        self.assertEqual((p["class"], p["decided"]), ("fault", False))
        self.assertIn("geno_define_data.inc", json.dumps(p["signature"]))

    def test_summary_footer_fatal_zero_is_not_a_fault(self):
        p = runparse.parse_text("GRABCHECK case=a PASS ok\nexit      0\nFATAL     0\n")
        self.assertEqual((p["class"], p["fault_count"]), ("pass", 0))

    def test_run_directory_reads_exit_json_and_crashlog(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "melee-pc.log").write_text("hello\n")
            (d / "exit.json").write_text(json.dumps({"reason": "clean shutdown", "code": 0}))
            self.assertEqual(runparse.parse(d)["class"], "clean_no_verdict")
            (d / "crashlogs").mkdir()
            (d / "crashlogs" / "c.log").write_text("access violation at 0x0\n")
            self.assertEqual(runparse.parse(d)["class"], "fault")

    def test_signature_is_bounded_and_redacted(self):
        log = "\n".join("line %d C:\\Users\\me\\x" % i for i in range(200)) + "\nFATAL boom\n"
        sig = runparse.parse_text(log)["signature"]
        self.assertLessEqual(len(json.dumps(sig)), 2000)
        self.assertNotIn("Users", json.dumps(sig))


class Triage(unittest.TestCase):
    def test_deterministic_classes_never_call_the_model(self):
        with patch("jev.urlopen", side_effect=AssertionError("network used")):
            for text, want in ((PASS_LOG, "pass"), (TIMEOUT_SETUP, "harness_artifact"), ("COMBOTEST RESULT: FAIL x\n", "test_fail")):
                r = triage_run.classify({}, text)
                self.assertEqual((r["choice"], r["source"]), (want, "code"))

    def test_fault_asks_one_request_with_both_option_orders(self):
        seen = {}

        def fake(state, questions, **kw):
            seen["q"] = questions
            seen["state"] = state
            keys = list(questions["forward"]["criteria"])
            return {n: {"type": "choice", "choice": "geno_define_failure", "probabilities": {k: float(k == "geno_define_failure") for k in keys},
                        "confidence": 0.95, "source": "jev"} for n in questions}
        log = "assertion \"x\" failed in pc/geno/geno_define_data.inc on line 215.\n"
        with patch("jev.call", side_effect=fake):
            r = triage_run.classify({}, log)
        f, rv = list(seen["q"]["forward"]["criteria"]), list(seen["q"]["reversed"]["criteria"])
        self.assertEqual(f, rv[::-1])
        self.assertEqual((r["choice"], r["band"], r["order_stable"]), ("mod_content", "act", True))
        self.assertEqual(set(seen["state"]), {"crash_signature", "run_facts"})

    def test_order_disagreement_routes_to_human(self):
        def fake(state, questions, **kw):
            keys = list(questions["forward"]["criteria"])
            pick = {"forward": keys[0], "reversed": keys[-1]}
            return {n: {"type": "choice", "choice": pick[n], "probabilities": {k: float(k == pick[n]) for k in keys}, "confidence": 0.99, "source": "jev"} for n in questions}
        with patch("jev.call", side_effect=fake):
            r = triage_run.classify({}, "FATAL access violation\n")
        self.assertEqual((r["choice"], r["band"], r["order_stable"]), ("needs_human", "human", False))

    def test_low_confidence_routes_to_human(self):
        def fake(state, questions, **kw):
            keys = list(questions["forward"]["criteria"])
            return {n: {"type": "choice", "choice": keys[0], "probabilities": {k: 1 / len(keys) for k in keys}, "confidence": 0.3, "source": "jev"} for n in questions}
        with patch("jev.call", side_effect=fake):
            self.assertEqual(triage_run.classify({}, "FATAL x\n")["choice"], "needs_human")

    def test_unavailable_degrades(self):
        with patch("jev.call", return_value=None):
            r = triage_run.classify({}, "FATAL x\n")
        self.assertEqual((r["choice"], r["source"]), ("jev: unavailable", "unavailable"))


class Confidence(unittest.TestCase):
    def test_bands_and_overrides(self):
        a = {"type": "choice", "confidence": 0.7}
        self.assertEqual(confidence.band(a), "confirm")
        self.assertEqual(confidence.band({"type": "choice", "confidence": 0.5}), "human")
        self.assertEqual(confidence.band({"type": "choice", "confidence": 0.9}), "act")
        self.assertEqual(confidence.band(a, {"choice_act": 0.6}), "act")
        self.assertEqual(confidence.band(None), "human")

    def test_noul_state(self):
        self.assertEqual([confidence.noul_state(p) for p in (0.95, 0.5, 0.05)], ["yes", "unsure", "no"])

    def test_env_override_cannot_break_defaults(self):
        with patch.dict("os.environ", {"JEV_THRESHOLDS": "not json"}):
            self.assertEqual(confidence.thresholds()["choice_floor"], 0.6)
        with patch.dict("os.environ", {"JEV_THRESHOLDS": '{"choice_floor": 0.7}'}):
            self.assertEqual(confidence.thresholds()["choice_floor"], 0.7)


BRIEF = """- [ ] Fix the landing sink bug in tools/jev
- [ ] Add 12 tests for runparse
2. Update the README with the new tools
"""
REPORT = """Landing sink bug fixed: 40/40 cases sinking=0 (log _build/x/melee-pc.log).
Tests added: 12 tests in test_v2.py, all pass.
README update is owed; not done yet.
"""


class Coverage(unittest.TestCase):
    def test_requirements_parse(self):
        self.assertEqual([r["text"] for r in coverage.requirements(BRIEF)][2], "Update the README with the new tools")

    def test_retrieval_selects_relevant_lines_only(self):
        passages, _ = coverage.retrieve("Update the README with the new tools", REPORT)
        self.assertTrue(any("README" in p for p in passages))

    def test_offline_statuses(self):
        res = coverage.coverage(BRIEF, REPORT, offline=True)
        self.assertEqual([r["status"] for r in res["requirements"]], ["done", "done", "owed"])

    def test_no_match_is_unaddressed_without_model_call(self):
        with patch("jev.urlopen", side_effect=AssertionError("network used")):
            res = coverage.coverage("- Rotate the zebra", REPORT)
        self.assertEqual(res["requirements"][0]["status"], "unaddressed")

    def test_combine_rules(self):
        def a(c, e, o):
            return {"completed": {"noul": c}, "evidence": {"noul": e}, "owed": {"noul": o}}
        self.assertEqual(coverage.combine(a(.95, .9, .05))[0], "done")
        self.assertEqual(coverage.combine(a(.95, .1, .05))[:2], ("unclear", False))
        self.assertEqual(coverage.combine(a(.95, .9, .95))[:2], ("unclear", True))
        self.assertEqual(coverage.combine(a(.5, .9, .05))[:2], ("unclear", True))
        self.assertEqual(coverage.combine(a(.05, .1, .9))[0], "owed")
        self.assertEqual(coverage.combine(a(.05, .1, .05))[0], "unaddressed")

    def test_payload_contains_only_relevant_excerpt(self):
        seen = []

        def fake(state, questions, **kw):
            seen.append(json.dumps(state))
            return {k: {"type": "noul", "noul": 0.9, "source": "jev"} for k in questions}
        with patch("jev.call", side_effect=fake):
            coverage.coverage("- Update the README", REPORT)
        self.assertEqual(len(seen), 1)
        self.assertNotIn("sinking", seen[0])


class Claims(unittest.TestCase):
    def test_tests_and_build_never_use_the_model(self):
        with tempfile.TemporaryDirectory() as d, patch("jev.urlopen", side_effect=AssertionError("network used")):
            log = Path(d) / "t.log"
            log.write_text("10/10 tests pass\nBuild OK\n")
            r = check_claims.check("10/10 tests pass. Build OK.", [log])
            self.assertEqual([c["verdict"] for c in r], ["supported", "supported"])
            self.assertEqual({c["source"] for c in r}, {"code"})

    def test_runs_pass_claim_uses_runparse(self):
        with tempfile.TemporaryDirectory() as d:
            ok, bad = Path(d) / "ok", Path(d) / "bad"
            for p, txt in ((ok, "X RESULT PASS\nmelee-pc: exit 0\n"), (bad, "X RESULT FAIL\n")):
                p.mkdir()
                (p / "melee-pc.log").write_text(txt)
            self.assertEqual(check_claims.check("all runs PASS", [ok])[0]["verdict"], "supported")
            self.assertEqual(check_claims.check("all runs PASS", [ok, bad])[0]["verdict"], "unsupported")


if __name__ == "__main__":
    unittest.main()
