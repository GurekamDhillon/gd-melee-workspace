"""Slice-1 author contract and source-only package export."""
import hashlib
import json
from pathlib import Path
import shutil


def definition_schema():
    return {"type": "object", "additionalProperties": False, "required": ["key", "name", "base", "common", "resources"],
        "properties": {"key": {"type": "string", "pattern": r"^[a-z0-9][a-z0-9_.-]{0,38}$"},
            "name": {"type": "string", "minLength": 1, "maxLength": 47, "pattern": "^[ -~]+$"},
            "base": {"const": "mario"}, "common": {"const": "melee.common.v1"}, "resources": {"const": "retail:mario"}}}


def validate_definition(data, fighter, path):
    errors = []
    if data["geno"] != 6:
        errors.append((path+".define", "define requires geno: 6"))
    if ".." in fighter["define"]["key"]:
        errors.append((path+".define.key", "identity must not contain '..'"))
    # Slice 1 is native inheritance and script/attribute overrides, not owned assets or Lua.
    for key in ("articles", "fx_bindings", "special_attributes"):
        if key in fighter:
            errors.append((path+"."+key, "standalone definitions do not support this later-slice field"))
    motions = [row["motion"] for row in fighter.get("common_states", [])]
    if len(set(motions)) != len(motions):
        errors.append((path+".common_states", "duplicate motion override"))
    keys = [f["define"]["key"] for f in data["fighters"] if "define" in f]
    if len(set(keys)) != len(keys):
        errors.append((path+".define.key", "duplicate definition identity in package"))
    # Native Mario preset: ftData_Table_Unk0[0].count == 303, rows 0..302.
    for row in fighter.get("subactions", []):
        if row["index"] >= 303:
            errors.append((path+".subactions", "Mario preset subaction must be in 0..302"))
    for row in fighter.get("common_states", []):
        if row.get("subaction", 0) >= 303:
            errors.append((path+".common_states", "Mario preset subaction must be in 0..302"))
    for field in ("states", "motion_anims"):
        for row in fighter.get(field, []):
            if isinstance(row.get("subaction"), int) and row["subaction"] >= 303:
                errors.append((path+"."+field, "Mario preset subaction must be in 0..302"))
    return errors


def export_package(source, out):
    from .check import load_json, validate, local_file
    source, out = Path(source), Path(out)
    data = load_json(source / "geno.json")
    if validate(data, source) or not all("define" in f for f in data["fighters"]):
        raise ValueError("export requires a valid standalone definition")
    if out.exists():
        raise ValueError("export refuses an existing output")
    # Disallow archive/audio payloads even if not referenced. Do not copy a whole mod blindly.
    if any(p.suffix.lower() in (".dat", ".usd", ".ssm", ".iso", ".gcm", ".hps") for p in source.rglob("*")):
        raise ValueError("slice-1 package must reference retail assets, not contain archives")
    files = {"mod.json", "geno.json"}
    for f in data["fighters"]:
        for row in f.get("subactions", []):
            if isinstance(row.get("file"), str):
                errors = []
                path = local_file(source, row["file"], "file", errors)
                if errors or path is None: raise ValueError("invalid package script")
                files.add(path.relative_to(source).as_posix())
    manifest = {"format": 1, "backend": "geno.define.v1", "offline_only": True, "retail_preset": "mario.v1",
        "files": {name: hashlib.sha256((source/name).read_bytes()).hexdigest() for name in sorted(files)}}
    manifest["sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    out.mkdir(parents=True); (out / "files").mkdir()
    for name in sorted(files):
        dest = out / name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source/name, dest)
    (out / "manifest.runtime.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    return manifest
