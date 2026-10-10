from pathlib import Path
from types import SimpleNamespace
import operators_play as P


def settings(**changes):
    values = dict(project="project with spaces", move="jab1", row="jab1",
                  engine_exe="", mods_dir="", iso="")
    values.update(changes)
    return SimpleNamespace(**values)


def test_lab_passes_current_row_and_paths_as_separate_arguments():
    args = P.play_arguments(settings(), "lab")
    assert args[1:] == ["--project", "project with spaces", "--lab", "--clip", "jab1", "--json"]
    assert Path(args[0]).parts[-3:] == ("tools", "geno", "play.py")


def test_cpu_play_does_not_freeze_selected_row_in_clips():
    args = P.play_arguments(settings(), "vs")
    assert args[1:] == ["--project", "project with spaces", "--vs", "cpu", "--json"]


def test_empty_selection_opens_regular_lab_and_explicit_overrides_survive():
    args = P.play_arguments(settings(move="__GENO_WB_NO_ROW__", row="", iso="disc path",
                                    mods_dir="mods path", engine_exe="engine path"), "lab")
    assert "--clip" not in args
    assert args[args.index("--iso") + 1] == "disc path"
    assert args[args.index("--mods-dir") + 1] == "mods path"
    assert args[args.index("--engine-exe") + 1] == "engine path"


def test_rebuild_requires_the_dialog_choice():
    assert "--rebuild" not in P.play_arguments(settings(), "lab")
    assert "--rebuild" in P.play_arguments(settings(), "lab", rebuild=True)


def test_scene_settings_reads_the_actual_disc_property():
    scene = SimpleNamespace(project="//project", move="dair", row="dair",
                            engine_exe="//melee-pc.exe", mods_dir="//mods",
                            iso_path="//disc.iso")
    normalized = P._scene_settings(scene, lambda value: "/absolute/" + value[2:])
    args = P.play_arguments(normalized, "lab")
    assert args[args.index("--project") + 1] == "/absolute/project"
    assert args[args.index("--iso") + 1] == "/absolute/disc.iso"
    assert args[args.index("--engine-exe") + 1] == "/absolute/melee-pc.exe"
    assert args[args.index("--mods-dir") + 1] == "/absolute/mods"


def test_finished_launch_status_includes_the_run_log(monkeypatch):
    import io
    import json
    process = SimpleNamespace(poll=lambda: 0, returncode=0)
    output = io.BytesIO(json.dumps({"ok": True, "log_path": "run/unique/melee-pc.log"}).encode())
    scene = SimpleNamespace(status="")
    monkeypatch.setattr(P, "_JOBS", [(process, output, scene)])
    monkeypatch.setattr(P, "_TIMER", True)
    assert P._poll_jobs() is None
    assert "run/unique/melee-pc.log" in scene.status
    assert output.closed


def checkout(tmp_path, name):
    root = tmp_path / name
    (root / ".git").mkdir(parents=True)
    project = root / "ports/fighter"
    project.mkdir(parents=True)
    script = root / "tools/geno/play.py"
    script.parent.mkdir(parents=True)
    script.write_text("from pathlib import Path\n"
                      "def resolve_project(*args, **kwargs):\n"
                      "    return Path(__file__).resolve().parents[2]\n")
    return root, project


def test_copied_addon_uses_the_current_projects_checkout(tmp_path, monkeypatch):
    root, project = checkout(tmp_path, "author checkout")
    copied = tmp_path / "Blender/4.2/scripts/addons/geno_workbench/operators_play.py"
    monkeypatch.setattr(P, "__file__", str(copied))
    args = P.play_arguments(settings(project=str(project)), "lab")
    assert Path(args[0]) == root / "tools/geno/play.py"


def test_switching_checkout_uses_its_own_resolver(tmp_path, monkeypatch):
    first, project1 = checkout(tmp_path, "first")
    second, project2 = checkout(tmp_path, "second")
    current = settings(project=str(project1))
    monkeypatch.setattr(P, "_settings", lambda context: current)
    assert P._plan(None, "lab") == first
    current.project = str(project2)
    assert P._plan(None, "lab") == second


def test_external_project_can_use_explicit_workspace(tmp_path):
    root, _ = checkout(tmp_path, "workspace")
    external = tmp_path / "external fighter"
    external.mkdir()
    assert P._play_script(str(external), env={"GW_ROOT": str(root)}) == root / "tools/geno/play.py"


def test_nearest_worktree_without_helper_is_actionable(tmp_path):
    import pytest
    root, project = checkout(tmp_path, "missing helper")
    (root / "tools/geno/play.py").unlink()
    with pytest.raises(ValueError, match="play.py"):
        P._play_script(str(project), env={})
