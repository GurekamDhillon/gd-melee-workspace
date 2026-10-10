"""Render button command is pure Python and uses a host interpreter, not bpy."""
from pathlib import Path

import pytest

from ui_command import render_command


def test_render_command_passes_project_pose_and_art_with_spaces(tmp_path):
    root = tmp_path / 'workspace with spaces'
    project = root / 'ports/goku-xv2'
    project.mkdir(parents=True)
    (project / 'workbench.json').write_text('{}')
    command = render_command(project, row='dair', frame=8, art='C:/local art/fighter.glb',
                             python='C:/Python/python.exe', root=root, costume='2')
    assert command[0] == 'C:/Python/python.exe'
    assert command[command.index('--project') + 1] == str(project.resolve())
    assert command[command.index('--pose') + 1] == 'dair:8'
    assert command[command.index('--art') + 1] == 'C:/local art/fighter.glb'
    assert command[command.index('--costume') + 1] == '2'
    assert command[1] == str(root / 'tools/csp/render_ui.py')


def test_missing_project_or_invalid_frame_fails(tmp_path):
    with pytest.raises(ValueError):
        render_command(tmp_path, python='python', root=tmp_path)
    (tmp_path / 'workbench.json').write_text('{}')
    with pytest.raises(ValueError):
        render_command(tmp_path, row='Wait', frame=-1, python='python', root=tmp_path)


def test_workbench_logs_reject_external_directory_link(tmp_path):
    from ui_command import generated_path
    outside = tmp_path / 'outside'
    outside.mkdir()
    (tmp_path / '_build/csp-render').mkdir(parents=True)
    try:
        (tmp_path / '_build/csp-render/workbench').symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('directory symlinks unavailable')
    with pytest.raises(ValueError, match='outside'):
        generated_path(tmp_path, 'workbench/render.log')
    assert generated_path(tmp_path, 'local/render.log').is_relative_to(tmp_path / '_build/csp-render')
