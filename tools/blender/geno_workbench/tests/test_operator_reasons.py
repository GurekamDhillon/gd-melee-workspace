"""Exercise real operator polls with lightweight bpy boundaries; no UI or server."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parents[1]


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def operators(monkeypatch):
    class Operator:
        reason = ""

        @classmethod
        def poll_message_set(cls, reason):
            cls.reason = reason

        def report(self, level, message):
            self.reports.append((level, message))

    bpy = ModuleType("bpy")
    bpy.types = SimpleNamespace(Operator=Operator, PropertyGroup=type("PropertyGroup", (), {}))
    bpy.props = ModuleType("bpy.props")
    for name in ("EnumProperty", "FloatProperty", "IntProperty", "StringProperty", "PointerProperty"):
        setattr(bpy.props, name, lambda **kwargs: None)
    bpy.path = SimpleNamespace(abspath=lambda path: path)
    monkeypatch.setitem(sys.modules, "bpy", bpy)
    monkeypatch.setitem(sys.modules, "bpy.props", bpy.props)
    props = load_file("reason_test_props", HERE / "props.py")
    props.sync_from_session = lambda *args: None
    monkeypatch.setitem(sys.modules, "props", props)
    state = SimpleNamespace(connected=True, info={"frame": 1}, has_roles=True, can_rebuild=True,
                            hitboxes=[{}], problems=[{}], last_error="", status="",
                            art_blend="fighter.blend", art_glb="", source_row="jab1")

    def set_status(message):
        state.status = message
        return True

    state.set_status = set_status
    monkeypatch.setitem(sys.modules, "api", SimpleNamespace(session=lambda: state))
    monkeypatch.setitem(sys.modules, "client", SimpleNamespace(WbError=RuntimeError))
    monkeypatch.setitem(sys.modules, "launch", SimpleNamespace(start_serve=lambda *a, **k: pytest.fail("must not launch a second server")))
    arm = SimpleNamespace(name="ExportRig")
    monkeypatch.setitem(sys.modules, "pose", SimpleNamespace(calibration_for=lambda obj: ({}, {}) if obj else None))
    monkeypatch.setitem(sys.modules, "rig", SimpleNamespace(find_armature=lambda name: arm))
    for name in ("nla", "travel", "wbspace"):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    nla = load_file("reason_test_nla", HERE / "operators_nla.py")
    monkeypatch.setitem(sys.modules, "operators_nla", nla)
    general = load_file("reason_test_operators", HERE / "operators.py")
    fighter = load_file("reason_test_fighter", HERE / "operators_fighter.py")
    settings = SimpleNamespace(hitbox_index=0, problem_index=0, port=51726, project="", blender_art="")
    context = SimpleNamespace(scene=SimpleNamespace(geno_wb=settings, geno_wb_fighter=SimpleNamespace(armature="")),
                              object=arm, mode="OBJECT")
    arm.type = "ARMATURE"
    return SimpleNamespace(general=general, fighter=fighter, nla=nla, state=state, context=context, props=props)


@pytest.mark.parametrize("name", ["engine_restart", "refresh_rows", "load_row", "step", "play", "run_checks", "goto_problem", "suggest_bone", "edit_hitbox", "rebuild_reload"])
def test_disconnected_operator_explains_connection(operators, name):
    operators.state.connected = False
    cls = getattr(operators.general, "GENO_WB_OT_" + name)
    assert cls.poll(operators.context) is False
    assert "connect" in cls.reason.lower()


@pytest.mark.parametrize("name", ["step", "play"])
def test_frame_dependent_operator_explains_missing_frame(operators, name):
    operators.state.info = None
    cls = getattr(operators.general, "GENO_WB_OT_" + name)
    assert cls.poll(operators.context) is False
    assert "frame" in cls.reason.lower()


@pytest.mark.parametrize("name", ["run_checks", "suggest_bone"])
def test_role_dependent_operator_explains_missing_map(operators, name):
    operators.state.has_roles = False
    cls = getattr(operators.general, "GENO_WB_OT_" + name)
    assert cls.poll(operators.context) is False
    assert "role map" in cls.reason.lower()


def test_rebuild_operator_explains_missing_build(operators):
    operators.state.can_rebuild = False
    cls = operators.general.GENO_WB_OT_rebuild_reload
    assert cls.poll(operators.context) is False
    assert "workbench.json" in cls.reason


def test_suggest_operator_explains_missing_selection(operators):
    operators.context.scene.geno_wb.hitbox_index = -1
    cls = operators.general.GENO_WB_OT_suggest_bone
    assert cls.poll(operators.context) is False
    assert "hitbox" in cls.reason.lower()


def test_start_server_explains_connected_session(operators):
    cls = operators.general.GENO_WB_OT_start_server
    assert cls.poll(operators.context) is False
    assert "disconnect" in cls.reason.lower()


def test_start_server_explains_owned_server(operators):
    operators.state.connected = False
    operators.general._server_process = SimpleNamespace(poll=lambda: None)
    cls = operators.general.GENO_WB_OT_start_server
    assert cls.poll(operators.context) is False
    assert "running server" in cls.reason.lower()


def test_server_reuse_reports_the_port_without_acquiring_ownership(operators, monkeypatch):
    operators.state.connected = False
    monkeypatch.setattr(operators.general, "server_answers", lambda port: True)
    op = operators.general.GENO_WB_OT_start_server()
    op.reports = []
    assert op.execute(operators.context) == {"FINISHED"}
    assert any(level == {"INFO"} and "51726" in message and "reus" in message.lower()
               for level, message in op.reports)
    assert operators.general._server_process is None
    assert "51726" in operators.state.status


@pytest.mark.parametrize("name", ["import_clip", "layout_recipe", "save_strips", "bake_export"])
def test_splice_poll_explains_missing_armature_and_mode(operators, name):
    cls = getattr(operators.nla, "GENO_WB_OT_" + name)
    operators.context.object = None
    assert cls.poll(operators.context) is False
    assert "armature" in cls.reason.lower()
    operators.context.object = SimpleNamespace(type="ARMATURE")
    operators.context.mode = "EDIT_ARMATURE"
    assert cls.poll(operators.context) is False
    assert "Object Mode" in cls.reason


@pytest.mark.parametrize("name", ["load_fighter", "calibrate"])
def test_fighter_poll_explains_connection(operators, name):
    operators.state.connected = False
    cls = getattr(operators.fighter, "GENO_WB_OT_" + name)
    assert cls.poll(operators.context) is False
    assert "connect" in cls.reason.lower()


def test_fighter_load_poll_explains_missing_art(operators):
    operators.state.art_blend = ""
    cls = operators.fighter.GENO_WB_OT_load_fighter
    assert cls.poll(operators.context) is False
    assert "art" in cls.reason.lower()


def test_calibrate_poll_explains_missing_armature(operators, monkeypatch):
    monkeypatch.setattr(operators.fighter, "active_armature", lambda *args, **kwargs: None)
    cls = operators.fighter.GENO_WB_OT_calibrate
    assert cls.poll(operators.context) is False
    assert "armature" in cls.reason.lower()


def test_verify_poll_explains_calibration_then_frame(operators, monkeypatch):
    cls = operators.fighter.GENO_WB_OT_verify_pose
    monkeypatch.setattr(operators.fighter.pose, "calibration_for", lambda arm: None)
    assert cls.poll(operators.context) is False
    assert "calibrat" in cls.reason.lower()
    monkeypatch.setattr(operators.fighter.pose, "calibration_for", lambda arm: ({}, {}))
    operators.state.info = None
    assert cls.poll(operators.context) is False
    assert "frame" in cls.reason.lower()


def test_ready_operator_polls_stay_enabled(operators):
    for cls in operators.general.CLASSES:
        if cls is operators.general.GENO_WB_OT_start_server or not hasattr(cls, "poll"):
            continue
        assert cls.poll(operators.context) is True, cls.__name__
    for cls in operators.fighter._CLASSES:
        assert cls.poll(operators.context) is True, cls.__name__


@pytest.mark.parametrize("index", [-1, 1])
def test_goto_problem_explains_missing_selection(operators, index):
    operators.context.scene.geno_wb.problem_index = index
    cls = operators.general.GENO_WB_OT_goto_problem
    assert cls.poll(operators.context) is False
    assert "problem" in cls.reason.lower()


def test_start_server_uses_config_root_before_project_root(operators, tmp_path, monkeypatch):
    import json

    shared = tmp_path / "shared"
    project_root = tmp_path / "project-root"
    project = project_root / "authoring/fighter"
    project.mkdir(parents=True)
    (project_root / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    for directory, label in ((shared, "shared"), (project_root, "wrong")):
        cache = directory / "_build/tools.json"
        cache.parent.mkdir(parents=True)
        cache.write_text(json.dumps({"schema": 1, "paths": {
            "GW_LAUNCHER": label + "/launcher.exe",
            "GW_ENGINE_EXE": label + "/engine.exe",
            "GW_ISO_VANILLA": label + "/vanilla.iso",
            "GW_QT_BIN": label + "/qt/bin",
        }}), encoding="utf-8")
    monkeypatch.setattr(operators.general, "launch", load_file("reason_test_real_launch", HERE / "launch.py"))
    monkeypatch.setenv("GW_ROOT", str(shared))
    for key in ("GW_LAUNCHER", "GW_ENGINE_EXE", "GW_ISO_VANILLA", "GW_QT_BIN", "GW_TOOLS_CONFIG"):
        monkeypatch.delenv(key, raising=False)
    operators.state.connected = False
    settings = operators.context.scene.geno_wb
    settings.project = str(project)
    for key in ("launcher_exe", "engine_exe", "mods_dir", "iso_path"):
        setattr(settings, key, "")
    monkeypatch.setattr(operators.general, "server_answers", lambda port: False)
    started = []
    process = SimpleNamespace(poll=lambda: None)

    def start(argv, **kwargs):
        started.append((argv, kwargs["env"]))
        return process, 51726

    monkeypatch.setattr(operators.general.launch, "start_serve", start)
    op = operators.general.GENO_WB_OT_start_server()
    op.reports = []
    assert op.execute(operators.context) == {"FINISHED"}
    argv, env = started[0]
    assert argv[0] == str(shared / "shared/launcher.exe")
    assert argv[argv.index("--engine-exe") + 1] == str(shared / "shared/engine.exe")
    assert env["MELEE_ISO"] == str(shared / "shared/vanilla.iso")
    assert env["PATH"].startswith(str(shared / "shared/qt/bin"))
    assert env["GW_ROOT"] == str(shared)


@pytest.mark.parametrize("panel", ["connect", "timeline", "problems"])
@pytest.mark.parametrize("connected,frame", [(False, 0), (True, 0), (True, 600)])
def test_panel_buttons_leave_disabling_to_operator_reasons(operators, monkeypatch, panel, connected, frame):
    class Layout:
        def __init__(self, parent=None):
            self.parent = parent
            self.enabled = True

        def row(self, **kwargs):
            return Layout(self)

        column = row
        box = row

        def operator(self, name, **kwargs):
            current = self
            while current is not None:
                assert current.enabled, name + " is disabled outside its poll"
                current = current.parent
            return SimpleNamespace()

        def prop(self, *args, **kwargs):
            pass

        label = prop
        template_list = prop

    operators.state.connected = connected
    operators.state.info = {"frame": frame} if connected else None
    operators.state.row_frames = lambda: 0
    operators.state.pump_cache = lambda: (0, 0, False)
    settings = operators.context.scene.geno_wb
    settings.frame = frame
    settings.playing = False
    settings.problem_index = -1
    settings.status = ""
    bpy = sys.modules["bpy"]
    bpy.types.Panel = type("Panel", (), {})
    bpy.types.UIList = type("UIList", (), {})
    monkeypatch.setitem(sys.modules, "operators", operators.general)
    panels = load_file("reason_test_panels", HERE / "panels.py")
    instance = getattr(panels, "GENO_WB_PT_" + panel)()
    instance.layout = Layout()
    instance.draw(operators.context)
