"""Editable local Falcon project and gameplay-only package rebuilds.

Only templates/tools are tracked. Plans, baselines, words and disassembled
sources are written below _build, and existing source edits are never reseeded.
"""
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from . import metadata

MANIFEST = "falcon_sources.json"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def generated(path):
    path = Path(path).resolve()
    if "_build" not in path.parts:
        raise ValueError(f"disc-derived output must be below _build: {path}")
    return path


def inside(base, relative):
    relative = str(relative).replace("\\", "/")
    if not relative or Path(relative).is_absolute() or ":" in relative or ".." in relative.split("/"):
        raise ValueError(f"unsafe relative path: {relative}")
    base = Path(base).resolve()
    path = (base / relative).resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"path escapes {base}: {relative}")
    return path


def write(path, text):
    """Replace, don't truncate; keep stable files' mtimes for fast reloads."""
    path = Path(path)
    data = text.encode("utf-8")
    if path.is_file() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, data):
    write(path, json.dumps(data, indent=2) + "\n")


def codec():
    # Import after the CLI has applied GW_MELEE; the shared codec reads that contract.
    from tools.geno import script
    return script


def falcon_fighter(document):
    fighters = document.get("fighters", [])
    if len(fighters) != 1 or fighters[0].get("define", {}).get("template") != "captain":
        raise ValueError("expected one Captain Falcon retail define")
    return fighters[0]


def plan_file(package, document):
    fighter = falcon_fighter(document)
    return inside(package / "files", fighter["fighter"]["plan"])


def package_ready(package):
    package = Path(package)
    if not all((package / name).is_file() for name in ("geno.json", "mod.json")):
        return False
    document = load(package / "geno.json")
    fighter = falcon_fighter(document)["fighter"]
    paths = [plan_file(package, document), inside(package / "files", fighter["animation"])]
    paths += [inside(package / "files", c["file"]) for c in fighter["costumes"]]
    return all(p.is_file() for p in paths)


def ensure_package(package, seed, root):
    """No subprocess on the hot path. Recover assets only if the package is missing."""
    package, root = generated(package), Path(root).resolve()
    if package_ready(package):
        return "gameplay-only"
    if seed and Path(seed).resolve() != package and package_ready(seed):
        shutil.copytree(seed, package, dirs_exist_ok=True)
        return "restaged"
    from .make_falcon_art import iso_path
    iso = iso_path(root)
    if not iso or not Path(iso).is_file():
        raise ValueError("missing Falcon package and seed; set GW_ISO_VANILLA to rebuild from your disc")
    disc = generated(root / "_build/geno-falcon-art/disc")
    disc.mkdir(parents=True, exist_ok=True)
    required = ["PlCa.dat", "PlCaAJ.dat", "PlCaNr.dat", "PlCaGy.dat", "PlCaRe.usd",
                "PlCaWh.dat", "PlCaGr.dat", "PlCaBu.dat", "PlCo.dat"]
    for prefix in ("PlCa", "PlCo"):
        if any(not (disc / name).is_file() for name in required if name.startswith(prefix)):
            subprocess.run([sys.executable, str(root / "tools/gc_extract.py"), str(iso), str(disc),
                            "--only", prefix], check=True)
    package.parent.mkdir(parents=True, exist_ok=True)
    # The temporary directory is confined to the generated package's parent.
    with tempfile.TemporaryDirectory(prefix="falcon-package-", dir=package.parent) as temporary:
        fresh = Path(temporary) / "geno-falcon"
        subprocess.run([sys.executable, str(root / "ports/ir/tools/retail_define.py"), "captain",
                        "--disc-dir", str(disc), "--out", str(fresh)], check=True)
        if not package_ready(fresh):
            raise ValueError("retail_define did not produce a complete Falcon package")
        shutil.copytree(fresh, package, dirs_exist_ok=True)
    return "extracted"


def overlay_words(package, overlay):
    asm = codec()
    if "words" in overlay:
        return [asm.word(w) for w in overlay["words"]]
    return asm.read_words(inside(package, overlay["file"]).read_text(encoding="utf-8-sig"))


def editable_source(words):
    asm = codec()
    text = asm.disassemble(words)
    # The Workbench uses this assembler alias when it closes a source hitbox window.
    text = re.sub(r"(?m)^" + re.escape(asm.NAMES[16]) + r"(?=\s|$)", "clear_hitboxes", text)
    if asm.assemble(text) != words:
        raise ValueError("disassembled move did not round-trip exactly")
    if re.search(r"(?m)^hitbox\s+raw=", text):
        raise ValueError("hitbox could not be exposed as editable named fields")
    return "# Local disc-derived move; do not commit or share. Branch operands are word indices.\n" + text


def prepare(project, package, states, template, *, root, game=None, seed=None):
    project, package = generated(project), generated(package)
    template, root = Path(template), Path(root).resolve()
    marker = project / MANIFEST
    if marker.is_file():
        manifest = load(marker)
        if Path(manifest["package"]).resolve() != package:
            raise ValueError("project belongs to a different package")
        for entry in manifest["overlays"]:
            # A missing authored source is an error, never a request to discard an edit.
            inside(project, entry["source"]).read_text(encoding="utf-8-sig")
        for name in ("gameplay.json", "workbench.json", "role_map.json"):
            load(project / name)
        return project
    document = load(package / "geno.json")
    fighter = falcon_fighter(document)
    plan = load(plan_file(package, document))
    role_table = load(project / "role_map.json" if (project / "role_map.json").is_file()
                      else template / "role_map.json")
    roles, _ = metadata.resolve_roles(plan, role_table)
    sources, entries, scripts = {}, [], {}
    for overlay in fighter.get("subactions", []):
        index = overlay["index"]
        if type(index) is not int or not 0 <= index < len(plan["row_clips"]) or index in scripts:
            raise ValueError(f"duplicate or invalid overlay index {index}")
        source = f"moves/{index:03}.genoasm"
        sources[source] = editable_source(overlay_words(package, overlay))
        scripts[index] = source
        entries.append({"index": index, "source": source, "output": f"moves/wb-{index:03}.words"})
    if not entries:
        raise ValueError("package has no overlays; rebuild it without --no-scripts")
    gameplay_path = project / "gameplay.json"
    gameplay = load(gameplay_path if gameplay_path.is_file() else template / "gameplay.json")
    gameplay["moves"] = metadata.make_rows(plan, states, scripts, gameplay["moves"])
    gameplay["note"] = ("All Captain action states; subaction is the animation/script row. Shared subactions share a source. "
                        "An empty pick.clip explicitly means there is no fixed clip, or the local bank lacks that row.")
    config_path = project / "workbench.json"
    config = load(config_path if config_path.is_file() else template / "workbench.json")
    config.update(moves_dir="moves", plan_abs=str(plan_file(package, document)), mods_dir=str(package.parent),
                  rebuild=[sys.executable, str(Path(__file__).with_name("build.py")), "--project", "{project}"])
    art = Path(config["art_blend"])
    config["art_blend"] = str(art if art.is_absolute() else root / art)
    config.setdefault("art", {})["calibration_action_offset"] = 0   # Falcon: Blender action frame N == engine frame N (Goku: N-1)
    config["art"]["bone_aliases"] = {j["name"]: f"JOBJ_{j['index']}" for j in plan["joints"]}
    manifest = {"version": 1, "package": str(package), "workspace": str(root),
                "game": str(Path(game or os.environ.get("GW_MELEE") or root / "melee").resolve()),
                "seed_package": str(Path(seed).resolve()) if seed else "",
                "geno": document, "plan": plan, "states": states, "overlays": entries}
    # Finish all validation before publishing any source; preserve interrupted-run edits.
    for source, text in sources.items():
        path = inside(project, source)
        if path.exists() and path.read_text(encoding="utf-8-sig") != text:
            raise ValueError(f"existing source differs; preserve it before initializing: {path}")
    for source, text in sources.items():
        write(inside(project, source), text)
    write_json(project / "role_map.json", role_table)
    write_json(gameplay_path, gameplay)
    write_json(config_path, config)
    annotated = copy.deepcopy(plan)
    annotated["roles"] = roles
    write_json(plan_file(package, document), annotated)
    # This is the initialization commit marker. Later launches never regenerate these sources.
    write_json(marker, manifest)
    return project


def assemble_source(text, plan, tokens):
    joints = {j["name"]: j["index"] for j in plan["joints"]}
    joints.update({str(j["index"]): j["index"] for j in plan["joints"]})
    joints.update(tokens)
    def joint(match):
        token = match[1]
        if token not in joints:
            raise ValueError(f"unknown joint/role {token}")
        return "joint=" + str(joints[token])
    text = re.sub(r"\bjoint=@([^@\s]+)@", joint, text)
    asm = codec()
    words = asm.assemble(text)
    if not words:
        raise ValueError("move script is empty")
    commands = list(asm.commands(words))
    boundaries = {offset for offset, _ in commands}
    valid_joints = {j["index"] for j in plan["joints"]}
    for offset, command in commands:
        op = command[0] >> 26
        if op in (5, 7) and command[1] not in boundaries:
            raise ValueError(f"word {offset}: branch does not target a command in this overlay")
        if op == 11 and (command[0] >> 11 & 255) not in valid_joints:
            raise ValueError(f"word {offset}: hitbox joint is absent from the plan")
    return words


def rebuild(project):
    project = generated(project)
    manifest = load(project / MANIFEST)
    if manifest.get("version") != 1:
        raise ValueError("unsupported Falcon source manifest")
    package = generated(manifest["package"])
    plan = copy.deepcopy(manifest["plan"])
    roles, tokens = metadata.resolve_roles(plan, load(project / "role_map.json"))
    plan["roles"] = roles
    document = copy.deepcopy(manifest["geno"])
    fighter = falcon_fighter(document)
    entries = {e["index"]: e for e in manifest["overlays"]}
    if len(entries) != len(manifest["overlays"]):
        raise ValueError("duplicate source overlay")
    if set(entries) != {o["index"] for o in fighter["subactions"]}:
        raise ValueError("source manifest does not cover every overlay")
    outputs = {}
    for overlay in fighter["subactions"]:
        entry = entries[overlay["index"]]
        text = inside(project, entry["source"]).read_text(encoding="utf-8-sig")
        words = assemble_source(text, plan, tokens)
        output = inside(package, entry["output"])
        if output in outputs:
            raise ValueError("two overlays share an output word file")
        outputs[output] = "\n".join(f"0x{word:08X}" for word in words) + "\n"
        overlay.pop("words", None)
        overlay["file"] = entry["output"]
    # Clip assignments can change the plan without re-extracting its animation bank.
    # Two action states sharing one subaction cannot ask that row to play different clips.
    selected = {}
    states = {s["motion"]: s for s in manifest["states"]}
    seen = set()
    for row in load(project / "gameplay.json")["moves"]:
        for motion in row["motions"]:
            if motion not in states or motion in seen:
                raise ValueError(f"unknown or duplicate motion {motion}")
            seen.add(motion)
            sub = states[motion]["subaction"]
            clip = row.get("pick", {}).get("clip", "")
            expected = entries[sub]["source"] if sub in entries else ""
            if row.get("script", "") != expected:
                raise ValueError(f"{row['name']}: script binding changed; shared subactions use {expected}")
            if row.get("pick", {}).get("crop_start", 0):
                raise ValueError("retail clip cropping requires an animation rebuild")
            if sub < 0:
                if clip:
                    raise ValueError(f"{row['name']} has no fixed animation row")
                continue
            if clip and clip not in plan["bank"]["clips"]:
                raise ValueError(f"unknown clip {clip}")
            if not clip and plan["row_clips"][sub] is not None:
                raise ValueError(f"{row['name']}: cannot remove a clip")
            if sub in selected and selected[sub] != clip:
                raise ValueError(f"states sharing subaction {sub} must share a clip assignment")
            selected[sub] = clip
    if seen != set(states):
        raise ValueError("gameplay no longer lists every Captain action state")
    for sub, clip in selected.items():
        if clip:
            plan["row_clips"][sub] = clip
    # Compile and validate every source before recovering/publishing any package output.
    mode = ensure_package(package, manifest.get("seed_package"), manifest["workspace"])
    for path, text in outputs.items():
        write(path, text)
    # Hand-animated clips (<project>/anim/hand.json, geno_workbench/README "Hand-animate with IK and FK"): appended to the bank copy in the package
    from . import hand_apply
    hand_report = hand_apply.apply_hand(project, inside(package / "files", falcon_fighter(document)["fighter"]["animation"]), plan)
    for item in hand_report:
        print("HAND:", json.dumps(item, sort_keys=True))
    write_json(plan_file(package, document), plan)
    write_json(package / "geno.json", document)
    return mode
