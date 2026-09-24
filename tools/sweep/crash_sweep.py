#!/usr/bin/env python3
"""crash_sweep.py - load every stage and every fighter on each disc and report what crashes.

    python tools/sweep/crash_sweep.py --exe _build/agents/beta/melee-pc.exe --out _build/agents/beta/sweep
    python tools/sweep/crash_sweep.py --discs vanilla --only stages --parallel 4
    python tools/sweep/crash_sweep.py --plan            # list the runs, start nothing

One VS match per run, launched with MELEE_SCENE (no menus): each STAGE with two level-9 CPUs
(Fox, Falco), each group of four FIGHTERS as level-9 CPUs on Battlefield. A run passes when the
match scene is entered, frames keep coming for the whole run, the process is still alive at the
end and the log has no FATAL / crash log. Counts of m-ex fighters and stages come from each
disc's own boot log (a short probe run first). Results: <out>/results.md (a table per disc) and
<out>/results.json; each run keeps its sandbox (log, crash log) under <out>/runs/.

Windows are visible (tiled 2x2 on the primary screen), labelled, and muted (MELEE_VOLUME=0).
Discs come from .env (GW_ISO_VANILLA / GW_ISO_AKANEIA / GW_ISO_ACE).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

VANILLA_STAGES = [  # (name, StKind) - gw_sl_stage_names in gw_runtime.c, one name per stage
    ("fountain", 2), ("stadium", 3), ("castle", 4), ("kongo", 5), ("brinstar", 6), ("corneria", 7),
    ("yoshistory", 8), ("onett", 9), ("mutecity", 10), ("rcruise", 11), ("kingdom2", 12),
    ("greatbay", 13), ("temple", 14), ("kraid", 15), ("yoshiisland", 16), ("greens", 17),
    ("fourside", 18), ("inishie1", 19), ("inishie2", 20), ("akaneia", 21), ("venom", 22),
    ("pokefloats", 23), ("bigblue", 24), ("icemt", 25), ("icetop", 26), ("flatzone", 27),
    ("dreamland64", 28), ("oldyoshi", 29), ("oldkongo", 30), ("battlefield", 31), ("fd", 32),
]
VANILLA_FIGHTERS = list(range(0, 26))  # CharacterKind 0..25, the playable cast
MEX_CK0 = 34                            # ChKind_Mex0: added fighters are contiguous from here
MEX_EXT0 = 288                          # added stages: external StKind 288 + k


def env_isos():
    isos = {}
    try:
        for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
            m = re.match(r'\s*(?:export\s+)?GW_ISO_(\w+)\s*=\s*"?([^"\n]*)"?', line)
            if m:
                isos[m.group(1).lower()] = m.group(2)
    except OSError:
        pass
    return isos


class Run:
    def __init__(self, disc, kind, tag, scene, secs, what):
        self.disc, self.kind, self.tag, self.scene, self.secs, self.what = disc, kind, tag, scene, secs, what
        self.result, self.detail, self.proc, self.t0, self.sandbox = None, "", None, 0.0, ""


def prepare_sandbox(out, exe, tag):
    sb = os.path.join(out, "runs", tag)
    os.makedirs(sb, exist_ok=True)
    exedir = os.path.dirname(exe)
    for f in ("melee-pc.exe", "melee-pc.map"):
        if os.path.exists(os.path.join(exedir, f)):
            shutil.copy2(os.path.join(exedir, f), sb)
    for f in ("SDL3.dll", "webgpu_dawn.dll", "initial_pipeline_cache.db", "initial_pipeline_cache.core"):
        src = os.path.join(ROOT, "_build", f)
        if os.path.exists(src):
            shutil.copy2(src, sb)
    for f in ("melee-pc.log",):
        try:
            os.remove(os.path.join(sb, f))
        except OSError:
            pass
    shutil.rmtree(os.path.join(sb, "crashlogs"), ignore_errors=True)
    return sb


def start(run, out, exe, iso, slot, label):
    run.sandbox = prepare_sandbox(out, exe, run.tag)
    env = {k: v for k, v in os.environ.items() if not k.startswith("MELEE_")}
    x, y = (slot % 2) * 660, (slot // 2) * 520
    env.update({
        "MELEE_SCENE": run.scene, "MELEE_VOLUME": "0", "MELEE_INPUT": "keyboard",
        "MELEE_PAD_IGNORE_ADAPTER": "1", "SDL_JOYSTICK_HIDAPI_GAMECUBE": "0",
        "MELEE_RUN_LABEL": "%s - %s" % (label, run.tag), "MELEE_MODS_DIR": os.path.join(ROOT, "_build", "nomods"),
        "MELEE_WINDOW_X": str(x), "MELEE_WINDOW_Y": str(y + 30), "MELEE_WINDOW_W": "640", "MELEE_WINDOW_H": "480",
    })
    os.makedirs(env["MELEE_MODS_DIR"], exist_ok=True)
    run.proc = subprocess.Popen([os.path.join(run.sandbox, "melee-pc.exe"), "--iso", iso], cwd=run.sandbox,
                                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run.t0 = time.time()


def judge(run):
    log = os.path.join(run.sandbox, "melee-pc.log")
    text = open(log, encoding="latin-1").read() if os.path.exists(log) else ""
    crashes = os.listdir(os.path.join(run.sandbox, "crashlogs")) if os.path.isdir(os.path.join(run.sandbox, "crashlogs")) else []
    alive = run.proc.poll() is None
    fatal = re.search(r"FATAL[^\n]*", text)
    entered = re.search(r"scene: enter mode=GM_VS\(2\)[^\n]*screen=GS_VS\(2\)", text)
    beats = [int(m) for m in re.findall(r"heartbeat retrace=(\d+)", text)]
    after = text[entered.start():] if entered else ""
    beats_after = [int(m) for m in re.findall(r"heartbeat retrace=(\d+)", after)]
    progressed = len(beats_after) >= 2 and beats_after[-1] - beats_after[0] >= 600
    if fatal or crashes:
        line = fatal.group(0) if fatal else "crash log " + crashes[0]
        return "CRASH", line[:160]
    if not alive:
        return "EXIT", "process exited early (code %s), no fault logged" % run.proc.returncode
    if not entered:
        last = re.findall(r"scene: enter [^\n]*", text)
        return "NOMATCH", (last[-1] if last else "no scene entered")[:160]
    if not progressed:
        return "HANG", "frames stopped after the match began (last heartbeat %s)" % (beats[-1] if beats else "none")
    return "PASS", ""


def probe_counts(out, exe, iso, disc, label):
    run = Run(disc, "probe", "%s-probe" % disc, "mode=vs;p1=fox/cpu9;p2=falco/cpu9;stage=battlefield;time=0", 16, "probe")
    start(run, out, exe, iso, 0, label)
    time.sleep(run.secs)
    run.proc.kill()
    run.proc.wait()
    text = open(os.path.join(run.sandbox, "melee-pc.log"), encoding="latin-1").read()
    fk = re.search(r"m-ex fighter kinds from MxDt\.dat \(kinds (\d+)\.\.(\d+)\)", text)
    st = re.search(r"stage tables ready: (\d+) internal, (\d+) external", text)
    fighters = int(fk.group(2)) - int(fk.group(1)) + 1 if fk else 0
    externals = int(st.group(2)) if st else 0
    return fighters, externals


def plan(disc, fighters, externals, only, secs, items="0"):
    # items: the scene grammar's item frequency (0 = the old default here; 4 = very high). A sweep
    # with items records the item models' pipelines, tagged MUST_DRAW, for the pipeline seed.
    runs = []
    if only in ("all", "stages"):
        stages = [(n, "%s" % n) for n, _ in VANILLA_STAGES] + [("ext%d" % e, "ext:%d" % e) for e in range(MEX_EXT0, externals)]
        for name, ref in stages:
            runs.append(Run(disc, "stage", "%s-st-%s" % (disc, name),
                            "mode=vs;p1=fox/cpu9;p2=falco/cpu9;stage=%s;time=0;items=%s" % (ref, items), secs, name))
    if only in ("all", "fighters"):
        cks = VANILLA_FIGHTERS + list(range(MEX_CK0, MEX_CK0 + fighters))
        for g in range(0, len(cks), 4):
            grp = cks[g:g + 4]
            ps = ";".join("p%d=ck:%d/cpu9" % (i + 1, c) for i, c in enumerate(grp))
            runs.append(Run(disc, "fighters", "%s-ck%d-%d" % (disc, grp[0], grp[-1]),
                            "mode=vs;%s;stage=battlefield;time=0;items=%s" % (ps, items), secs + 5,
                            ",".join(str(c) for c in grp)))
    return runs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--exe", default=os.path.join(ROOT, "_build", "melee-pc.exe"))
    ap.add_argument("--out", default=os.path.join(ROOT, "_build", "sweep"))
    ap.add_argument("--discs", default="vanilla,ace,akaneia")
    ap.add_argument("--only", choices=("all", "stages", "fighters"), default="all")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--secs", type=int, default=24, help="seconds per stage run (fighter runs +5)")
    ap.add_argument("--items", default="0", help="item frequency per match (0..4, or off)")
    ap.add_argument("--label", default="crash sweep")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--match", default="", help="only runs whose tag contains this")
    a = ap.parse_args()
    exe = os.path.abspath(a.exe)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    isos = env_isos()
    all_runs = []
    for disc in a.discs.split(","):
        iso = isos.get(disc)
        if not iso:
            print("no ISO for %s in .env" % disc)
            return 2
        fighters, externals = (0, 0) if a.plan else probe_counts(out, exe, iso, disc, a.label)
        runs = plan(disc, fighters, externals, a.only, a.secs, a.items)
        if a.match:
            runs = [r for r in runs if a.match in r.tag]
        print("%s: %d m-ex fighters, %d external stages -> %d runs" % (disc, fighters, externals, len(runs)))
        for r in runs:
            r.iso = iso
        all_runs += runs
    if a.plan:
        for r in all_runs:
            print("%-28s %s" % (r.tag, r.scene))
        return 0
    queue, active, done = list(all_runs), {}, []
    t_start = time.time()
    while queue or active:
        for slot in range(a.parallel):
            if slot not in active and queue:
                r = queue.pop(0)
                start(r, out, exe, r.iso, slot, a.label)
                active[slot] = r
        time.sleep(1)
        for slot, r in list(active.items()):
            if r.proc.poll() is not None or time.time() - r.t0 >= r.secs:
                time.sleep(0.5)
                r.result, r.detail = judge(r)
                if r.proc.poll() is None:
                    r.proc.kill()
                    r.proc.wait()
                del active[slot]
                done.append(r)
                print("[%3d/%3d] %-7s %-28s %s" % (len(done), len(all_runs), r.result, r.tag, r.detail))
    json.dump([{"disc": r.disc, "kind": r.kind, "tag": r.tag, "what": r.what, "scene": r.scene,
                "result": r.result, "detail": r.detail} for r in done],
              open(os.path.join(out, "results.json"), "w"), indent=1)
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("# Crash sweep - %s\n\nexe `%s`, %d runs in %.0f min\n" %
                (time.strftime("%Y-%m-%d %H:%M"), exe, len(done), (time.time() - t_start) / 60))
        for disc in a.discs.split(","):
            rows = [r for r in done if r.disc == disc]
            bad = [r for r in rows if r.result != "PASS"]
            f.write("\n## %s - %d/%d pass\n\n| run | what | result | detail |\n|---|---|---|---|\n" %
                    (disc, len(rows) - len(bad), len(rows)))
            for r in sorted(rows, key=lambda r: (r.result == "PASS", r.tag)):
                f.write("| %s | %s | %s | %s |\n" % (r.tag, r.what, r.result, r.detail.replace("|", "/")))
    fails = [r for r in done if r.result != "PASS"]
    print("done: %d/%d pass -> %s" % (len(done) - len(fails), len(done), os.path.join(out, "results.md")))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
