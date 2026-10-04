"""Public pure-Python API; staged mission-folder publication."""
import copy
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import uuid
from .data import coordinates, lua, model_name, assign_chunk
from .validation import validate, safe_name
from .assets import used_assets
from .references import model_reference


def content_matches(path, content):
    if not path.is_file() or path.stat().st_size != len(content): return False
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): digest.update(block)
    return digest.digest() == hashlib.sha256(content).digest()


def atomic_write(path, content):
    if content_matches(path, content): return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('wb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def remove_generation(path, parent):
    """Verify the exact staging/backup target before recursive Windows deletion."""
    resolved = path.resolve()
    if resolved.parent != parent.resolve() or not path.name.startswith('.') or path.is_symlink():
        raise ValueError('Refusing to remove a generation outside the mission parent')
    shutil.rmtree(path)


def export_document(doc, mod_folder, name):
    errors = validate(doc)
    if not safe_name(name): errors.append('Mission name: use letters, numbers, underscores or hyphens')
    if errors: raise ValueError('\n'.join(errors))
    parent = Path(mod_folder).resolve() / 'missions'
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / name
    if target.is_symlink(): raise ValueError('Mission destination must not be a symlink')
    stage = Path(tempfile.mkdtemp(prefix='.' + name + '-', dir=parent))
    backup = parent / ('.' + name + '-old-' + uuid.uuid4().hex)
    def staged_file(path, content):
        previous = target / path.relative_to(stage)
        path.parent.mkdir(parents=True, exist_ok=True)
        if content_matches(previous, content):
            # Reuse the immutable file, preserving inode and modification time.
            # The old generation is removed only after the new link is published.
            try: os.link(previous, path)
            except OSError: shutil.copy2(previous, path)
        else:
            atomic_write(path, content)
    try:
        (stage / 'models').mkdir()
        for asset, content in used_assets(doc).items():
            if Path(asset).name != asset or '/' in asset or '\\' in asset:
                raise ValueError('Unsafe model filename')
            staged_file(stage / 'models' / asset, content)
        level = copy.deepcopy(doc['level'])
        pending = []
        chunks = doc.get('chunks', [])
        if chunks:
            level['parts'] = []
            level['chunks'] = []
            for chunk in sorted(chunks, key=lambda c: c['id']):
                parts = [p for p in doc['level']['parts'] if assign_chunk(p['x'], p['y'], chunks) == chunk['id']]
                relative = 'chunks/' + chunk['id']
                # Absolute game coordinates are retained across all chunk files.
                chunk_level = dict(version=2, units=level['units'], parts=parts)
                for key in ('size', 'exits'):
                    if key in chunk: chunk_level[key] = copy.deepcopy(chunk[key])
                if 'camera' in chunk:
                    chunk_level['camera'] = {k: chunk[k] for k in ('left', 'right', 'top', 'bottom')}
                    chunk_level['camera'].update(copy.deepcopy(chunk['camera']))
                model_reference(stage / relative / 'models', target / 'models')
                pending.append((stage / relative / 'level.lua', chunk_level))
                rect = {k: chunk[k] for k in ('left', 'right', 'top', 'bottom')}
                # Prefer authored checkpoints/start for rebirth. Fallback is a
                # floor origin plus 1m; otherwise the rectangle's centre.
                points = doc['mission'].get('checkpoints', []) + [doc['mission']['start']]
                spawn = next((dict(x=p['x'], y=p['y']) for p in points
                              if assign_chunk(p['x'], p['y'], [chunk]) is not None), None)
                if spawn is None:
                    from .constants import UNITS
                    floor = next((p for p in parts if 'floor' in p['part']), None)
                    if floor and assign_chunk(floor['x'], floor['y'] + UNITS, [chunk]):
                        spawn = dict(x=floor['x'], y=floor['y'] + UNITS)
                    else:
                        spawn = dict(x=(rect['left']+rect['right'])/2, y=(rect['bottom']+rect['top'])/2)
                entry = dict(id=chunk['id'], rect=rect, spawn=spawn)
                level['chunks'].append(entry)
        for path, value in pending: staged_file(path, ('return ' + lua(value) + '\n').encode('utf-8'))
        staged_file(stage / 'level.lua', ('return ' + lua(level) + '\n').encode('utf-8'))
        staged_file(stage / 'mission.lua', ('return ' + lua(doc['mission']) + '\n').encode('utf-8'))
        # Windows cannot atomically replace a nonempty directory. A completed
        # generation is published with two renames; the brief missing-folder
        # interval is preferable to exposing mismatched Lua files. Restore on error.
        if target.exists(): os.replace(target, backup)
        try: os.replace(stage, target)
        except OSError:
            if backup.exists(): os.replace(backup, target)
            raise
        if backup.exists(): remove_generation(backup, parent)
        return target
    finally:
        if stage.exists(): remove_generation(stage, parent)
