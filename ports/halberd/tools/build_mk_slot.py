"""One command for the Meta Knight fighter slot (ACE disc): scripts + numbers + MK's own model and clips.

    python tools/build_mk_slot.py                                  # tuning.json -> mods-slot/metaknight-slot
    python tools/build_mk_slot.py --preset tuning.melee-feel.json

Steps:
 1. tools/build_mk.py (preset) -> build/stage: files/PlKb.dat (stage A), final/PlBm.dat (stage B), CHANGES.json, geno.json
 2. tools/verify_mk.py on that build (brawl-kirby's verify_mod.py + MK checks); a failure leaves the mod folder alone
 3. mod folder: files/PlBm.dat (= stage B) + MxDt.dat / PlCo.dat / MnSlChr.usd / IfAll.usd (tools/mk_slot_files.py, built
    on top of brawl-kirby-slot's copies so both slots coexist)
 3b. tools/build_mk_ui.py: MK's own menu art from Brawl's menu textures replaces the Kirby placeholders - CSS icon (MnSlChr
    icon joint), 6 CSPs (MnSlChr), 6 stock icons (IfAll), results-screen name strips (GmRst.usd, new in this mod)
 4. model/tools/install_mk.py <mod> --scripts=mk --no-vis (Phases 2/3: costumes PlBm<cc>.dat, PlBmAJ.dat, ftData joint
    fields, motion table -> MK clips, demo-table hole, PlCo parts, MxDt anim file + costumes). --scripts=mk: this build
    already writes MK joints; --no-vis: this build writes the ModelVis commands itself.
 5. clip overrides (build_mk.py CLIP_OVERRIDES: rows whose clip the scripts are built for) written into PlBm.dat's motion
    table, then a post-install check that every row this build wrote plays the clip length it was built against.
 6. geno.json (Geno profile: multi-jump, v1 overlays and - knob mk.geno_v2, on by default - the v2 states / specials / glide,
    tornado and drill blocks; the v2 states play build_mk.py's V2ROWS, Kirby copy-ability rows repointed at MK's extra
    clips; the post-install check covers them and the Drill row's animation-driven flag), CHANGES.json, TUNING.json, mod.json
Rebuild after brawl-kirby-slot changes its shared files, and after the model/anim phases rebuild their outputs."""
import argparse, json, os, shutil, subprocess, sys, hashlib, struct
HERE = os.path.dirname(os.path.abspath(__file__)); MK = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(MK, "model", "tools"))
ap = argparse.ArgumentParser()
ap.add_argument("--preset", default=os.path.join(MK, "tuning.json"))
ap.add_argument("--out", default=os.path.join(MK, "mods-slot", "metaknight-slot"))
ap.add_argument("--name", default="Brawl Meta Knight", help="m-ex fighter name (CSS / scene token). ACE already has a 'Meta Knight' (ext 41).")
a = ap.parse_args()
stage = os.path.join(MK, "build", "stage")
print("== 1. build_mk (preset %s)" % os.path.basename(a.preset))
subprocess.run([sys.executable, os.path.join(HERE, "build_mk.py"), "--preset", a.preset, "--out", stage], check=True, stdout=subprocess.DEVNULL)
print("== 2. verify")
if subprocess.run([sys.executable, os.path.join(HERE, "verify_mk.py"), "--mod", stage]).returncode != 0:
    sys.exit("verify failed - mod folder not updated")
print("== 3. mod folder", a.out)
f = os.path.join(a.out, "files"); os.makedirs(f, exist_ok=True)
shutil.copyfile(os.path.join(stage, "final", "PlBm.dat"), os.path.join(f, "PlBm.dat"))
log = subprocess.run([sys.executable, os.path.join(HERE, "mk_slot_files.py"), "--out", f, "--name", a.name], capture_output=True, text=True, check=True).stdout
os.makedirs(os.path.join(MK, "build"), exist_ok=True)
lg = json.loads(log)
json.dump(lg, open(os.path.join(MK, "build", "slot_files_log.json"), "w"), indent=1)
print("== 3b. MK's menu / UI art (build_mk_ui.py: CSS icon, CSPs, stock icons, results name strips)")
r = subprocess.run([sys.executable, os.path.join(HERE, "build_mk_ui.py"), "--files", f], capture_output=True, text=True)
if r.returncode != 0: sys.exit("build_mk_ui failed: " + r.stdout[-2000:] + r.stderr[-2000:])
ui = json.loads(r.stdout); json.dump(ui, open(os.path.join(MK, "build", "ui_log.json"), "w"), indent=1)
print(f"   icon joint {ui['icon']['joint']}; CSPs {ui['csp']['mode'].split(':')[0]}; stocks {ui['stock']['size']}; {len(ui['names']) - 1} name strips (GmRst.usd)")
r = subprocess.run([sys.executable, os.path.join(HERE, "ui", "verify_ui.py"), "--after", f], capture_output=True, text=True)
print("   " + (r.stdout.strip().splitlines() or ["verify_ui: no output"])[-1])
if r.returncode != 0: sys.exit("verify_ui failed:\n" + r.stdout[-3000:] + r.stderr[-2000:])
print("== 4. install_mk --scripts=mk --no-vis")
r = subprocess.run([sys.executable, os.path.join(MK, "model", "tools", "install_mk.py"), a.out, "--scripts=mk", "--no-vis"], capture_output=True, text=True)
if r.returncode != 0: sys.exit("install_mk failed:\n" + r.stdout[-2000:] + r.stderr[-2000:])
print("   " + r.stdout.strip().splitlines()[-1])
print("== 5. clip overrides + post-install check")
import install_mk as IM
C = json.load(open(os.path.join(stage, "CHANGES.json")))
w = IM.Writer(open(os.path.join(f, "PlBm.dat"), "rb").read())
fd = w.ar.public([s for s, _ in w.ar.publics if s.startswith("ftData")][0]); mt = w.u32(fd + 0xC)
syms = {}
for r_, c in C["clip_overrides"].items():
    o = mt + int(r_) * 0x18
    if c["symbol"] not in syms: syms[c["symbol"]] = w.cstr(c["symbol"])
    w.ptr(o, syms[c["symbol"]]); w.put(o + 4, c["offset"]); w.put(o + 8, c["size"])
w.save(os.path.join(f, "PlBm.dat"))
MR = json.load(open(os.path.join(MK, "anim", "out", "motion_rows.json")))
by_off = {(c["offset"], c["size"]): c for c in MR["clips"] + MR["extras"]}
w = IM.Writer(open(os.path.join(f, "PlBm.dat"), "rb").read())
bad = []
for m in C["moves"]:
    o = mt + m["melee_row"] * 0x18
    c = by_off.get((w.u32(o + 4), w.u32(o + 8)))
    if c is None or int(c["frames"]) != int(m["melee_anim_frames"]) or c["brawl_clip"] != m["clip"]:
        bad.append((m["move"], m["melee_row"], m["clip"], c and c["brawl_clip"], m["melee_anim_frames"], c and c["frames"]))
    if w.str_at(w.u32(o)) != (c or {}).get("symbol"): bad.append((m["move"], m["melee_row"], "row name != clip symbol"))
for r_, fl in (C.get("row_flags") or {}).items():       # Geno v2 rows: flags as built (Drill = animation-driven TransN)
    if w.u32(mt + int(r_) * 0x18 + 0x10) != int(fl, 16): bad.append(("row flags", r_, hex(w.u32(mt + int(r_) * 0x18 + 0x10)), fl))
if bad: sys.exit("post-install clip check failed: %s" % bad[:10])
print(f"   {len(C['clip_overrides'])} rows overridden; {len(C['moves'])} script rows play the clip they were built for")
print("== 6. geno.json, CHANGES, mod.json")
gv = C.get("geno") or {}
if gv.get("states"):
    print(f"   geno v{gv['version']}: {len(gv['states'])} states, specials {gv['specials']}")
    for st in gv["states"]: print(f"     {st['n']:2d} {st['motion']} {st['name']:16s} {st['behavior']:20s} row {st['subaction']} ({st['clip']})")
shutil.copyfile(os.path.join(stage, "CHANGES.json"), os.path.join(a.out, "CHANGES.json"))
shutil.copyfile(os.path.join(stage, "geno.json"), os.path.join(a.out, "geno.json"))
shutil.copyfile(a.preset, os.path.join(a.out, "TUNING.json"))
mod = {"id": "metaknight-slot", "name": "META KNIGHT (Brawl, own fighter slot)", "version": "0.3.0", "kind": "fighter",
       "description": "Adds '%s' as an m-ex fighter on the ACE disc (internal %d / external %d, a Kirby clone; replaces ACE's '%s' row). "
                      "Meta Knight's own model and clips (PlBm<cc>.dat, PlBmAJ.dat) with Brawl Meta Knight's numbers and scripts (PlBm.dat, %s); "
                      "Kirby's code runs his specials on the main exe. On the Geno exe, geno.json (v3) runs every special as Geno states on MK's own "
                      "clips (no Kirby special code): the glide, Mach Tornado, Drill Rush (Brawl's code), Shuttle Loop (root motion -> glide), "
                      "Dimensional Cape (stick-steered vanish, N/F/B slash or plain reappear), up/side taunts, the Wait3 idle, and the v1 "
                      "overlays (ftilt chain). Carries brawl-kirby-slot's shared tables too, so both mods can be on "
                      "together. Built by ports/halberd/tools/build_mk_slot.py."
                      % (a.name, lg["row"]["internal"], lg["row"]["external"], lg["row"]["replaces"]["name"], os.path.basename(a.preset)),
       "requires": [], "conflicts": []}
json.dump(mod, open(os.path.join(a.out, "mod.json"), "w"), indent=1)
# 7. effects (tools/build_mk_effects.py, the effects pass): MK's Brawl effect bank (EfBmData.dat) + MxDt row, the GFX /
#    sword-trail commands merged into the finished PlBm.dat rows and geno.json overlays, and the GetTrailData ftFunction.
#    Runs on the finished folder so whatever rows the steps above produced get their effects.
print("== 7. effects (build_mk_effects.py)")
r = subprocess.run([sys.executable, os.path.join(HERE, "build_mk_effects.py"), "--mod", a.out], capture_output=True, text=True)
if r.returncode != 0: sys.exit("build_mk_effects failed: " + r.stdout[-2000:] + r.stderr[-2000:])
print(r.stdout.rstrip())
# 8. sounds (tools/build_mk_sounds.py, the sound pass): MK's Brawl sound bank (audio/us/brawlmk.ssm + its smash2.sem
#    scripts) + MxDt ssm row, the SFX commands of every Brawl-clip row at Brawl's frames, the ftData voices.
#    Runs after effects, on the finished folder, matching rows by clip as effects does.
print("== 8. sounds (build_mk_sounds.py)")
r = subprocess.run([sys.executable, os.path.join(HERE, "build_mk_sounds.py"), "--mod", a.out], capture_output=True, text=True)
if r.returncode != 0: sys.exit("build_mk_sounds failed: " + r.stdout[-2000:] + r.stderr[-2000:])
print(r.stdout.rstrip())
# 9. model visuals (tools/build_mk_visuals.py): Brawl's eye clips as SetTexAnim eye states merged into every Brawl-clip row
#    (and its Geno overlay), matching rows by clip as effects / sounds do. The costume files' eye TObj matanim and the
#    results-screen motions come from install_mk (step 4).
print("== 9. visuals (build_mk_visuals.py)")
r = subprocess.run([sys.executable, os.path.join(HERE, "build_mk_visuals.py"), "--mod", a.out], capture_output=True, text=True)
if r.returncode != 0: sys.exit("build_mk_visuals failed: " + r.stdout[-2000:] + r.stderr[-2000:])
print(r.stdout.rstrip())
# 10. geno.json overlays -> words files. The Geno parser holds a geno.json in 2048 JSON nodes (geno_registry.c JDOC_NODES);
#     with every pass's commands inline MK's file outgrew it (2372 nodes) and the Geno exe rejected it whole. Each overlay's
#     words (effects + sounds + visuals, exactly as the passes left them) move to <mod>/geno/sub_<index>.txt and the entry
#     becomes {"index": n, "file": "geno/sub_<index>.txt"} (docs/geno.md 15.5: a words file is whitespace-separated words).
#     Last step, so every pass above still reads and writes inline words.
print("== 10. geno.json overlays -> words files")
def _nodes(x):
    if isinstance(x, dict): return 1 + sum(_nodes(v) for v in x.values())
    if isinstance(x, list): return 1 + sum(_nodes(v) for v in x)
    return 1
gp = os.path.join(a.out, "geno.json"); G = json.load(open(gp)); before = _nodes(G)
gd = os.path.join(a.out, "geno"); os.makedirs(gd, exist_ok=True)
for n in os.listdir(gd):
    if n.startswith("sub_") and n.endswith(".txt"): os.remove(os.path.join(gd, n))
moved = 0
for fi in G["fighters"]:
    for e in fi.get("subactions", []):
        if "words" not in e: continue
        ws = ["0x%08X" % (int(x, 16) if isinstance(x, str) else int(x)) for x in e["words"]]
        rel = "geno/sub_%03d.txt" % e["index"]
        NL = chr(10)
        with open(os.path.join(a.out, rel), "w", newline=NL) as fh:
            fh.write("# %s subaction %d overlay (build_mk_slot.py step 10)" % (fi.get("name", "?"), e["index"]) + NL)
            for k in range(0, len(ws), 8): fh.write(" ".join(ws[k:k + 8]) + NL)
        del e["words"]; e["file"] = rel; moved += 1
json.dump(G, open(gp, "w"), indent=1)
print(f"   {moved} overlays moved to geno/*.txt; geno.json {before} -> {_nodes(G)} JSON nodes (the Geno parser holds 2048)")
if _nodes(G) > 2048: sys.exit("geno.json still has more than 2048 JSON nodes")
for dp, dn, fn in sorted(os.walk(f)):
    for n in sorted(fn):
        b = open(os.path.join(dp, n), "rb").read(); rel = os.path.relpath(os.path.join(dp, n), f).replace(os.sep, "/")
        print(f"   {rel:22s} {len(b):>9,}  sha1 {hashlib.sha1(b).hexdigest()[:12]}")
print("   row", lg["row"], "css", lg["css"])
