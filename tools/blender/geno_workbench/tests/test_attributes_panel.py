"""Attribute panel registration and range UI without a Blender process."""
import types

import api
import panels_attributes as panel
from attributes import AttributeDraft


class Layout:
    def __init__(self, calls=None):
        self.calls = [] if calls is None else calls
        self.enabled = True
        self.alert = False
    def row(self, **kwargs):
        return Layout(self.calls)
    column = row
    box = row
    def label(self, **kwargs):
        self.calls.append(("label", kwargs, self.alert))
    def prop(self, owner, field, **kwargs):
        self.calls.append(("prop", field, kwargs, self.alert))
    def operator(self, name, **kwargs):
        self.calls.append(("operator", name, kwargs))
        return types.SimpleNamespace()


def test_draw_shows_range_changed_highlight_and_existing_rebuild():
    rows = [{"name": "jumps.max", "value": 3, "type": "integer", "group": "jump",
             "range": {"minimum": 1, "maximum": 250}, "description": "Total jumps", "unit": "count"}]
    draft = AttributeDraft(rows)
    draft.set("jumps.max", 4)
    item = types.SimpleNamespace(name="jumps.max", integer=True, int_value=4, float_value=0.0)
    settings = types.SimpleNamespace(filter="", items=[item])
    sess = types.SimpleNamespace(connected=True, can_rebuild=True, stale=False, last_error="", status="")
    layout = Layout()
    panel.draw_attributes(layout, settings, draft, sess)
    assert any(c[0] == "label" and "1" in c[1].get("text", "") and "250" in c[1].get("text", "") for c in layout.calls)
    assert any(c[0] == "prop" and c[1] == "int_value" and c[3] for c in layout.calls)
    assert any(c[0] == "operator" and c[1] == "geno_wb.apply_attributes" for c in layout.calls)
    assert any(c[0] == "operator" and c[1] == "geno_wb.rebuild_reload" for c in layout.calls)


def test_registration_is_lazy_and_cleanup_releases_scene_property(monkeypatch):
    import sys
    registry = []
    class Scene:
        pass
    def register_class(cls):
        registry.append(cls)
    def unregister_class(cls):
        registry.remove(cls)
    prop = lambda **kwargs: kwargs
    fake_bpy = types.SimpleNamespace(
        types=types.SimpleNamespace(PropertyGroup=object, Operator=object, Panel=object, Scene=Scene),
        props=types.SimpleNamespace(StringProperty=prop, BoolProperty=prop, IntProperty=prop,
                                   FloatProperty=prop, CollectionProperty=prop, PointerProperty=prop),
        utils=types.SimpleNamespace(register_class=register_class, unregister_class=unregister_class),
        data=types.SimpleNamespace(scenes=[]),
    )
    monkeypatch.setitem(sys.modules, "bpy", fake_bpy)
    monkeypatch.setattr(api, "_session", api.WbSession(lambda: None))
    callback = lambda value: None
    api.session().on_change = callback
    panel.register()
    try:
        assert hasattr(Scene, "geno_wb_attributes")
        assert any(getattr(cls, "bl_idname", "") == "GENO_WB_PT_attributes" for cls in registry)
        assert api.session().on_change is not callback
        panel.register()  # no duplicate classes or callback wrappers
        assert len(registry) == 5
    finally:
        panel.unregister()
    assert registry == [] and not hasattr(Scene, "geno_wb_attributes")
    assert api.session().on_change is callback


def test_filter_reveals_matches_in_a_collapsed_group():
    rows = [{"name": "jumps.max", "value": 3, "type": "integer", "group": "jump",
             "range": {"minimum": 1, "maximum": 250}, "description": "Total jumps", "unit": "count"}]
    draft = AttributeDraft(rows)
    item = types.SimpleNamespace(name="jumps.max", integer=True, int_value=3)
    settings = types.SimpleNamespace(filter="JuMps", items=[item], show_jump=False)
    sess = types.SimpleNamespace(connected=True, can_rebuild=True, stale=False, last_error="", status="")
    layout = Layout()
    panel.draw_attributes(layout, settings, draft, sess)
    assert any(c[0] == "prop" and c[1] == "int_value" for c in layout.calls)
