"""Authored fixtures for bare-scene eligibility and recorded-probe diagnosis."""
import copy
import json

import pytest

from falcon import previewability


def plan(*, frames=13, flags=0):
    return {"bank": {"clips": {"Punch": {"frames": frames}}},
            "row_clips": ["Punch"], "row_flags": [flags]}


def row(motion=44, *, subaction=0, clip="Punch"):
    return {"name": "authored_move", "motions": [motion], "subaction": subaction,
            "pick": {"clip": clip}, "script": "moves/authored.genoasm"}


def probe(message, motion=44):
    return previewability.parse_sweep(
        f"authored_move [{motion}] refused: {message}\n")[0]


def test_sample_count_is_not_a_one_based_end_frame():
    # A 13-sample fixture has an entry pose and move frames 1..12.
    status = previewability.classify_row(row(), plan())
    assert status.previewable
    assert status.clip_end_frame == 12


@pytest.mark.parametrize("subaction,category", [(-1, "no-fixed-animation"), (0, "missing-clip")])
def test_explicit_empty_clip_does_not_fall_back_to_plan(subaction, category):
    status = previewability.classify_row(row(subaction=subaction, clip=""), plan())
    assert not status.previewable
    assert status.category == category
    assert status.reason
    assert status.clip_end_frame is None


def test_omitted_pick_can_resolve_a_subaction_clip():
    source = row()
    del source["pick"]
    assert previewability.classify_row(source, plan()).previewable


def test_crop_reduces_the_available_sample_range():
    source = row()
    source["pick"]["crop_start"] = 3
    assert previewability.classify_row(source, plan()).clip_end_frame == 9


@pytest.mark.parametrize("frames", [0, 1])
def test_a_clip_without_a_move_frame_is_not_previewable(frames):
    status = previewability.classify_row(row(), plan(frames=frames))
    assert not status.previewable
    assert status.category == "no-playable-frames"


def test_unknown_bank_clip_is_a_data_error_not_a_context_refusal():
    status = previewability.classify_row(row(clip="Absent"), plan())
    assert not status.previewable
    assert status.category == "invalid-clip-reference"


@pytest.mark.parametrize("motion", [15, 16, 17, 21, 22, 40, *range(75, 87), 91,
    178, 179, 182, 192, 211, 245, 246, 250, 252, 253, 260, 261, 262, 297, 298, 300])
def test_known_bare_scene_transitions_have_a_reason_even_with_a_long_clip(motion):
    status = previewability.classify_row(row(motion), plan(frames=101))
    assert not status.previewable
    assert status.category == "requires-gameplay-context"
    assert status.reason


@pytest.mark.parametrize("motion,word", [(12, "platform"), (223, "partner"), (308, "item")])
def test_engine_context_refusals_name_the_missing_context(motion, word):
    status = previewability.classify_row(row(motion), plan())
    assert not status.previewable
    assert word in status.reason.lower()


def test_loop_flag_does_not_disable_an_otherwise_valid_move():
    status = previewability.classify_row(row(48), plan(flags=0x40000000))
    assert status.previewable
    assert status.looping
    wrapped = previewability.classify_probe(row(48), plan(flags=0x40000000), probe(
        "frame 14 is past the end of this move (the fighter is at frame 2 of action 48)", 48))
    assert wrapped.category == "loop-wrap"
    assert wrapped.previewable
    assert wrapped.playable_end_frame is None


def test_frame_zero_mismatch_is_a_numbering_issue_not_a_short_move():
    status = previewability.classify_probe(row(), plan(), probe(
        "frame 0 is past the end of this move (the fighter is at frame 1 of action 44)"))
    assert status.category == "frame-numbering-convention"
    assert status.previewable
    assert status.playable_end_frame is None


def test_returned_frame_of_a_different_action_is_never_used_as_move_end():
    status = previewability.classify_probe(row(), plan(), probe(
        "frame 1 is past the end of this move (the fighter is at frame 0 of action 24)"))
    assert not status.previewable
    assert status.category == "action-transition"
    assert status.observed_motion == 24
    assert status.playable_end_frame is None
    assert status.clip_end_frame == 12


def test_request_beyond_clip_end_keeps_the_earlier_move_frames_previewable():
    status = previewability.classify_probe(row(), plan(), probe(
        "frame 13 is past the end of this move (the fighter is at frame 12 of action 44; last frame 12)"))
    assert status.previewable
    assert status.category == "past-clip-end"
    assert status.playable_end_frame == 12


def test_request_within_clip_can_still_end_at_an_earlier_action_frame():
    status = previewability.classify_probe(row(), plan(frames=31), probe(
        "frame 20 is past the end of this move (the fighter is at frame 0 of action 45; last frame 15)"))
    assert status.previewable
    assert status.category == "action-ended"
    assert status.playable_end_frame == 15
    assert status.clip_end_frame == 30


def test_unavailable_special_is_engine_evidence_not_a_bad_source_motion_id():
    status = previewability.classify_probe(row(347), plan(), probe(
        "[console] console:1: no such motion for this fighter", 347))
    assert not status.previewable
    assert status.category == "engine-motion-unavailable"
    # Source metadata must not permanently blacklist a valid template special.
    assert previewability.classify_row(row(347), plan()).previewable


def test_sweep_parser_ignores_headers_tracebacks_and_summary_without_leaking_paths():
    text = ("WB_SERVE port=1234 engine=<local executable>\n"
            "authored_move [44] refused: frame 1 is past the end of this move "
            "(the fighter is at frame 0 of action 24)\n"
            "\t[C]: in field 'row'\n"
            "wait [14] ok\n"
            "SWEEP rows=2 refused=1 dead=0 failed=[]\n")
    records = previewability.parse_sweep(text)
    assert [(r.name, r.motion, r.outcome) for r in records] == [
        ("authored_move", 44, "past-end"), ("wait", 14, "ok")]
    assert records[0].requested_frame == 1
    assert records[0].observed_frame == 0
    assert records[0].observed_motion == 24


def test_refresh_preserves_authored_rows_picks_windows_and_sources():
    gameplay = {"note": "keep", "moves": [row(15), row()]}
    gameplay["moves"][0]["windows"] = [[3, 2]]
    before = copy.deepcopy(gameplay)
    updated = previewability.annotate_gameplay(gameplay, plan())
    assert gameplay == before
    assert updated["moves"][0]["previewable"] is False
    assert updated["moves"][0]["preview_reason"]
    assert updated["moves"][1]["previewable"] is True
    assert updated["moves"][1]["preview_reason"] == ""
    for old, new in zip(before["moves"], updated["moves"]):
        for key, value in old.items():
            assert new[key] == value


def test_refresh_removes_stale_classifier_reason_when_a_missing_clip_is_assigned():
    source = row()
    source.update(previewable=False, preview_reason="old missing clip", preview_class="missing-clip")
    updated = previewability.annotate_gameplay({"moves": [source]}, plan())["moves"][0]
    assert updated["previewable"] is True
    assert updated["preview_reason"] == ""


def test_recorded_engine_unavailability_does_not_survive_a_source_refresh():
    source = {"moves": [row(347)]}
    recorded = previewability.annotate_gameplay(source, plan(), [probe(
        "[console] console:1: no such motion for this fighter", 347)])
    assert recorded["moves"][0]["previewable"] is False
    refreshed = previewability.annotate_gameplay(recorded, plan())
    assert refreshed["moves"][0]["previewable"] is True
    assert refreshed["moves"][0]["pick"] == source["moves"][0]["pick"]


def test_cli_annotation_is_source_only_even_with_recorded_engine_evidence(tmp_path):
    gameplay_path = tmp_path / "gameplay.json"
    plan_path = tmp_path / "plan.json"
    sweep_path = tmp_path / "sweep.log"
    report_path = tmp_path / "audit.md"
    gameplay_path.write_text(json.dumps({"moves": [row(347)]}), encoding="utf-8")
    plan_path.write_text(json.dumps(plan()), encoding="utf-8")
    sweep_path.write_text("authored_move [347] refused: no such motion for this fighter\n", encoding="utf-8")
    assert previewability.main([
        "--gameplay", str(gameplay_path), "--plan", str(plan_path),
        "--sweep", str(sweep_path), "--report", str(report_path), "--annotate",
    ]) == 0
    annotated = json.loads(gameplay_path.read_text(encoding="utf-8"))["moves"][0]
    assert annotated["previewable"] is True
    assert annotated["preview_reason"] == ""
    assert "engine-motion-unavailable" in report_path.read_text(encoding="utf-8")


def test_blender_row_help_uses_the_classifiers_reason_and_refreshes_it(monkeypatch):
    from types import SimpleNamespace
    import props
    source = row()
    source.update(previewable=False, preview_reason="This row needs initialized hitstun.")
    monkeypatch.setattr(props, "_session", lambda: SimpleNamespace(rows=[source]))
    assert props.row_items()[1][2] == source["preview_reason"]
    source["preview_reason"] = "The current engine has no such motion."
    assert props.row_items()[1][2] == source["preview_reason"]
