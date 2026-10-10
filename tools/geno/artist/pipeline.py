"""pipeline.py - validate -> convert -> build models -> moves + geno.json -> install into an isolated test mods folder.

    python -m tools.geno.artist build path/to/fighter.json [--out DIR] [--export] [--strict]
    python -m tools.geno.artist run-command path/to/fighter.json [--out DIR]

Outputs under <out> (default <workspace>/_build/artist/<key>/, never committed):
    build/            plan.json, mesh_*.json, Gn<Token>_<costume>.dat, Gn<Token>AJ.dat, bank.json, build-report.md
    mods/<key>/       the define folder (mod.json, geno.json, moves/, files/)
    mods/geno-lab/    the LAB mod copied from the game checkout (so the folder works alone)
    mods/enabled.txt  what MELEE_MODS_DIR loads
"""
import json
import re
import os
import shutil
import subprocess
import sys
import time

from . import assemble as A
from . import convert, model as M, spec, validate as V
from .model import ArtistError


def blender_exe():
    """Shared GW_BLENDER/.env/tools.json lookup (BLENDER remains an alias)."""
    from tools.port import tools_config
    try:
        path = tools_config.load_config()["GW_BLENDER"]
    except tools_config.ToolsConfigError as exc:
        raise ArtistError(str(exc)) from exc
    if path and os.path.isfile(path):
        return path
    raise ArtistError("Blender was not found: set GW_BLENDER in .env or run python tools/port/tools_config.py --detect (Blender is needed to export a .blend or make a starter)")


def _run_blender(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    except OSError as exc:
        raise ArtistError("cannot start Blender (%s); check GW_BLENDER in .env or _build/tools.json" % exc) from exc


def _blender_failure(result):
    """Keep stderr separate so a verbose stdout cannot bury the traceback."""
    lines = ["Blender exited with code %d." % result.returncode]
    for name, output in (("stdout", result.stdout), ("stderr", result.stderr)):
        tail = "\n".join((output or "").splitlines()[-20:])[-4000:]
        if tail:
            lines.append("Blender %s (last 20 lines):\n%s" % (name, tail))
    return "\n".join(lines)


def export_from_blend(cfg_path, log=print, force=False):
    """Export art.blend with export_fighter.py when its glb is missing or stale."""
    cfg_path = M.config_path(cfg_path)
    cfg = M.load_json(cfg_path)
    art = cfg.get("art", {})
    if not art.get("blend"):
        return True
    base = os.path.dirname(cfg_path)
    blend = os.path.normpath(os.path.join(base, art["blend"]))
    glb = os.path.normpath(os.path.join(base, art.get("glb", os.path.splitext(art["blend"])[0] + ".glb")))
    if not os.path.isfile(blend):
        raise ArtistError("art.blend: %s does not exist" % blend)
    if not force and os.path.isfile(glb) and os.path.getmtime(glb) >= os.path.getmtime(blend):
        log("[0/5] glb is newer than the .blend: not re-exporting (use --export to force)")
        return True
    log("[0/5] export %s -> %s (headless Blender)" % (os.path.basename(blend), glb))
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender", "export_fighter.py")
    r = _run_blender([blender_exe(), "-b", blend, "--python-exit-code", "1", "--python", script, "--", "--out", glb])
    for line in ((r.stdout or "") + "\n" + (r.stderr or "")).splitlines():
        if line.startswith("GENO "):
            log("  " + line)
    if r.returncode or not os.path.isfile(glb):
        log(_blender_failure(r))
        if not os.path.isfile(glb):
            log("Expected export is missing: %s" % glb)
        log("STOPPED: Blender export failed; fix the preflight finding or traceback above, then run build again.")
        return False
    return True


def new_character(dest, key, name, params=None, log=print):
    """Scaffold a .blend and fighter.json; build exports the glb on first use."""
    os.makedirs(dest, exist_ok=True)
    blend = os.path.join(dest, key + ".blend")
    cmd = [blender_exe(), "-b", "--python-exit-code", "1", "--python", os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender", "make_starter.py"), "--", "--out", blend, "--name", name]
    if params:
        cmd += ["--params", os.path.abspath(params)]
    r = _run_blender(cmd)
    if r.returncode or not os.path.isfile(blend):
        raise ArtistError("make_starter failed (expected %s):\n%s" % (blend, _blender_failure(r)))
    cfg = {"schema": "geno-artist/1", "key": key, "name": name, "art": {"blend": key + ".blend", "glb": "art/%s.glb" % key}}
    path = os.path.join(dest, "fighter.json")
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        json.dump(cfg, file, indent=1)
    log("created %s and %s" % (blend, path))
    log("The glb is exported by the first build; validate reports the build command until then.")
    log(M.build_fix(path))


def out_dir(f, override=None):
    if override:
        return os.path.abspath(override)
    if f.cfg.get("output"):
        return os.path.normpath(os.path.join(f.base, f.cfg["output"]))
    return os.path.join(spec.workspace_root(), "_build", "artist", f.key)


def mods_env(out):
    return os.path.join(out, "mods")


def run_command(f, out, scene=None):
    scene = scene or "mode=lab;p1=geno:%s/hu;p2=mario/cpu0;stage=fd" % f.key
    return ('MELEE_MODS_DIR="%s" MELEE_SCENE="%s" bash tools/port/run.sh %s-lab --iso "$GW_ISO_VANILLA"' %
            (mods_env(out).replace("\\", "/"), scene, f.key))


def build(cfg_path, out=None, install=True, log=print, strict=False, force_export=False):
    t0 = time.time()
    if not export_from_blend(cfg_path, log, force_export):
        return 1, None
    log("[1/5] validate %s" % cfg_path)
    rep, f = V.validate(cfg_path)
    log(V.format_report(rep))
    if not rep.ok:
        log("STOPPED: fix the blockers above (nothing was built).")
        return 1, None
    if strict and rep.count(V.W):
        log("STOPPED: --strict and there are warnings.")
        return 1, None
    out = out_dir(f, out)
    bd = os.path.join(out, "build")
    if os.path.isdir(bd):
        shutil.rmtree(bd)
    os.makedirs(bd)
    log("[2/5] plan, mesh and animation bank -> %s" % bd)
    plan, tris, lost = convert.write_mesh_and_plan(f, bd)
    fname, nbytes, worst = convert.write_bank(f, bd)
    log("  plan: %d joints, %d hurtboxes; bank %s: %d clips, %d bytes, max euler error %.5f rad" % (plan["joint_count"], len(plan["hurtboxes"]), fname, len(f.clips), nbytes, worst))
    if lost:
        log("  influence reduction moved %.1f vertex-weight units onto the two strongest bones" % lost)
    if plan["unresolved"]:
        log("  unresolved parts (not needed to load): %s" % [u.get("common_part") or u.get("role") for u in plan["unresolved"]])
    log("[3/5] models (fighterbuild, one per costume)")
    convert.build_models(f, bd, log)
    log("[4/5] moves and geno.json")
    mods = mods_env(out)
    mod_dir = os.path.join(mods, f.key)
    height = getattr(f, "_mesh_stats", {}).get("height", 11.7)
    hs = float(f.cfg.get("moves", {}).get("hitbox_scale") or max(0.5, min(1.5, height / 11.7)))
    n, notes = A.assemble(f, bd, mod_dir, hs, getattr(f, "ref_speeds", {}), log)
    log("  %d move scripts retargeted by role (hitbox scale %.2f)%s" % (n, hs, "".join("\n  note: " + x for x in notes)))
    r = subprocess.run([sys.executable, "-m", "tools.geno.check", mod_dir], cwd=spec.workspace_root(), capture_output=True, text=True, env=dict(os.environ, GW_MELEE=spec.game_dir()))
    tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
    log("  geno check: " + (" | ".join(tail) if tail else "(no output)"))
    if r.returncode:
        log("STOPPED: the generated define does not check (a converter bug, please report).")
        return 1, None
    log("[5/5] install into the isolated mods folder %s" % mods)
    if install:
        lab_src = os.path.join(spec.game_dir(), "pc", "geno", "mods", "geno-lab")
        lab_dst = os.path.join(mods, "geno-lab")
        if os.path.isdir(lab_src):
            if os.path.isdir(lab_dst):
                shutil.rmtree(lab_dst)
            shutil.copytree(lab_src, lab_dst)
        with open(os.path.join(mods, "enabled.txt"), "w", newline="\n") as fh:
            fh.write("geno-lab\n%s\n" % f.key)
    from . import gameplay_cache
    gameplay_cache.write(cfg_path, bd, token=f.token, costumes=f.costumes,
                         height=height, ref_speeds=getattr(f, "ref_speeds", {}))
    write_report(f, rep, out, bd, plan, nbytes)
    log("OK in %.0f s.  Report: %s" % (time.time() - t0, os.path.join(bd, "build-report.md")))
    log("Preview (LAB):  " + run_command(f, out))
    log("Restart the game after every rebuild: definitions are read once at start (geno.md 22).")
    return 0, f


def write_report(f, rep, out, bd, plan, nbytes):
    ph = getattr(f, "_placeholders", [])
    lines = ["# Build report: %s (%s)" % (f.name, f.key), "",
             "- joints %d, hurtboxes %d (%s), clips %d, bank %d bytes" % (plan["joint_count"], len(plan["hurtboxes"]), f.hurtbox_src, len(f.clips), nbytes),
             "- measured reference speeds (units/frame at rate 1.0): %s" % (getattr(f, "ref_speeds", {}) or "none"), ""]
    lines.append("## Findings")
    for i in rep.items:
        if i["severity"] != V.I:
            lines.append("- %s %s %s: %s%s" % (i["severity"], i["code"], i["where"], i["message"], (" -> " + i["fix"]) if i["fix"] else ""))
    lines.append("")
    lines.append("## Rows that play a placeholder clip (%d)" % len(ph))
    byc = {}
    for row in f.rows:
        if row["status"] == "placeholder":
            byc.setdefault(row["clip"], []).append(row["row"])
    for c, rows in sorted(byc.items(), key=lambda kv: str(kv[0])):
        lines.append("- plays `%s`: %s" % (c, ", ".join(rows)))
    lines.append("")
    lines.append("## Clips authored but not mapped to a row")
    um = [c for c in f.clips.values() if not c.rows]
    lines.append(", ".join(c.name for c in um) or "none")
    open(os.path.join(bd, "build-report.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")



def build_gameplay(cfg_path, out=None, log=print):
    """Reassemble cached art into a checked package without Blender/fighterbuild.

    The first full build records the Stage A contract. Changes outside moves,
    attributes, jumps and display name require another full build.
    """
    from pathlib import Path
    from types import SimpleNamespace
    import tempfile
    from . import gameplay_cache

    cfg_path = os.path.abspath(cfg_path)
    cfg = M.load_json(cfg_path)
    key = cfg.get("key", "")
    if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", key):
        raise ArtistError("fighter.json has an invalid define key")
    shell = SimpleNamespace(cfg=cfg, base=os.path.dirname(cfg_path), key=key)
    out = out_dir(shell, out)
    bd = Path(out) / "build"
    try:
        cache = gameplay_cache.read_current(cfg_path, bd)
    except ValueError as exc:
        raise ArtistError(str(exc)) from exc
    f = SimpleNamespace(cfg=cfg, key=key, name=cfg.get("name") or key,
                        token=cache["token"], costumes=cache["costumes"])
    required = [bd / "plan.json", bd / ("Gn%sAJ.dat" % f.token)]
    required += [bd / ("Gn%s_%s.dat" % (f.token, c["name"])) for c in f.costumes]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise ArtistError("Gameplay-only rebuild needs a full build first; missing: " + ", ".join(missing))
    height = cache["height"]
    scale = float(cfg.get("moves", {}).get("hitbox_scale") or max(0.5, min(1.5, height / 11.7)))
    destination = Path(out) / "mods" / key
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="play-gameplay-", dir=out) as tmp:
        staged = Path(tmp) / key
        log("Rebuilding gameplay; using cached plan, models and animation bank")
        n, notes = A.assemble(f, str(bd), str(staged), scale, cache["ref_speeds"], log)
        result = subprocess.run([sys.executable, "-m", "tools.geno.check", str(staged)],
                                cwd=spec.workspace_root(), capture_output=True, text=True,
                                env=dict(os.environ, GW_MELEE=spec.game_dir()))
        log((result.stdout + result.stderr).strip())
        if result.returncode:
            log("STOPPED: rebuilt gameplay did not check; the installed package was kept.")
            return result.returncode, None
        previous = Path(tmp) / "previous"
        if destination.exists():
            destination.rename(previous)
        try:
            staged.rename(destination)
        except OSError:
            if previous.exists():
                previous.rename(destination)
            raise
    log("Gameplay rebuilt: %d move scripts; art and animation bank reused." % n)
    for note in notes:
        log("  note: " + note)
    return 0, f
