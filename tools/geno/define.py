"""Slice-1 author contract and source-only package export."""
import hashlib
import json
from pathlib import Path
import shutil


# The retail fighters a define may name in "ai.like" and "kirby_copy" (the names and aliases of geno_registry.c's gn_vanilla table; Nana is Popo's partner).
RETAIL_FIGHTERS = ("mario", "fox", "captain", "falcon", "donkey", "dk", "kirby", "koopa", "bowser", "link", "seak", "sheik", "ness", "peach", "popo", "pikachu",
                   "samus", "yoshi", "purin", "jigglypuff", "mewtwo", "luigi", "mars", "marth", "zelda", "clink", "younglink", "drmario", "falco", "pichu",
                   "gamewatch", "gnw", "ganon", "ganondorf", "emblem", "roy")


def definition_schema():
    return {"type": "object", "additionalProperties": False, "required": ["key", "name", "base", "common", "resources"],
        "properties": {"key": {"type": "string", "pattern": r"^[a-z0-9][a-z0-9_.-]{0,38}$"},
            "name": {"type": "string", "minLength": 1, "maxLength": 47, "pattern": "^[ -~]+$"},
            "base": {"enum": ["mario", "none"], "description": "mario: the retail Mario preset is the template; none (geno 9): the package owns its model, bank, parts table and joint fields (docs/geno.md 22.4)"},
            "common": {"const": "melee.common.v1"}, "resources": {"enum": ["retail:mario", "mod:files"], "description": "retail:mario with base mario; mod:files with base none"}}}


def validate_definition(data, fighter, path):
    errors = []
    own = fighter["define"].get("base") == "none"
    if data["geno"] not in (6, 7, 8, 9, 10):
        errors.append((path+".define", "define requires geno: 6, 7, 8, 9 or 10"))
    if own and data["geno"] < 9:
        errors.append((path+".define.base", "base none needs geno: 9"))
    if own != (fighter["define"].get("resources") == "mod:files"):
        errors.append((path+".define.resources", "base none takes resources mod:files; base mario takes retail:mario"))
    if own and "fighter" not in fighter:
        errors.append((path+".fighter", "base none needs a fighter block (plan, animation, costumes)"))
    if ".." in fighter["define"]["key"]:
        errors.append((path+".define.key", "identity must not contain '..'"))
    # Slice 2 (geno 7) admits special_attributes, fx_bindings and the whole attribute table; articles, own
    # model/clips, sounds and Lua are later slices.
    # Slice 3 (geno 8) admits articles and the named-sound table (the resolver): every sound an article names must exist.
    for key in ("articles", "sounds"):
        if key in fighter and data["geno"] < 8:
            errors.append((path+"."+key, "needs geno: 8"))
    names = [s.get("name") for s in fighter.get("sounds", []) if isinstance(s, dict)]
    if len(set(names)) != len(names):
        errors.append((path+".sounds", "duplicate sound name"))
    for j, article in enumerate(fighter.get("articles", [])):
        for key in ("spawn_sound", "end_sound"):
            if key in article and article[key] not in names:
                errors.append((path+".articles[%d].%s" % (j, key), "%r is not a name in sounds (no donor fallback)" % (article[key],)))
    # Slice 6 (geno 9, no version bump): the package's own menu and HUD art, and a base none define's declared costume colours.
    if "presentation" in fighter and data["geno"] < 9:
        errors.append((path+".presentation", "needs geno: 9"))
    costumes = fighter.get("fighter", {}).get("costumes", [])
    for team in ("red", "blue", "green"):
        rows = [i for i, c in enumerate(costumes) if c.get("team") == team]
        if len(rows) > 1:
            errors.append((path+".fighter.costumes[%d].team" % rows[1], "team %s is already declared by costume %d" % (team, rows[0])))
    for key in ("portrait", "stock"):
        value = fighter.get("presentation", {}).get(key)
        if isinstance(value, list) and own and len(value) > len(costumes):
            errors.append((path+".presentation."+key, "%d entries for %d costumes" % (len(value), len(costumes))))
    # Slice 6 (geno 10): the CPU's stand-in fighter, what Kirby copies, the package's own sound clips, the results emblem.
    for key in ("ai", "kirby_copy"):   # they change what a fighter does; audio and the emblem are presentation and take 9 like the art
        if key in fighter and data["geno"] < 10:
            errors.append((path+"."+key, "needs geno: 10"))
    if "audio" in fighter and data["geno"] < 9:
        errors.append((path+".audio", "needs geno: 9"))
    like = fighter.get("ai", {}).get("like") if isinstance(fighter.get("ai"), dict) else None
    if like is not None and str(like).lower() not in RETAIL_FIGHTERS:
        errors.append((path+".ai.like", "%r is not a retail fighter (mario, fox, captain, ... emblem)" % (like,)))
    copy = fighter.get("kirby_copy")
    if copy is not None and copy != "none":
        name = copy[len("retail:"):] if isinstance(copy, str) and copy.startswith("retail:") else None
        if name is None or name.lower() not in RETAIL_FIGHTERS or name.lower() == "kirby":
            errors.append((path+".kirby_copy", 'must be "none" or "retail:<fighter>" (a retail fighter other than Kirby)'))
    sfxs = [v.get("sfx") for v in (fighter.get("audio") or {}).get("voice", []) if isinstance(v, dict)]
    if len(set(sfxs)) != len(sfxs):
        errors.append((path+".audio.voice", "a sound id is replaced twice"))
    for key in ("fx_bindings", "special_attributes"):
        if key in fighter and data["geno"] < 7:
            errors.append((path+"."+key, "needs geno: 7"))
    from . import schema
    first40 = list(schema.S["attrs"])[:40]
    for name in fighter.get("attributes", {}):
        if name not in first40 and data["geno"] < 7:
            errors.append((path+".attributes."+name, "needs geno: 7 (only the first 40 attributes exist in geno: 6)"))
    motions = [row["motion"] for row in fighter.get("common_states", [])]
    if len(set(motions)) != len(motions):
        errors.append((path+".common_states", "duplicate motion override"))
    keys = [f["define"]["key"] for f in data["fighters"] if "define" in f]
    if len(set(keys)) != len(keys):
        errors.append((path+".define.key", "duplicate definition identity in package"))
    # Native Mario preset: ftData_Table_Unk0[0].count == 303, rows 0..302.
    for row in (fighter.get("subactions", []) if not own else []):   # a base none define owns its row table
        if row["index"] >= 303:
            errors.append((path+".subactions", "Mario preset subaction must be in 0..302"))
    for row in (fighter.get("common_states", []) if not own else []):
        if row.get("subaction", 0) >= 303:
            errors.append((path+".common_states", "Mario preset subaction must be in 0..302"))
    for field in (("states", "motion_anims") if not own else ()):
        for row in fighter.get(field, []):
            if isinstance(row.get("subaction"), int) and row["subaction"] >= 303:
                errors.append((path+"."+field, "Mario preset subaction must be in 0..302"))
    return errors


MOVE_TAGS = ("jab", "dash_attack", "tilt", "smash", "aerial", "grab", "throw", "special", "projectile")


def expand_moves(data):
    """The authoring sugar (D9): a fighter's `moves` block becomes a `subactions` overlay plus a
    `common_states` row per move. The engine reads no `moves` key; the result has engine keys only.

        "moves": {"ftilt": {"motion": 53, "words": "moves/ftilt.words", "tag": "tilt"}}

    `subaction` may be given; otherwise it is the animation row the donor's motion row plays."""
    import copy
    data = copy.deepcopy(data)
    for fighter in data.get("fighters", []):
        moves = fighter.pop("moves", None)
        if not moves:
            continue
        from .report import motion_subactions
        rows = motion_subactions()
        for name, move in moves.items():
            motion = move["motion"]
            sub = move.get("subaction", rows.get(motion, (None, -1))[1])
            if sub is None or sub < 0:
                raise ValueError("move %r: motion %d has no animation row; give a subaction" % (name, motion))
            overlay = {"index": sub, ("file" if isinstance(move["words"], str) else "words"): move["words"]}
            if move.get("tag"):
                overlay["move_tag"] = move["tag"]
            fighter.setdefault("subactions", []).append(overlay)
            row = {"motion": motion}
            if move.get("tag"):
                row["move_tag"] = move["tag"]
            fighter.setdefault("common_states", []).append(row)
    return data


def export_package(source, out):
    from .check import load_json, validate, local_file
    source, out = Path(source), Path(out)
    data = expand_moves(load_json(source / "geno.json"))
    if validate(data, source) or not all("define" in f for f in data["fighters"]):
        raise ValueError("export requires a valid standalone definition")
    if out.exists():
        raise ValueError("export refuses an existing output")
    # Disallow archive/audio payloads even if not referenced. Do not copy a whole mod blindly.
    if any(p.suffix.lower() in (".dat", ".usd", ".ssm", ".iso", ".gcm", ".hps") for p in source.rglob("*")):
        raise ValueError("slice-1 package must reference retail assets, not contain archives")
    files = {"mod.json", "geno.json"}
    for f in data["fighters"]:
        if isinstance(f.get("fx_bindings"), str):
            errors = []
            path = local_file(source, f["fx_bindings"], "fx_bindings", errors)
            if errors or path is None: raise ValueError("invalid package effect bindings")
            files.add(path.relative_to(source).as_posix())
        for key, value in (f.get("presentation") or {}).items():   # slice 6: the package's own menu and HUD art (original pixels, .gxtex)
            for name in ([value] if isinstance(value, str) else value):
                if (source / "files" / name).is_file():
                    files.add("files/" + name)
        audio = f.get("audio") or {}   # slice 6 (geno 10): the package's own sound clips (.gnsnd, converted from original audio by tools/geno/audio.py)
        for name in ([audio["announcer"]] if "announcer" in audio else []) + [v["file"] for v in audio.get("voice", []) if isinstance(v, dict) and "file" in v]:
            if (source / "files" / name).is_file():
                files.add("files/" + name)
        for row in f.get("subactions", []):
            if isinstance(row.get("file"), str):
                errors = []
                path = local_file(source, row["file"], "file", errors)
                if errors or path is None: raise ValueError("invalid package script")
                files.add(path.relative_to(source).as_posix())
        if isinstance(f.get("fx_bindings"), str):   # the effect packages the bindings name travel with them
            for p in (source / "fx").rglob("*") if (source / "fx").is_dir() else ():
                if p.is_file() and p.suffix.lower() in (".json", ".png"):
                    files.add(p.relative_to(source).as_posix())
    expanded = (json.dumps(data, indent=2) + "\n").encode("utf-8")   # engine keys only

    def digest(name):
        return hashlib.sha256(expanded if name == "geno.json" else (source/name).read_bytes()).hexdigest()
    manifest = {"format": 1, "backend": "geno.define.v1", "offline_only": True, "retail_preset": "mario.v1",
        "files": {name: digest(name) for name in sorted(files)}}
    manifest["sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    out.mkdir(parents=True); (out / "files").mkdir()
    for name in sorted(files):
        dest = out / name; dest.parent.mkdir(parents=True, exist_ok=True)
        if name == "geno.json":
            dest.write_bytes(expanded)
        else:
            shutil.copyfile(source/name, dest)
    (out / "manifest.runtime.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    return manifest
