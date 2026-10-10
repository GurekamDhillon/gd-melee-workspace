import json
import sys
from pathlib import Path

PORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT / "tools"))
sys.path.insert(0, str(PORT.parents[1]))
import xv2_to_artist as X  # noqa: E402

ROWS = list(X.HOVER_ROWS) + list(X.ANCHOR_ROWS) + list(X.NO_GROUND) + ["AttackAirLw", "Attack11", "Squat", "SquatRv", "Catch", "ThrowF", "Nonexistent"]


def test_empty_file_matches_legacy(tmp_path, monkeypatch):
    p = tmp_path / "g.json"
    p.write_text(json.dumps({"schema": "ground-modes/1", "rows": {}, "grounded_clips": []}))
    monkeypatch.setattr(X, "GROUND_MODES_PATH", p)
    for row in ROWS:
        assert X.ground_mode(row) == X._legacy_ground_mode(row)
        assert X.ground_blend(row) == X._legacy_ground_blend(row)


def test_absent_file_matches_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(X, "GROUND_MODES_PATH", tmp_path / "missing.json")
    for row in ROWS:
        assert X.ground_mode(row) == X._legacy_ground_mode(row)


def test_shipped_file_changes_nothing():
    for row in ROWS:
        assert X.ground_mode(row) == X._legacy_ground_mode(row)
        assert X.ground_blend(row) == X._legacy_ground_blend(row)


def test_file_overrides_exact_row(tmp_path, monkeypatch):
    p = tmp_path / "g.json"
    p.write_text(json.dumps({"schema": "ground-modes/1", "rows": {"Wait": {"mode": "anchored", "blend_in": True, "blend_out": False}}}))
    monkeypatch.setattr(X, "GROUND_MODES_PATH", p)
    assert X.ground_mode("Wait") == "anchor"
    assert X.ground_blend("Wait") == (True, False)
    assert X.ground_mode("Walk") == X._legacy_ground_mode("Walk")


def test_bad_mode_rejected(tmp_path, monkeypatch):
    p = tmp_path / "g.json"
    p.write_text(json.dumps({"schema": "ground-modes/1", "rows": {"Wait": {"mode": "float"}}}))
    monkeypatch.setattr(X, "GROUND_MODES_PATH", p)
    try:
        X.ground_mode("Wait")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "float" in str(e)
