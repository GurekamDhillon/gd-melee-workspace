"""Generate a stable notify-only manifest from the exact guarded release zip.

Signing keys/verifier are not configured. --allow-unsigned is required and
never creates a pretend signature. See UPDATE-MANIFEST.md.
"""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import zipfile

VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))?\Z")
MAX_MANIFEST = 64 * 1024


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summary(path):
    blocks = re.findall(r"<!--\s*update-summary\s*\n(.*?)-->", path.read_text(encoding="utf-8"), re.S)
    if len(blocks) != 1:
        raise ValueError("notes need exactly one <!-- update-summary bilingual block")
    result = {}
    for language in ("en", "es"):
        lines = re.findall(rf"^\s*{language}:\s*([^\n\r]+)\s*$", blocks[0], re.M)
        if len(lines) != 1 or not lines[0].strip() or len(lines[0].strip()) > 2048:
            raise ValueError(f"notes need one nonempty {language}: summary of at most 2048 characters")
        result[language] = lines[0].strip()
    return result


def generate(args):
    if not args.allow_unsigned:
        raise ValueError("signing is not configured: use --allow-unsigned for phase-1 notifications only")
    if not VERSION.fullmatch(args.version) or any(int(n) > 2147483647 for n in args.version.split(".")):
        raise ValueError("version must be a stable numeric x.y.z[.w] release")
    if not 1 <= args.protocol <= 2147483647:
        raise ValueError("protocol must be a positive 32-bit integer")
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", args.repo) or args.repo.split("/")[1] in (".", ".."):
        raise ValueError("repo must be owner/name")
    released = date.fromisoformat(args.released)
    if released.isoformat() != args.released:
        raise ValueError("released must be YYYY-MM-DD")
    name = f"GDMelee-{args.version}-win64"
    if args.zip.name != name + ".zip":
        raise ValueError("zip filename must match the release version")
    with zipfile.ZipFile(args.zip) as archive:
        for leaf, limit in (("version.txt", 16384), ("MANIFEST.sha256", 4 * 1024 * 1024)):
            candidates = [i for i in archive.infolist() if i.filename.rsplit("/", 1)[-1] == leaf]
            if len(candidates) != 1 or candidates[0].filename != f"{name}/{leaf}" or candidates[0].file_size > limit:
                raise ValueError(f"zip needs exactly one bounded {name}/{leaf}")
        metadata = archive.read(f"{name}/version.txt").decode("utf-8-sig")
        leading = re.match(r"^(\d+\.\d+\.\d+(?:\.\d+)?)(?:\s|$)", metadata)
        protocols = re.findall(r"^netplay_protocol\s+([0-9]+)\s*$", metadata, re.M)
        if not leading or leading[1] != args.version:
            raise ValueError("version.txt does not match the requested version")
        if len(protocols) != 1 or int(protocols[0]) != args.protocol:
            raise ValueError("version.txt does not match the release protocol policy")
        files_manifest = archive.read(f"{name}/MANIFEST.sha256")
        if not files_manifest.strip():
            raise ValueError("empty MANIFEST.sha256")
    base = f"https://github.com/{args.repo}/releases"
    manifest = {
        "schema": 1, "channel": "stable", "version": args.version,
        "released": args.released, "netplay_protocol": int(protocols[0]),
        "min_launcher_for_self_update": "0.3.0", "notes_url": f"{base}/tag/v{args.version}",
        "notes_short": summary(args.notes),
        "package": {"url": f"{base}/download/v{args.version}/{name}.zip",
                    "size": args.zip.stat().st_size, "sha256": sha256_file(args.zip)},
        "files_manifest_sha256": hashlib.sha256(files_manifest).hexdigest(), "critical": False,
    }
    raw = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(raw) > MAX_MANIFEST:
        raise ValueError("manifest exceeds 64 KiB")
    if Path(str(args.output) + ".sig").exists():
        raise ValueError("an existing update.json.sig must be removed before generating unsigned metadata")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as f:
        staging = Path(f.name)
        f.write(raw)
    try:
        staging.replace(args.output)
    finally:
        staging.unlink(missing_ok=True)
    print(f"UNSIGNED notify-only manifest: {args.output} (signing keys/verifier not configured; no .sig emitted)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--protocol", required=True, type=int)
    parser.add_argument("--notes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo", default="GurekamDhillon/gd-melee-workspace")
    parser.add_argument("--released", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--allow-unsigned", action="store_true")
    args = parser.parse_args()
    try:
        generate(args)
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as error:
        print(f"update manifest: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
