"""Fetch external CSProject + portable Windows Blender 3.5.1 into _build/tools-ext.

No repository assets are vendored. The cache is reused without changing its
revision; --revision can pin a first fetch, and --scene resolves ambiguity.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.csp.project import workspace_root, generated_path, confined_path

REPOSITORY = 'https://github.com/AeonSSB/Melee-CSProject.git'
BLENDER_VERSION = '3.5.1'
BLENDER_ARCHIVE = 'blender-3.5.1-windows-x64.zip'
BLENDER_BASE = 'https://download.blender.org/release/Blender3.5/'


def choose_scene(paths, character='captain', requested=None):
    paths = list(paths)
    if requested:
        if requested not in paths or not requested.lower().endswith('.blend') or '..' in PurePosixPath(requested).parts:
            raise ValueError('--scene must name a tracked local-template .blend path')
        return requested
    aliases = {'captain': ('falcon',), 'captainfalcon': ('falcon',)}
    words = aliases.get(re.sub(r'[^a-z0-9]', '', character.lower()), (character.lower(),))
    candidates = [p for p in paths if p.lower().endswith('.blend') and any(w in p.lower() for w in words)]
    preferred = [p for p in candidates if 'csproject' in re.sub(r'[^a-z0-9]', '', p.lower())]
    candidates = preferred or candidates
    if len(candidates) != 1:
        raise ValueError('Choose --scene from character .blend paths: ' + ', '.join(candidates))
    return candidates[0]


def guard_tree(path, boundary):
    """Preflight existing mutable trees before git/copy/extraction can write."""
    path = confined_path(path, boundary, allow_boundary=True)
    if not path.exists():
        return path
    pending, visited = [path], set()
    while pending:
        directory = pending.pop()
        if directory in visited:
            continue
        visited.add(directory)
        for child in directory.iterdir():
            resolved = confined_path(child, boundary, allow_boundary=True)
            if resolved.is_dir():
                pending.append(resolved)
    return path


def safe_extract(archive, target, *, boundary=None):
    """Preflight every zip member, including Windows paths and symlinks."""
    boundary = Path(boundary) if boundary is not None else Path(target).absolute()
    target = guard_tree(target, boundary)
    with zipfile.ZipFile(archive) as z:
        members = []
        for info in z.infolist():
            name = info.filename.replace('\\', '/')
            path = PurePosixPath(name)
            destination = (target / name).resolve()
            mode = (info.external_attr >> 16) & 0o170000
            if path.is_absolute() or '..' in path.parts or ':' in name or mode == 0o120000 or not destination.is_relative_to(target):
                raise ValueError('Unsafe archive path: ' + info.filename)
            members.append((info, destination))
        for info, destination in members:
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as source, destination.open('wb') as output:
                    shutil.copyfileobj(source, output)


def validate_tools(manifest, root):
    if manifest.get('blender_version') != BLENDER_VERSION:
        raise ValueError('Cache must contain Blender 3.5.1')
    base = generated_path(Path(root) / '_build/tools-ext', root)
    for key in ('blender', 'template', 'scripts'):
        path = confined_path(manifest.get(key, ''), base)
        if not path.exists():
            raise ValueError('Missing/out-of-cache ' + key + ': ' + str(path))
    addons = guard_tree(Path(manifest['scripts']) / 'addons', base)
    for name in ('loom', 'render_button'):
        if not (addons / name / '__init__.py').is_file() and not (addons / (name + '.py')).is_file():
            raise ValueError('Missing external add-on: ' + name)
    return manifest


def load_tools(root=None):
    root = Path(root or workspace_root())
    base = generated_path(root / '_build/tools-ext', root)
    path = confined_path(base / 'csp/tools.json', base)
    return validate_tools(json.loads(path.read_text(encoding='utf-8')), root)


def run_git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def download(url, destination, *, boundary=None):
    destination = confined_path(destination, boundary or Path(destination).absolute().parent)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.csp-download-', suffix='.part',
                                         dir=destination.parent, delete=False) as output:
            temporary = Path(output.name)
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'gd-melee-csp-fetch/1.0'}), timeout=60) as response:
                shutil.copyfileobj(response, output)
        os.replace(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def install_addons(resources, cache):
    cache = Path(cache).resolve()
    guard_tree(cache, cache)
    addons = confined_path(cache / 'scripts/addons', cache)
    addons.mkdir(parents=True, exist_ok=True)
    for module in ('loom', 'render_button'):
        if (addons / module / '__init__.py').is_file() or (addons / (module + '.py')).is_file():
            continue
        candidates = list(resources.rglob(module + '.py')) + list(resources.rglob(module + '/__init__.py'))
        # Resources may store the add-ons as zip archives. Extract only archives
        # containing the named module; the checkout itself stays untouched.
        for archive in resources.rglob('*.zip'):
            with zipfile.ZipFile(archive) as z:
                names = [n.replace('\\', '/') for n in z.namelist()]
            if any(n.lower().endswith('/' + module + '/__init__.py') or n.lower() == module + '/__init__.py'
                   or n.lower().endswith('/' + module + '.py') or n.lower() == module + '.py' for n in names):
                extracted = confined_path(cache / 'addon-unpacked' / archive.stem, cache)
                safe_extract(archive, extracted, boundary=cache)
                candidates += list(extracted.rglob(module + '.py')) + list(extracted.rglob(module + '/__init__.py'))
        candidates = sorted(set(candidates))
        if len(candidates) != 1:
            raise ValueError('Resources add-on layout needs verification for ' + module + ': ' + repr(candidates))
        candidate = candidates[0]
        if candidate.name == '__init__.py':
            destination = confined_path(addons / module, cache)
            if destination.exists():
                raise ValueError('Remove incomplete cached add-on directory: ' + str(destination))
            shutil.copytree(candidate.parent, destination)
        else:
            shutil.copy2(candidate, confined_path(addons / (module + '.py'), cache))
    return addons.parent


def fetch(root, character='captain', scene=None, revision=None):
    root = Path(root).resolve()
    base = generated_path(root / '_build/tools-ext', root)
    cache = confined_path(base / 'csp', base)
    guard_tree(cache, cache)
    cache.mkdir(parents=True, exist_ok=True)
    manifest_file = confined_path(cache / 'tools.json', cache)
    if manifest_file.is_file():
        manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
        if manifest.get('character') == character and (scene is None or manifest.get('scene') == scene) and (revision is None or manifest.get('revision', '').startswith(revision)):
            try:
                return validate_tools(manifest, root)
            except ValueError:
                pass
    repo = confined_path(cache / 'CSProject', cache)
    if not (repo / '.git').is_dir():
        subprocess.run(['git', 'clone', '--depth', '1', '--filter=blob:none', '--sparse', REPOSITORY, str(repo)], check=True)
    if revision:
        if not re.fullmatch(r'[0-9a-fA-F]{7,40}', revision):
            raise ValueError('--revision must be a commit hash')
        run_git(repo, 'fetch', '--depth', '1', 'origin', revision)
        run_git(repo, 'checkout', '--detach', revision)
    paths = run_git(repo, 'ls-tree', '-r', '--name-only', 'HEAD').splitlines()
    chosen = choose_scene(paths, character, scene)
    parent = str(PurePosixPath(chosen).parent)
    # Non-cone mode avoids checking out every character when a scene is at root.
    pattern = '/' + (parent + '/' if parent != '.' else chosen)
    run_git(repo, 'sparse-checkout', 'set', '--no-cone', '/Resources/', pattern)
    guard_tree(repo, cache)
    template = confined_path(repo / chosen, repo)
    with template.open('rb') as stream:
        pointer = stream.read(128).startswith(b'version https://git-lfs.github.com/spec/')
    if pointer:
        run_git(repo, 'lfs', 'pull', '--include', chosen)
    if not template.is_file():
        raise ValueError('Sparse checkout has no template: ' + chosen)
    guard_tree(cache, cache)
    scripts = install_addons(confined_path(repo / 'Resources', cache), cache)
    blender = confined_path(cache / 'blender/blender-3.5.1-windows-x64/blender.exe', cache)
    if not blender.is_file():
        archive = confined_path(cache / BLENDER_ARCHIVE, cache)
        checksum_file = confined_path(cache / 'blender-3.5.1.sha256', cache)
        if not checksum_file.is_file():
            download(BLENDER_BASE + checksum_file.name, checksum_file, boundary=cache)
        hashes = {}
        for line in checksum_file.read_text(encoding='utf-8').splitlines():
            parts = line.split()
            if len(parts) == 2:
                hashes[parts[1].lstrip('*')] = parts[0].lower()
        if BLENDER_ARCHIVE not in hashes:
            raise ValueError('Official checksum file has no ' + BLENDER_ARCHIVE)
        if not archive.is_file():
            download(BLENDER_BASE + BLENDER_ARCHIVE, archive, boundary=cache)
        with archive.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else _digest(source)
        if digest != hashes[BLENDER_ARCHIVE]:
            raise ValueError('Blender archive checksum mismatch; remove the cache archive and retry')
        safe_extract(archive, cache / 'blender', boundary=cache)
    manifest = {
        'blender_version': BLENDER_VERSION, 'blender': str(blender.resolve()),
        'template': str(template.resolve()), 'scripts': str(scripts.resolve()),
        'character': character, 'scene': chosen, 'revision': run_git(repo, 'rev-parse', 'HEAD'),
    }
    validate_tools(manifest, root)
    temporary = confined_path(manifest_file.with_suffix('.tmp'), cache)
    temporary.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, manifest_file)
    return manifest


def _digest(source):
    digest = hashlib.sha256()
    for block in iter(lambda: source.read(1024 * 1024), b''):
        digest.update(block)
    return digest.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--character', default='captain')
    ap.add_argument('--scene', help='repo-relative .blend path, when automatic selection is ambiguous')
    ap.add_argument('--revision', help='pin a CSProject commit hash (cache is otherwise retained)')
    args = ap.parse_args(argv)
    try:
        result = fetch(workspace_root(), args.character, args.scene, args.revision)
    except (OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print('csp fetch: ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
