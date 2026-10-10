"""Source attributes, drafts and batch failures against the synthetic MCP engine."""
import copy
import math

import pytest
import api
import client
from attributes import AttributeDraft, validate_value
from fake_engine import FakeWorkbench


@pytest.fixture
def connected():
    fake = FakeWorkbench()
    port = fake.start()
    sess = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
    assert sess.connect(), sess.last_error
    try:
        yield fake, sess
    finally:
        sess.disconnect()
        fake.stop()


def row(sess, name):
    return next(item for item in sess.attributes if item["name"] == name)


def test_refresh_metadata_and_failed_refresh_retains_previous_list(connected):
    fake, sess = connected
    assert sess.refresh_attributes(), sess.last_error
    assert row(sess, "weight")["value"] == 73.25
    assert row(sess, "walk_max_vel")["group"] == "ground"
    assert row(sess, "jumps.max")["range"] == {"minimum": 1, "maximum": 250}
    assert row(sess, "gravity")["source_file"] == "gameplay.json"
    before = copy.deepcopy(sess.attributes)
    fake.fail_next = "changed externally: gameplay.json"
    assert not sess.refresh_attributes()
    assert sess.attributes == before and sess.connected


def test_attribute_edit_updates_source_and_stale_without_changing_pose(connected):
    fake, sess = connected
    assert sess.load_row("jab") and sess.set_frame(7)
    assert sess.refresh_attributes()
    before = (copy.deepcopy(sess.info), sess.row, sess.frame)
    fired = []
    sess.on_frame.append(lambda value: fired.append(value.frame))
    assert sess.edit_attribute("weight", 81.5), sess.last_error
    assert row(sess, "weight")["value"] == 81.5 and sess.stale
    assert (sess.info, sess.row, sess.frame) == before and fired == []
    assert fake.loaded_attributes["weight"] == 73.25
    assert sess.rebuild_reload(), sess.last_error
    assert fake.loaded_attributes["weight"] == 81.5
    assert not sess.stale and (sess.row, sess.frame) == ("jab", 7)


@pytest.mark.parametrize("name,value", [
    ("jumps.max", 0), ("jumps.max", 251), ("jumps.max", 1.5),
    ("weight", True), ("weight", "80"), ("weight", None),
    ("weight", math.inf), ("weight", math.nan), ("unknown", 2),
])
def test_invalid_edit_is_refused_before_sending(connected, name, value):
    fake, sess = connected
    assert sess.refresh_attributes()
    before = copy.deepcopy(sess.attributes)
    calls = len(fake.calls)
    assert not sess.edit_attribute(name, value)
    assert len(fake.calls) == calls and sess.attributes == before and not sess.stale


def test_proposed_edit_keeps_source_values_and_existing_stale_marker(connected):
    fake, sess = connected
    assert sess.refresh_attributes()
    fake.attribute_proposals = True
    assert sess.edit_attribute("weight", 81.5), sess.last_error
    assert row(sess, "weight")["value"] == 73.25 and not sess.stale
    assert "proposal" in sess.status
    sess.stale = True
    assert sess.edit_attribute("weight", 81.5)
    assert sess.stale and row(sess, "weight")["value"] == 73.25


def test_noop_reply_does_not_mark_source_stale(connected):
    fake, sess = connected
    assert sess.refresh_attributes()
    assert sess.edit_attribute("weight", 73.25)
    assert not sess.stale


def test_edit_failure_and_failed_rebuild_keep_source_and_selection(connected):
    fake, sess = connected
    assert sess.refresh_attributes() and sess.load_row("jab") and sess.set_frame(7)
    before = copy.deepcopy(sess.attributes)
    fake.fail_next = "changed externally: gameplay.json"
    assert not sess.edit_attribute("weight", 81.5)
    assert sess.attributes == before and not sess.stale
    assert sess.edit_attribute("weight", 81.5)
    fake.fail_next = "build failed"
    assert not sess.rebuild_reload()
    assert sess.stale and (sess.row, sess.frame) == ("jab", 7)
    assert row(sess, "weight")["value"] == 81.5


def test_reconnect_clears_attribute_cache(connected):
    fake, sess = connected
    assert sess.refresh_attributes() and sess.attributes
    assert sess.connect()
    assert sess.attributes == []


def test_drafts_filter_group_and_only_apply_changed_values(connected):
    fake, sess = connected
    assert sess.refresh_attributes()
    draft = AttributeDraft(sess.attributes)
    draft.set("weight", 81.5)
    draft.set("walk_max_vel", 1.75)
    draft.set("gravity", 0.125)
    assert draft.changed == {"weight": 81.5, "walk_max_vel": 1.75}
    assert [item["name"] for item in draft.filtered("WaLK", "ground")] == ["walk_max_vel"]
    assert [item["name"] for item in draft.filtered("weight")] == ["weight"]
    assert draft.apply(sess), sess.last_error
    assert draft.changed == {} and sess.stale
    edits = [args for name, args in fake.calls if name == "edit_attribute"]
    assert edits == [{"name": "weight", "value": 81.5}, {"name": "walk_max_vel", "value": 1.75}]
    assert row(sess, "weight")["value"] == 81.5


def test_partial_batch_failure_keeps_unsent_draft_and_successful_source(connected):
    fake, sess = connected
    assert sess.refresh_attributes()
    draft = AttributeDraft(sess.attributes)
    draft.set("weight", 81.5)
    draft.set("walk_max_vel", 1.75)
    real = fake._execute
    def fail_second(tool, args):
        if tool == "edit_attribute" and args["name"] == "walk_max_vel":
            raise ValueError("changed externally: gameplay.json")
        return real(tool, args)
    fake._execute = fail_second
    assert not draft.apply(sess)
    assert draft.changed == {"walk_max_vel": 1.75}
    assert row(sess, "weight")["value"] == 81.5 and sess.stale
    assert "changed externally" in sess.last_error


def test_batch_stops_at_first_proposal_and_keeps_remaining_drafts(connected):
    fake, sess = connected
    assert sess.refresh_attributes()
    draft = AttributeDraft(sess.attributes)
    draft.set("weight", 81.5)
    draft.set("walk_max_vel", 1.75)
    fake.attribute_proposals = True
    assert draft.apply(sess)
    assert draft.changed == {"weight": 81.5, "walk_max_vel": 1.75} and not sess.stale
    edits = [args for name, args in fake.calls if name == "edit_attribute"]
    assert edits == [{"name": "weight", "value": 81.5}]
    assert "proposal" in sess.status


def test_refresh_keeps_dirty_values_but_tracks_new_server_baseline(connected):
    fake, sess = connected
    assert sess.refresh_attributes()
    draft = AttributeDraft(sess.attributes)
    draft.set("weight", 81.5)
    assert sess.edit_attribute("gravity", 0.2) and sess.refresh_attributes()
    draft.refresh(sess.attributes)
    assert draft.changed == {"weight": 81.5}
    assert draft.value("gravity") == 0.2


def test_missing_inherited_values_require_explicit_override():
    metadata = {"name": "weight", "value": None, "type": "number", "group": "misc",
                "range": {"minimum": None, "maximum": None}, "description": "Weight", "unit": "weight"}
    draft = AttributeDraft([metadata])
    assert draft.changed == {} and draft.value("weight") is None
    draft.set("weight", 12.5)
    assert draft.changed == {"weight": 12.5}
    draft.reset("weight")
    assert draft.changed == {} and draft.value("weight") is None


@pytest.mark.parametrize("value", [-2.5, 0, 1e4])
def test_no_physical_range_is_invented_for_unbounded_schema_numbers(value):
    meta = {"name": "gravity", "type": "number", "range": {"minimum": None, "maximum": None}}
    assert validate_value(meta, value) == value


def test_post_commit_refresh_failure_retains_unsent_scene_drafts(connected, monkeypatch):
    import types
    import panels_attributes as panel
    fake, sess = connected
    assert sess.refresh_attributes()
    monkeypatch.setattr(api, "_session", sess)
    monkeypatch.setattr(panel, "_drafts", {})
    scene = types.SimpleNamespace(as_pointer=lambda: 14)
    draft = panel._record(scene)["draft"]
    draft.set("weight", 81.5)
    draft.set("walk_max_vel", 1.75)
    monkeypatch.setattr(sess, "on_change", lambda value: panel._record(scene))
    real = fake._execute
    committed = False
    def lose_refresh(tool, args):
        nonlocal committed
        if tool == "list_attributes" and committed:
            raise ValueError("source refresh failed")
        result = real(tool, args)
        if tool == "edit_attribute":
            committed = True
        return result
    fake._execute = lose_refresh
    assert not draft.apply(sess)
    assert draft.changed == {"walk_max_vel": 1.75}
    assert row(sess, "weight")["value"] == 81.5 and sess.stale
    assert not sess.attributes_current and "refresh failed" in sess.last_error


def test_unset_air_impulse_can_be_applied_without_loading_an_engine_default(connected):
    fake, sess = connected
    assert sess.refresh_attributes()
    assert row(sess, "jumps.air_vy.0")["value"] is None
    draft = AttributeDraft(sess.attributes)
    draft.set("jumps.air_vy.0", 2.5)
    assert draft.apply(sess), sess.last_error
    assert draft.changed == {} and sess.stale
    assert row(sess, "jumps.air_vy.0")["value"] == 2.5
    assert row(sess, "jumps.air_vy.1")["value"] is None
    assert fake.loaded_attributes["jumps.air_vy.0"] is None
    assert sess.rebuild_reload(), sess.last_error
    assert fake.loaded_attributes["jumps.air_vy.0"] == 2.5
