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

Windows are visible (tiled 2x2 on the primary screen, or on a second monitor with --monitor2),
labelled, and muted (MELEE_VOLUME=0).

Runs go in turbo by default: an empty pad script (tools/sweep/empty_pad.lua, which drives no channel,
so the CPUs still play) lets MELEE_TURBO=1 be accepted, and --secs counts GAME seconds (frames / 60),
reached far sooner on the wall clock. --realtime runs at 60 fps with the old wall-clock --secs.
--skip TAG,TAG and --resume results.json leave runs out (resume keeps the earlier rows in the new
results); --max-games N holds each launch while N or more melee-pc.exe are already running.
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
MAIN = os.environ.get("GW_ROOT", ROOT)  # the main checkout: .env, SDL3.dll and friends live there, not in a worktree

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
EMPTY_PAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "empty_pad.lua")
MON2_ORIGIN = (-1080, -360)             # second monitor, left of the primary
MEX_EXT0 = 288                          # added stages: external StKind 288 + k
PROGRESS_GRACE_SECONDS = 30.0            # heartbeats normally arrive every two seconds


def env_isos():
    isos = {}
    try:
        for line in open(os.path.join(MAIN, ".env"), encoding="utf-8"):
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
        self.progress_values = None
        self.progress_times = None
        self.progress_stalled = False


def prepare_sandbox(out, exe, tag):
    sb = os.path.join(out, "runs", tag)
    os.makedirs(sb, exist_ok=True)
    exedir = os.path.dirname(exe)
    for f in ("melee-pc.exe", "melee-pc.map"):
        if os.path.exists(os.path.join(exedir, f)):
            shutil.copy2(os.path.join(exedir, f), sb)
    for f in ("SDL3.dll", "webgpu_dawn.dll", "initial_pipeline_cache.db", "initial_pipeline_cache.core"):
        src = os.path.join(MAIN, "_build", f)
        if os.path.exists(src):
            shutil.copy2(src, sb)
    if os.path.isdir(os.path.join(exedir, "ui")) and not os.path.isdir(os.path.join(sb, "ui")):
        shutil.copytree(os.path.join(exedir, "ui"), os.path.join(sb, "ui"))
    for f in ("melee-pc.log",):
        try:
            os.remove(os.path.join(sb, f))
        except OSError:
            pass
    shutil.rmtree(os.path.join(sb, "crashlogs"), ignore_errors=True)
    return sb


def running_games():
    """How many melee-pc.exe processes run on this machine, whoever started them."""
    o = subprocess.run(["tasklist", "/FI", "IMAGENAME eq melee-pc.exe", "/NH"], capture_output=True, text=True).stdout
    return o.count("melee-pc.exe")


def wait_for_slot(max_games, poll=5.0):
    """Hold while max_games or more games run (0 = no gate)."""
    while max_games > 0 and running_games() >= max_games:
        time.sleep(poll)


def window_geometry(slot, monitor2):
    if monitor2:
        w, h = 520, 390
        return MON2_ORIGIN[0] + (slot % 2) * (w + 20), MON2_ORIGIN[1] + (slot // 2) * (h + 15) + 30, w, h
    return (slot % 2) * 660, (slot // 2) * 520 + 30, 640, 480


def start(run, out, exe, iso, slot, label, turbo=False, monitor2=False):
    run.sandbox = prepare_sandbox(out, exe, run.tag)
    env = {k: v for k, v in os.environ.items() if not k.startswith("MELEE_")}
    x, y, w, h = window_geometry(slot, monitor2)
    if turbo:
        env.update({"MELEE_PAD_SCRIPT": EMPTY_PAD, "MELEE_TURBO": "1", "MELEE_FPS": "u"})
    env.update({
        "MELEE_SCENE": run.scene, "MELEE_VOLUME": "0", "MELEE_INPUT": "none",
        "MELEE_PAD_IGNORE_ADAPTER": "1", "SDL_JOYSTICK_HIDAPI_GAMECUBE": "0",
        "MELEE_RUN_LABEL": "%s - %s" % (label, run.tag), "MELEE_MODS_DIR": os.path.join(MAIN, "_build", "nomods"),
        "MELEE_WINDOW_X": str(x), "MELEE_WINDOW_Y": str(y), "MELEE_WINDOW_W": str(w), "MELEE_WINDOW_H": str(h),
    })
    os.makedirs(env["MELEE_MODS_DIR"], exist_ok=True)
    run.proc = subprocess.Popen([os.path.join(run.sandbox, "melee-pc.exe"), "--iso", iso], cwd=run.sandbox,
                                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run.t0 = time.time()


def sample_progress(run, now=None):
    """Observe liveness throughout the run; an old burst of frames is not evidence."""
    now = time.monotonic() if now is None else now
    log = os.path.join(run.sandbox, "melee-pc.log")
    try:
        with open(log, encoding="latin-1") as f:
            text = f.read()
    except OSError:
        return
    entered = re.search(r"scene: enter mode=GM_VS\(2\)[^\n]*screen=GS_VS\(2\)", text)
    if not entered:
        return
    beats = re.findall(r"heartbeat retrace=(\d+) presented=(\d+)", text[entered.start():])
    if not beats:
        return
    values = tuple(map(int, beats[-1]))
    if run.progress_values is None:
        run.progress_values = values
        run.progress_times = [now, now]
        return
    for i, value in enumerate(values):
        # Check the gap before accepting new progress, so a late recovery cannot
        # erase an extended freeze earlier in the run.
        if now - run.progress_times[i] > PROGRESS_GRACE_SECONDS:
            run.progress_stalled = True
        if value > run.progress_values[i]:
            run.progress_times[i] = now
    run.progress_values = values


def frames_since_entry(run):
    """Logic frames since the match scene was entered (from the heartbeat), or 0."""
    try:
        with open(os.path.join(run.sandbox, "melee-pc.log"), encoding="latin-1") as f:
            text = f.read()
    except OSError:
        return 0
    entered = re.search(r"scene: enter mode=GM_VS\(2\)[^\n]*screen=GS_VS\(2\)", text)
    if not entered:
        return 0
    beats = [int(m) for m in re.findall(r"heartbeat retrace=(\d+)", text[entered.start():])]
    return beats[-1] - beats[0] if len(beats) >= 2 else 0


def run_finished(run, turbo, now=None, frames=None):
    """Turbo: --secs is game seconds, so the run is over after secs*60 frames (or at a wall-clock cap
    of 4x --secs, at least 60 s). Realtime: --secs of wall clock."""
    now = time.time() if now is None else now
    if not turbo:
        return now - run.t0 >= run.secs
    if frames is None:
        frames = frames_since_entry(run)
    return frames >= run.secs * 60 or now - run.t0 >= max(60.0, run.secs * 4)


def judge(run):
    log = os.path.join(run.sandbox, "melee-pc.log")
    text = ""
    if os.path.exists(log):
        with open(log, encoding="latin-1") as f:
            text = f.read()
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
    if not progressed or run.progress_values is None or run.progress_stalled or run.progress_values[1] == 0:
        return "HANG", "logic/render progress missing or stalled during the run (last heartbeat %s)" % (beats[-1] if beats else "none")
    return "PASS", ""


def probe_counts(out, exe, iso, disc, label, monitor2=False):
    run = Run(disc, "probe", "%s-probe" % disc, "mode=vs;p1=fox/cpu9;p2=falco/cpu9;stage=battlefield;time=0", 16, "probe")
    start(run, out, exe, iso, 0, label, monitor2=monitor2)
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
    ap.add_argument("--exe", default=os.path.join(MAIN, "_build", "melee-pc.exe"))
    ap.add_argument("--out", default=os.path.join(MAIN, "_build", "sweep"))
    ap.add_argument("--discs", default="vanilla,ace,akaneia")
    ap.add_argument("--only", choices=("all", "stages", "fighters"), default="all")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--secs", type=int, default=24, help="seconds per stage run (fighter runs +5)")
    ap.add_argument("--items", default="0", help="item frequency per match (0..4, or off)")
    ap.add_argument("--label", default="crash sweep")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--match", default="", help="only runs whose tag contains this")
    ap.add_argument("--realtime", action="store_true",
                    help="60 fps, wall-clock --secs (default: turbo, --secs in game seconds)")
    ap.add_argument("--skip", default="", help="comma-separated run tags to leave out")
    ap.add_argument("--resume", default="", help="an earlier results.json: leave out its runs, keep its rows")
    ap.add_argument("--max-games", type=int, default=3,
                    help="hold each launch while this many melee-pc.exe run (0 = no gate)")
    ap.add_argument("--monitor2", action="store_true", help="tile the windows on the second monitor")
    a = ap.parse_args()
    exe = os.path.abspath(a.exe)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    isos = env_isos()
    turbo = not a.realtime
    skip = set(t for t in a.skip.split(",") if t)
    carried = []
    if a.resume:
        with open(a.resume, encoding="utf-8") as f:
            carried = json.load(f)
        skip |= set(row["tag"] for row in carried)
    all_runs = []
    for disc in a.discs.split(","):
        iso = isos.get(disc)
        if not iso:
            print("no ISO for %s in .env" % disc)
            return 2
        if not a.plan:
            wait_for_slot(a.max_games)
        fighters, externals = (0, 0) if a.plan else probe_counts(out, exe, iso, disc, a.label, a.monitor2)
        runs = plan(disc, fighters, externals, a.only, a.secs, a.items)
        if a.match:
            runs = [r for r in runs if a.match in r.tag]
        runs = [r for r in runs if r.tag not in skip]
        print("%s: %d m-ex fighters, %d external stages -> %d runs" % (disc, fighters, externals, len(runs)))
        for r in runs:
            r.iso = iso
        all_runs += runs
    if a.plan:
        for r in all_runs:
            print("%-28s %s" % (r.tag, r.scene))
        return 0
    queue, active, done = list(all_runs), {}, []
    for row in carried:
        c = Run(row["disc"], row["kind"], row["tag"], row["scene"], 0, row["what"])
        c.result, c.detail = row["result"], row["detail"]
        done.append(c)
    t_start = time.time()
    while queue or active:
        for slot in range(a.parallel):
            if slot not in active and queue and (a.max_games <= 0 or running_games() < a.max_games):
                r = queue.pop(0)
                start(r, out, exe, r.iso, slot, a.label, turbo, a.monitor2)
                active[slot] = r
        time.sleep(1)
        for slot, r in list(active.items()):
            sample_progress(r)
            if r.proc.poll() is not None or run_finished(r, turbo):
                time.sleep(0.5)
                r.result, r.detail = judge(r)
                if r.proc.poll() is None:
                    r.proc.kill()
                    r.proc.wait()
                del active[slot]
                done.append(r)
                print("[%3d/%3d] %-7s %-28s %s" % (len(done), len(all_runs) + len(carried), r.result, r.tag, r.detail))
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
