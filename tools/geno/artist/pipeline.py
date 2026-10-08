"""pipeline.py - validate -> convert -> build models -> moves + geno.json -> install into an isolated test mods folder.

    python -m tools.geno.artist build path/to/fighter.json [--out DIR] [--no-install] [--launch lab] [--smoke]

Outputs under <out> (default <workspace>/_build/artist/<key>/, never committed):
    build/            plan.json, mesh_*.json, Gn<Token>_<costume>.dat, Gn<Token>AJ.dat, bank.json, build-report.md
    mods/<key>/       the define folder (mod.json, geno.json, moves/, files/)
    mods/geno-lab/    the LAB mod copied from the game checkout (so the folder works alone)
    mods/enabled.txt  what MELEE_MODS_DIR loads
"""
import json
import os
import shutil
import subprocess
import sys
import time

from . import assemble as A
from . import convert, model as M, spec, validate as V
from .model import ArtistError


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


def build(cfg_path, out=None, install=True, log=print, strict=False):
    t0 = time.time()
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
