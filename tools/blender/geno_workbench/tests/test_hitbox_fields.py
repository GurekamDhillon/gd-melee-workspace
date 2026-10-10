"""Element, signed shield damage, hit_ground / hit_air and slot in the Blender hitbox editor (R2)."""
import pytest

import api
import client
import hitviz_math as M
import props
from fake_engine import FakeWorkbench


def make():
    fake = FakeWorkbench(); port = fake.start()
    s = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
    s.connect(); s.refresh_rows(); s.load_row("jab"); s.refresh_hitboxes()
    return fake, s


def test_new_fields_are_editable():
    for field in ("element", "shield", "slot", "ground", "air"):
        assert field in api.EDITABLE


def test_each_field_round_trips_through_the_server_and_list():
    fake, s = make()
    try:
        assert s.edit_hitbox(row="jab", ordinal=0, element=16, shield=-3, ground=False, air=True, slot=2)
        name, args = [c for c in fake.calls if c[0] == "edit_hitbox"][-1]
        assert args == {"row": "jab", "ordinal": 0, "element": 16, "shield": -3, "ground": False, "air": True, "slot": 2}
        box = s.hitboxes[0]
        assert (box["element"], box["shield"], box["slot"]) == (16, -3, 2)
        assert box["shield_damage"] == -3 and box["hit_ground"] is False and box["hit_air"] is True and box["wbk"] == box["fkb"]
    finally:
        fake.stop()


@pytest.mark.parametrize("fields", [
    {"shield": 128}, {"shield": -129}, {"slot": 4}, {"slot": -1}, {"element": 32}, {"element": -1},
    {"ground": "yes"}, {"air": 1}, {"shield": 1.5}, {"element": True},
])
def test_bad_values_are_refused_before_anything_is_sent(fields):
    fake, s = make()
    try:
        before = len([c for c in fake.calls if c[0] == "edit_hitbox"])
        assert s.edit_hitbox(row="jab", ordinal=0, **fields) is False
        assert len([c for c in fake.calls if c[0] == "edit_hitbox"]) == before
    finally:
        fake.stop()


def test_negative_shield_and_both_toggles_are_legal():
    fake, s = make()
    try:
        assert s.edit_hitbox(row="jab", ordinal=0, shield=-128)
        assert s.edit_hitbox(row="jab", ordinal=0, shield=127, ground=False, air=False)
        assert s.hitboxes[0]["shield"] == 127 and not s.hitboxes[0]["hit_air"] and not s.hitboxes[0]["hit_ground"]
    finally:
        fake.stop()


def test_hitviz_badges_light_up_from_the_launcher_record():
    fake, s = make()
    try:
        s.edit_hitbox(row="jab", ordinal=0, element=2, shield=-3, air=False)
        tags = M.badges(s.hitboxes[0])
        assert "electric" in tags and "ground only" in tags and "shield -3" in tags
        s.edit_hitbox(row="jab", ordinal=0, air=True, ground=False)
        assert "air only" in M.badges(s.hitboxes[0])
        # every retail element has a badge name, including the two ReDead/Lipstick ids the viz lacked
        assert [M.ELEMENT_NAMES[i] for i in (6, 7, 15, 16)] == ["nap", "sleep", "lipstick", "redead grab"]
    finally:
        fake.stop()


class _Session:
    edit_fields = api.EDITABLE


@pytest.fixture
def editor(monkeypatch):
    monkeypatch.setattr(props, "_session", lambda: _Session())
    return props._source_editor_values


def test_editor_reads_the_launcher_names(editor):
    values = editor({"bone": "HAND_R", "element": 5, "shield_damage": -3, "hit_ground": False, "hit_air": True, "slot": 1})
    assert values["element"] == "5" and values["shield"] == -3 and values["ground"] is False and values["air"] is True
    assert values["slot"] == 1


def test_editor_defaults_when_an_old_launcher_omits_the_fields(editor):
    values = editor({"bone": "HAND_R"})
    assert values["element"] == "0" and values["shield"] == 0 and values["ground"] is True and values["air"] is True


def test_slot_four_is_clamped_in_the_editor_so_it_is_never_sent(editor):
    assert editor({"bone": "A", "slot": 4})["slot"] == 3


def test_element_items_name_the_17_retail_ids():
    labels = [label for _, label, _ in props.ELEMENT_ITEMS]
    assert len(labels) == 32 and [i for i, _, _ in props.ELEMENT_ITEMS][:3] == ["0", "1", "2"]
    assert "ReDead" in labels[16] and "Lipstick" in labels[15] and "unused" in labels[17]


def test_changed_fields_convert_the_element_enum_to_a_number(monkeypatch):
    class Settings:
        edit_baseline = '{"element": "0", "shield": 0}'
        edit_element = "13"; edit_shield = 0
    class Sess:
        edit_fields = ("element", "shield")
    monkeypatch.setattr(props, "_session", lambda: Sess())
    assert props.changed_hitbox_fields(Settings()) == {"element": 13}
