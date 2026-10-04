#!/usr/bin/env python3
"""Scan game TUs by dependency content; retain a separate legacy timestamp scan.

--compare validates the preserved Python timestamp scan against the shell scan
on the same real tree. Hash mode is deliberately more selective after depfiles
exist, so its list is not expected to equal the old timestamp list.
"""

import argparse
import difflib
import glob
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys


PORT = Path(__file__).resolve().parent
ROOT = PORT.parent.parent


def default_bash():
    if os.name == 'nt':
        git_bash = Path(os.environ.get('ProgramFiles', 'C:/Program Files'))/'Git/bin/bash.exe'
        if git_bash.is_file():
            return str(git_bash)
    return shutil.which('bash') or 'bash'


class FileCache:
    """Share input reads within one scan or post-compile recording pass.

    Every new pass reads current bytes. Size and mtime cannot prove unchanged
    content: checkout/copy tools may preserve both across a source edit.
    """

    def __init__(self, path):
        self.path = path
        self.values = {}
        self.identities = {}
        self.paths = {}
        self.resolved = {}

    def cached(self, kind, path, read):
        token = (kind, path)
        if token not in self.values:
            self.values[token] = read()
        return self.values[token]

    def digest(self, path):
        return bytes.fromhex(self.cached("sha", path, lambda: hash_file(path).hex()))

    def dependencies(self, path, cwd):
        # Include the checkout so callers can share a pass across lanes.
        return self.cached("deps:" + str(cwd), path,
                           lambda: [str(p) for p in dependencies(path, cwd, self.resolved)])

    def intern_path(self, name):
        if name not in self.paths:
            self.paths[name] = Path(name)
        return self.paths[name]

    def key(self, path):
        return self.cached("key", path, lambda: path.read_text(encoding="ascii").strip())

    def save(self):
        # Retain the caller API; persisted content caches are intentionally unused.
        pass


def hash_file(path):
    content = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            content.update(chunk)
    return content.digest()


def newest_header(files: Path, melee: Path):
    """Match find -name '*.h' -newer files.txt across the three old roots."""
    manifest_time = files.stat().st_mtime_ns
    newest = None
    for root in (melee / "src", melee / "include", melee / "pc" / "geno"):
        for base, dirs, names in os.walk(root, followlinks=False):
            for name in dirs + names:
                if not name.endswith(".h"):
                    continue
                try:
                    modified = (Path(base) / name).stat().st_mtime_ns
                except OSError:
                    continue
                if modified > manifest_time and (newest is None or modified > newest):
                    newest = modified
    return newest


def scan(files: Path, melee: Path, out: Path):
    """Return exactly the old scan's ordered list of stale, existing TUs."""
    if not files.is_file():
        return []
    header_time = newest_header(files, melee)
    # The old `tr -d '\r'` removes every CR byte, not just CRLF line endings.
    manifest = files.read_bytes().replace(b"\r", b"").decode("utf-8")
    stale = []
    for file_name in manifest.split("\n"):
        if not file_name:
            continue
        source = melee / file_name
        if not source.exists():
            continue
        obj = out / (file_name.replace("/", "_") + ".obj")
        if not obj.is_file():
            stale.append(file_name)
            continue
        obj_time = obj.stat().st_mtime_ns
        if source.stat().st_mtime_ns > obj_time:
            stale.append(file_name)
            continue
        # Bash expands "${src%.c}"_*.inc even for unusual manifest entries.
        stem = str(source)[:-2] if str(source).endswith(".c") else str(source)
        if any(Path(part).exists() and Path(part).stat().st_mtime_ns > obj_time
               for part in glob.glob(stem + "_*.inc")):
            stale.append(file_name)
            continue
        if header_time is not None and header_time > obj_time:
            stale.append(file_name)
    return stale


def dependencies(depfile: Path, cwd: Path, resolved=None):
    """Read clang's make depfile, including escaped spaces and continuations."""
    data = depfile.read_text(encoding="utf-8")
    data = data.replace("\\\r\n", "").replace("\\\n", "")
    # Compiles use -MT object, so the first colon belongs to the rule target.
    if ":" not in data:
        raise ValueError(f"malformed depfile: {depfile}")
    data = data.split(":", 1)[1]
    names = []
    word = []
    i = 0
    while i < len(data):
        char = data[i]
        if char == "\\" and i + 1 < len(data) and data[i + 1] in " \\#:\t":
            word.append(data[i + 1])
            i += 2
            continue
        if char.isspace():
            if word:
                names.append("".join(word))
                word = []
        else:
            word.append(char)
        i += 1
    if word:
        names.append("".join(word))
    if not names:
        raise ValueError(f"empty depfile: {depfile}")
    if resolved is None:
        return sorted({(cwd / name).resolve() for name in names})
    paths = set()
    for name in names:
        token = (cwd, name)
        if token not in resolved:
            resolved[token] = (cwd / name).resolve()
        paths.add(resolved[token])
    return sorted(paths)


def object_key(depfile: Path, cwd: Path, config: bytes, source: Path | None = None,
               file_hashes=None):
    """Hash the command identity and every actual clang dependency's bytes."""
    digest = hashlib.sha256()
    digest.update(b"gw-object-v3\0" + config)
    cache = file_hashes if isinstance(file_hashes, FileCache) else None
    root = cwd if cache else cwd.resolve()
    paths = set(cache.intern_path(p) for p in cache.dependencies(depfile, cwd)) if cache else set(dependencies(depfile, cwd))
    if source is not None:
        paths.add(source if cache else source.resolve())
    for path in sorted(paths):
        token = (root, path)
        identity = cache.identities.get(token) if cache else None
        if identity is None:
            try:
                name = "lane:" + path.relative_to(root).as_posix()
            except ValueError:
                name = "external:" + path.as_posix()
            identity = b"\0" + name.encode("utf-8") + b"\0"
            if cache:
                cache.identities[token] = identity
        digest.update(identity)
        if cache:
            content_hash = cache.digest(path)
        elif file_hashes is not None and path in file_hashes:
            content_hash = file_hashes[path]
        else:
            content_hash = hash_file(path)
            if file_hashes is not None:
                file_hashes[path] = content_hash
        digest.update(content_hash)
    return digest.hexdigest()


def manifest_sources(files: Path, melee: Path):
    if not files.is_file():
        return []
    manifest = files.read_bytes().replace(b"\r", b"").decode("utf-8")
    return [name for name in manifest.split("\n") if name and (melee / name).exists()]


def scan_content(files: Path, melee: Path, out: Path, config: bytes, file_hashes=None):
    """Require dependency hashes; rebuild legacy objects once to establish them."""
    stale = []
    melee = melee.resolve()
    file_hashes = file_hashes if file_hashes is not None else FileCache(out / ".content-cache.json")
    for name in manifest_sources(files, melee):
        obj = out / (name.replace("/", "_") + ".obj")
        depfile = Path(str(obj) + ".d")
        keyfile = Path(str(obj) + ".sha256")
        if not obj.is_file():
            stale.append(name)
        elif not depfile.is_file() or not keyfile.is_file():
            stale.append(name)
        else:
            try:
                actual = object_key(depfile, melee, config, melee / name, file_hashes)
                if actual != file_hashes.key(keyfile) and not restore_object(obj, melee, config, melee / name, file_hashes):
                    stale.append(name)
            except (OSError, UnicodeError, ValueError):
                stale.append(name)
    file_hashes.save()
    return stale


def preserve_object(obj):
    """Keep one prior successful variant, bounded to one object per TU/shim."""
    previous = obj.parent / ".previous" / obj.name
    paths = [obj, Path(str(obj) + ".d"), Path(str(obj) + ".sha256")]
    if not all(p.is_file() for p in paths):
        return
    previous.parent.mkdir(parents=True, exist_ok=True)
    key = Path(str(previous) + ".sha256")
    key.unlink(missing_ok=True)  # Publish validity last, even after interruption.
    for source, target in zip(paths, [previous, Path(str(previous) + ".d"), key]):
        temp = Path(str(target) + f".{os.getpid()}.tmp")
        shutil.copyfile(source, temp)
        temp.replace(target)


def restore_object(obj, melee, config, source, cache):
    previous = obj.parent / ".previous" / obj.name
    depfile = Path(str(previous) + ".d")
    keyfile = Path(str(previous) + ".sha256")
    try:
        if not previous.is_file() or object_key(depfile, melee, config, source, cache) != cache.key(keyfile):
            return False
    except (OSError, ValueError, UnicodeError):
        return False
    # Replace directory entries, never overwrite a potentially hardlinked object.
    Path(str(obj) + ".sha256").unlink(missing_ok=True)
    for old, target in ((previous, obj), (depfile, Path(str(obj) + ".d")),
                        (keyfile, Path(str(obj) + ".sha256"))):
        temp = Path(str(target) + f".{os.getpid()}.tmp")
        shutil.copyfile(old, temp)
        temp.replace(target)
    print(f"restored recorded object: {source}", file=sys.stderr)
    return True


def compare(files: Path, melee: Path, out: Path, current, bash: str):
    legacy = PORT / "scan_stale_tus_legacy.sh"
    result = subprocess.run(
        [bash, legacy.as_posix(), files.as_posix(), melee.as_posix(), out.as_posix()],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
        raise RuntimeError(f"legacy stale scan failed with exit {result.returncode}")
    old = result.stdout.decode("utf-8").splitlines()
    if old != current:
        if scan(files, melee, out) != current:
            sys.stderr.write("tree changed during --compare; rerun on an idle lane\n")
            return False
        sys.stderr.writelines(difflib.unified_diff(
            [name + "\n" for name in old], [name + "\n" for name in current],
            fromfile="legacy", tofile="python",
        ))
        return False
    print(f"stale scan match: {len(current)} TU(s)")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files", type=Path, default=ROOT / "_build/masstest/files.txt")
    parser.add_argument("--melee", type=Path, default=Path(os.environ.get("GW_MELEE", ROOT / "melee")))
    build_root = Path(os.environ.get("GW_BUILD_ROOT", ROOT / "_build"))
    parser.add_argument("--out", type=Path, default=Path(os.environ.get("GW_OUT", build_root / "masstest/out")))
    parser.add_argument("--output", type=Path, help="write the ordered stale list for xargs")
    parser.add_argument("--compare", action="store_true", help="diff against the previous shell scan")
    parser.add_argument("--bash", default=default_bash(),
                        help="Git Bash executable for --compare")
    args = parser.parse_args()

    current = scan(args.files, args.melee, args.out)
    if args.compare and not compare(args.files, args.melee, args.out, current, args.bash):
        return 1
    data = "".join(name + "\n" for name in current).encode("utf-8")
    if args.output:
        args.output.write_bytes(data)
    elif not args.compare:
        sys.stdout.buffer.write(data)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, UnicodeError) as exc:
        sys.exit(f"stale scan failed: {exc}")
