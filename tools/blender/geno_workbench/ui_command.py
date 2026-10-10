"""Pure command construction for the independent Render UI panel."""
import os
from pathlib import Path
import re
import shutil


def workspace_for(project):
    if os.environ.get('GW_ROOT'):
        return Path(os.environ['GW_ROOT']).expanduser().resolve()
    for parent in (Path(project), *Path(project).parents):
        if (parent / '.git').exists() and (parent / 'tools/csp/render_ui.py').is_file():
            return parent.resolve()
    raise ValueError('Set GW_ROOT to the workspace containing tools/csp/render_ui.py')


def generated_path(root, relative):
    """Reject directory links that move UI logs/cancellation outside _build."""
    base = Path(root).expanduser().resolve() / '_build/csp-render'
    value = (base / relative).resolve()
    if not value.is_relative_to(base) or value == base:
        raise ValueError('UI output resolves outside _build/csp-render: ' + str(value))
    return value


def render_command(project, *, row='Wait', frame=0, art='', python=None,
                   root=None, costume='all', pose=None, cancel_file=None, backend='csproject', blender=''):
    project = Path(project).expanduser().resolve()
    if not (project / 'workbench.json').is_file():
        raise ValueError('Choose the directory containing workbench.json')
    if not isinstance(frame, int) or frame < 0:
        raise ValueError('Frame must be a non-negative integer')
    if pose is None:
        pose = str(row or 'Wait') + ':' + str(frame)
    if not re.fullmatch(r'[^\r\n]+:(?:0|[1-9][0-9]*)', pose):
        raise ValueError('Pose must be row:frame')
    if costume != 'all' and not re.fullmatch(r'0|[1-9][0-9]*', costume):
        raise ValueError('Costume must be all or a zero-based integer')
    if backend not in ('csproject', 'own'):
        raise ValueError('Backend must be csproject or own')
    python = python or os.environ.get('GW_UI_PYTHON') or shutil.which('python') or shutil.which('python3')
    if not python or 'blender' in Path(python).stem.lower():
        raise ValueError('Set GW_UI_PYTHON to a host Python with Pillow; Blender is a separate renderer')
    root = Path(root).resolve() if root else workspace_for(project)
    command = [str(python), str(root / 'tools/csp/render_ui.py'), '--project', str(project),
               '--costume', costume, '--pose', pose]
    command += ['--backend', backend]
    if blender:
        command += ['--blender', str(blender)]
    if art:
        command += ['--art', str(art)]
    if cancel_file:
        command += ['--cancel-file', str(cancel_file)]
    return command
