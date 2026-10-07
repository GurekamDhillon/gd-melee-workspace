import json
from pathlib import Path
import tempfile
import unittest

import check_claims
import rank_findings
import triage_run


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_triage_skips_pass_and_loads_sweep_sandboxes(self):
        run = self.root / "runs" / "vanilla-st-icetop"
        run.mkdir(parents=True)
        (run / "melee-pc.log").write_text("FATAL bgm != BGM_Undefined\n")
        rows = [{"tag": "vanilla-st-icetop", "what": "icetop", "kind": "stage", "result": "CRASH"}, {"tag": "ok", "result": "PASS"}]
        path = self.root / "results.json"
        path.write_text(json.dumps(rows))
        result = triage_run.triage_input(path, offline=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["triage"]["choice"], "known_issue")

    def test_single_sweep_directory_retains_stage_identity(self):
        run = self.root / "vanilla-st-icetop"
        run.mkdir()
        (run / "melee-pc.log").write_text("FATAL bgm != BGM_Undefined\n")
        self.assertEqual(triage_run.triage_input(run, offline=True)[0]["triage"]["choice"], "known_issue")

    def test_hang_progress_requires_both_counters_and_no_fault(self):
        row = {"result": "HANG", "detail": "load induced timeout"}
        text = "heartbeat retrace=10 presented=10\nheartbeat retrace=20 presented=20\n"
        self.assertEqual(triage_run.classify(row, text, offline=True)["choice"], "harness_artifact")
        self.assertEqual(triage_run.classify(row, text + "FATAL access violation", offline=True)["choice"], "real_bug")
        self.assertEqual(triage_run.classify(row, text.replace("presented=20", "presented=10"), offline=True)["choice"], "real_bug")

    def test_log_payload_is_bounded_and_retains_crash_tail(self):
        (self.root / "melee-pc.log").write_text("x" * 20000)
        (self.root / "crashlogs").mkdir()
        (self.root / "crashlogs" / "fault.log").write_text("FATAL access violation")
        logs = triage_run.run_logs(self.root)
        self.assertLessEqual(len(logs.encode()), 4096)
        self.assertIn("access violation", logs)

    def test_ranking_preserves_multiline_findings_and_original_severity(self):
        text = "1. HIGH, ui.py:2 cosmetic alignment\n  only at 150% zoom\n2. LOW, save.py:9 crash and data loss when saving\n3. MEDIUM, net.py:4 online desync after reconnect\n"
        ranked = rank_findings.rank(text, offline=True)
        self.assertEqual([r["number"] for r in ranked], [2, 3, 1])
        self.assertEqual(ranked[0]["severity"], "LOW")
        self.assertIn("150% zoom", ranked[-1]["text"])

    def test_claims_distinguish_missing_evidence_and_contradiction(self):
        log = self.root / "build.log"
        log.write_text("10/10 tests pass\nBuild FAILED\n")
        result = check_claims.check("10/10 tests pass. Build OK. Shown in game. No window opened.", [log], offline=True)
        self.assertEqual([r["verdict"] for r in result], ["supported", "unsupported", "no evidence", "no evidence"])

    def test_wrong_test_count_is_unsupported(self):
        log = self.root / "test.log"
        log.write_text("9/10 tests pass\n")
        self.assertEqual(check_claims.check("10/10 tests pass", [log], offline=True)[0]["verdict"], "unsupported")

    def test_repeated_report_detection_without_jev(self):
        self.assertFalse(check_claims.remember_report("same report", self.root))
        self.assertTrue(check_claims.remember_report("same report", self.root))
        self.assertFalse(check_claims.remember_report("different report", self.root))

    def test_conflicting_window_events_are_not_hidden_by_negative_summary(self):
        log = self.root / "window.log"
        log.write_text("window opened\nno window opened\n")
        self.assertEqual(check_claims.check("No window opened", [log], offline=True)[0]["verdict"], "unsupported")

    def test_unrelated_screenshot_is_not_visual_game_proof(self):
        log = self.root / "capture.log"
        log.write_text("screenshot saved of launcher\n")
        self.assertEqual(check_claims.check("Shown in game", [log], offline=True)[0]["verdict"], "no evidence")

    def test_existing_report_in_folder_is_detected_without_saved_hash(self):
        (self.root / "previous.md").write_text("same report")
        self.assertTrue(check_claims.remember_report("same report", self.root))

    def test_missing_triage_path_is_input_error(self):
        with self.assertRaises(OSError):
            triage_run.triage_input(self.root / "absent", offline=True)
