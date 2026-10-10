"""Turn workbench.json and a built package into a portable render job."""
import gzip
import json
import os
from pathlib import Path
import re

from .framing import resolve_role_bones
from .outputs import enumerate_costumes, select_costumes

ROOT = Path(__file__).resolve().parents[2]


def workspace_root():
    return Path(os.environ.get('GW_ROOT', ROOT)).expanduser().resolve()


def confined_path(path, boundary, *, allow_boundary=False):
    """Resolve existing directory links, then require the intended boundary.

    Keep the boundary lexical: resolving it could silently authorize an _build
    or cache junction that redirects writes outside the intended directory.
    """
    boundary = Path(boundary).expanduser().absolute()
    value = Path(path).expanduser().resolve()
    if not value.is_relative_to(boundary) or (value == boundary and not allow_boundary):
        raise ValueError('Path resolves outside output boundary ' + str(boundary) + ': ' + str(value))
    return value


def generated_path(path, root):
    build = Path(root).expanduser().resolve() / '_build'
    return confined_path(path, build)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def resolve_path(value, base):
    return (Path(base) / Path(value).expanduser()).resolve()


def blend_version(path):
    with Path(path).open('rb') as stream:
        header = stream.read(12)
    if header[:2] == b'\x1f\x8b':
        with gzip.open(path, 'rb') as stream:
            header = stream.read(12)
    if not header.startswith(b'BLENDER') or not header[9:12].isdigit():
        raise ValueError('Not a readable .blend header: ' + str(path))
    return int(header[9:12])


def compatible_art(path, fallback=None, any_version=False):
    """any_version: the own backend runs current Blender, which opens newer .blend files."""
    path = Path(path)
    if any_version and path.is_file() and path.suffix.lower() == '.blend':
        # Prefer what the 3.5 path would use (a GLB beside the blend carries the shipped,
        # smooth-shaded art); only a blend with no GLB is opened directly.
        try:
            return compatible_art(path, fallback)
        except ValueError:
            return path.resolve()
    if path.is_file() and path.suffix.lower() in ('.glb', '.gltf'):
        return path.resolve()
    if path.is_file() and path.suffix.lower() == '.blend':
        try:
            if blend_version(path) <= 305:
                return path.resolve()
        except ValueError:
            # Newer Blender compression can obscure the version header. A
            # separate GLB still provides a version-independent source.
            pass
    for candidate in (fallback, path.with_suffix('.glb')):
        if candidate and Path(candidate).is_file() and Path(candidate).suffix.lower() in ('.glb', '.gltf'):
            return Path(candidate).resolve()
    raise ValueError('Blender 3.5.1 needs compatible .blend art or a local GLB fallback: ' + str(path))


def compatible_retail_scene(path):
    scene = compatible_art(path)
    if scene.suffix.lower() != '.blend':
        raise ValueError('retail costume art must be a compatible CSProject .blend scene: ' + str(path))
    return scene


def resolve_pose(value, config, project, plan):
    if not isinstance(value, str) or ':' not in value:
        raise ValueError('Pose must be row:frame')
    row, frame = value.rsplit(':', 1)
    if not row or not re.fullmatch(r'0|[1-9][0-9]*', frame):
        raise ValueError('Pose needs a row and non-negative integer frame')
    clips = plan.get('row_clips', [])
    if row.isdecimal():
        index = int(row)
        if index >= len(clips) or not isinstance(clips[index], str):
            raise ValueError('Animation row is absent from plan: ' + row)
        action = clips[index]
    else:
        actions = {c for c in clips if isinstance(c, str)}
        bank = plan.get('bank', {}).get('clips', {})
        names = bank.keys() if isinstance(bank, dict) else (c.get('name') if isinstance(c, dict) else c for c in (bank or []))
        actions.update(c for c in names if isinstance(c, str))
        move = Path(project) / config.get('moves_dir', 'moves') / (row + '.json')
        if not move.resolve().is_relative_to(Path(project).resolve()):
            raise ValueError('Pose row cannot escape the project')
        if move.is_file():
            action = read_json(move).get('pick', {}).get('clip')
        else:
            action = row if row in actions else None
            if action is None and row == 'Wait' and 'Wait1' in actions:
                action = 'Wait1'  # retail idle is Wait1 (Wait2/3 are the rare variants)
        if not action or action not in actions:
            raise ValueError('No built animation clip for row: ' + row)
    return action, int(frame)


def load_project(project, *, root=None, package=None, fighter=None, art=None,
                 pose=None, costume='all', retail_scene=None, scene_config=None, emblem=None, backend='csproject'):
    root = Path(root or workspace_root()).resolve()
    project = Path(project).expanduser().resolve()
    if project.is_file():
        project = project.parent
    config = read_json(project / 'workbench.json')
    if config.get('schema') != 'workbench/1':
        raise ValueError('Expected workbench/1 project')
    ui = config.get('ui_render', {})
    if not isinstance(ui, dict):
        raise ValueError('ui_render must be an object')
    if package is None:
        plan_abs = config.get('plan_abs')
        if plan_abs:
            package = resolve_path(plan_abs, root).parent.parent
        else:
            package = resolve_path(config.get('plan', ''), project).parent.parent
    package = generated_path(package, root)
    doc = read_json(confined_path(package / 'geno.json', package))
    if doc.get('geno', 0) < 9:
        raise ValueError('Presentation requires geno >= 9')
    entries = doc.get('fighters', [])
    key = ui.get('fighter_key', config.get('mod_id'))
    matches = [i for i, e in enumerate(entries) if e.get('define', {}).get('key') == key]
    if len(matches) == 1:
        entry_index = matches[0]
    elif len(entries) == 1:
        entry_index = 0
    else:
        raise ValueError('Choose ui_render.fighter_key for a package with multiple fighters')
    entry = entries[entry_index]
    plan_name = entry.get('fighter', {}).get('plan', 'plan.json')
    files = confined_path(package / 'files', package)
    plan_path = confined_path(files / plan_name, files)
    plan = read_json(plan_path)
    source_file = fighter or ui.get('fighter')
    if not source_file:
        rebuild = config.get('rebuild', [])
        if '--fighter' in rebuild:
            i = rebuild.index('--fighter')
            if i + 1 < len(rebuild):
                source_file = rebuild[i + 1]
    source_path = resolve_path(source_file, root) if source_file else None
    source = read_json(source_path) if source_path else {}
    source_dir = source_path.parent if source_path else project
    source_glb = source.get('art', {}).get('glb')
    fallback = resolve_path(source_glb, source_dir) if source_glb else None
    art_value = art or ui.get('art') or config.get('art_blend') or config.get('art_glb') or fallback
    retail = retail_scene is not None
    if retail:
        define = entry.get('define', {})
        donor = define.get('template') if define.get('base') == 'none' else define.get('base')
        if not donor or donor == 'none':
            raise ValueError('Retail scene rendering needs an explicit retail base or define.template')
        retail_scene = compatible_retail_scene(retail_scene)
        art_path = None
    else:
        if not art_value:
            raise ValueError('Project needs art_blend/art_glb or --art')
        art_path = compatible_art(resolve_path(art_value, root), fallback, backend == 'own')
    costumes = enumerate_costumes(entry, source, source_dir, ui.get('costumes'))
    selected = select_costumes(costumes, costume)
    existing = entry.get('presentation', {})
    def have_zero(field):
        value = existing.get(field)
        if isinstance(value, list):
            value = value[0] if value else None
        return isinstance(value, str) and confined_path(files / value, files).is_file()
    fallback_zero_fields = []
    if selected[0]['index'] != 0:
        fallback_zero_fields = [f for f in ('icon', 'portrait', 'stock', 'results') if not have_zero(f)]
        if fallback_zero_fields:
            selected.insert(0, costumes[0])
    for c in selected:
        if c.get('art'):
            c['art'] = str(compatible_retail_scene(c['art']) if retail else compatible_art(c['art'], any_version=backend == 'own'))
        if c.get('texture') and not Path(c['texture']).is_file():
            raise ValueError('Missing costume texture: ' + c['texture'])
        if c['index'] > 0 and not any(c.get(k) for k in ('art', 'texture', 'material_colors', 'objects', 'collections')):
            raise ValueError('No distinct art/recolor inputs for costume ' + str(c['index']) + '; set ui_render.costumes')
    action, frame = resolve_pose(pose or ui.get('pose', 'Wait:0'), config, project, plan)
    settings = ui.get('scene_config', {})
    if isinstance(settings, str):
        settings = read_json(resolve_path(settings, project))
    if scene_config:
        settings = read_json(scene_config)
    if not isinstance(settings, dict):
        raise ValueError('Scene config must be an object')
    emblem_value = emblem or ui.get('emblem')
    emblem_path = str(resolve_path(emblem_value, project)) if emblem_value else None
    if emblem_path and not Path(emblem_path).is_file():
        raise ValueError('Missing authored emblem: ' + emblem_path)
    offset = ui.get('frame_offset', 0)
    if not isinstance(offset, int):
        raise ValueError('frame_offset must be an integer')
    return {
        'root': str(root), 'project': str(project), 'package': str(package),
        'entry_index': entry_index, 'key': entry.get('define', {}).get('key', 'fighter'),
        'count': len(costumes), 'costumes': selected, 'fallback_zero_fields': fallback_zero_fields, 'art': str(art_path) if art_path else None,
        'retail': retail, 'retail_scene': str(Path(retail_scene).resolve()) if retail else None,
        'pose_requested': pose is not None or 'pose' in ui,
        'action': action, 'frame': frame, 'frame_offset': offset,
        'scene_config': settings, 'fields': ui.get('fields', {}),
        'effects': ui.get('effects', {}), 'emblem': emblem_path,
        # role -> armature bone, from the built plan's role table (+ workbench bone aliases).
        'roles': resolve_role_bones(plan, (config.get('art') or {}).get('bone_aliases'), ui.get('roles')),
        'own_render': ui.get('own_render', {}),
    }
