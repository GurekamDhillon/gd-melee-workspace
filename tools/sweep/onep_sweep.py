#!/usr/bin/env python3
"""onep_sweep.py - load every 1P (Classic / Adventure / All-Star / bonus) stage and report what crashes.

    python tools/sweep/onep_sweep.py --exe _build/agents/alpha/melee-pc.exe --out _build/agents/alpha/onep
    python tools/sweep/onep_sweep.py --plan                  # list the runs, start nothing
    python tools/sweep/onep_sweep.py --match sora-int38      # only runs whose tag contains this

The scene launcher has no Classic / Adventure / All-Star mode, so each 1P stage is loaded directly as
a VS match on its internal stage kind (MELEE_SCENE "stage=int:N"): the stage's own ground code, models
and camera run, but not the 1P mode's script around it (Adventure's scroll triggers, the Master Hand
fight's HP bar, the bonus-stage goals). Break the Targets also runs in its own mode (mode=tt). Runs are
serial and wait for a free game slot (at most --max-games melee-pc on the machine). Each run: a pad
script waits, walks and jumps for ~20 s, logs gd.perf() frame times and ends itself with gd.quit().
A run passes on exit code 0 with the scene entered and no FATAL / PANIC / ALLOC_FAIL; a silent early
exit is rerun under cdbX86 for the stack. Results: <out>/results.md and <out>/results.json.
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
ISO_ACE = "C:/iso/SSBM ACE Build v2.0.0.iso"
CDB = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WindowsApps", "cdbX86.exe")

# GrKind (src/melee/gr/forward.h) -> what it is in 1P
ONEP = [
    (0x16, "Icicle Mountain (Adventure)"), (0x1F, "Mushroom Kingdom route (Adventure)"),
    (0x20, "Underground Maze (Adventure)"), (0x21, "Brinstar escape (Adventure)"),
    (0x22, "Big Blue route / F-Zero race (Adventure)"), (0x23, "Unk35 (Race to the Finish?)"),
    (0x25, "Final Destination (Master Hand / Crazy Hand)"), (0x26, "Snag the Trophies"),
    (0x27, "Pushon (Race to the Finish?)"),
] + [(k, "Break the Targets %s" % n) for k, n in enumerate(
    ["Mario", "C.Falcon", "Young Link", "DK", "Dr.Mario", "Falco", "Fox", "Ice Climbers", "Kirby",
     "Bowser", "Link", "Luigi", "Marth", "Mewtwo", "Ness", "Peach", "Pichu", "Pikachu", "Jigglypuff",
     "Samus", "Sheik", "Yoshi", "Zelda", "G&W", "Roy", "Ganondorf"], start=0x28)] + [
    (0x42, "All-Star rest area"), (0x43, "Home-Run Contest"),
    (0x44, "Figure1 (Adventure trophy battle)"), (0x45, "Figure2"), (0x46, "Figure3"),
]

PAD = r'''-- onep_sweep: wait, walk, jump, log frame times, quit.
local ms, n = 0, 0
gd.run(function()
  gd.wait_until(function() return gd.player(1) ~= nil end, 3000)
  gd.log("ONEP entered")
  gd.perf(1)
  for i = 1, 8 do
    gd.input(1, { x = (i % 2 == 0) and 80 or -80, y = 0 }, 60) gd.wait(60)
    gd.press(1, "X", 3) gd.wait(40)
    gd.perf(1)
    local p = gd.perf(60)
    for _, f in ipairs(p.frames or {}) do ms = ms + (f.total_ms or 0); n = n + 1 end
  end
  gd.log(string.format("ONEP frame %.2f ms avg over %d frames", n > 0 and ms / n or -1, n))
  gd.wait(10) gd.quit()
end)
'''


class Run:
    def __init__(self, tag, scene, what, mods):
        self.tag, self.scene, self.what, self.mods = tag, scene, what, mods
        self.result, self.detail, self.code, self.ms, self.stack = "", "", None, None, ""


def plan(fighters, mods_sora):
    runs = []
    for who, spec, mods in fighters:
        for kind, what in ONEP:
            runs.append(Run("%s-int%d" % (who, kind),
                            "mode=vs;p1=%s/cpu0/kind0;p2=fox/cpu1/kind0;stage=int:%d;time=0;items=off" % (spec, kind),
                            what, mods))
        runs.append(Run("%s-tt" % who, "mode=tt;p1=%s" % spec, "Break the Targets mode (own stage)", mods))
    return runs


def games_running():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-CimInstance Win32_Process -Filter \"Name='melee-pc.exe'\" | Measure-Object).Count"],
                         capture_output=True, text=True).stdout.strip()
    return int(out or "0")


def free_ram_gb():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB"],
                         capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 99.0


def sandbox(out, exe, tag):
    sb = os.path.join(out, "runs", tag)
    shutil.rmtree(sb, ignore_errors=True)
    os.makedirs(sb)
    for f in ("melee-pc.exe", "melee-pc.map"):
        shutil.copy2(os.path.join(os.path.dirname(exe), f), sb)
    for f in ("SDL3.dll", "webgpu_dawn.dll", "initial_pipeline_cache.db", "initial_pipeline_cache.core"):
        if os.path.exists(os.path.join(ROOT, "_build", f)):
            shutil.copy2(os.path.join(ROOT, "_build", f), sb)
    open(os.path.join(sb, "pad.lua"), "w").write(PAD)
    return sb


def env_for(run, sb, label):
    env = {k: v for k, v in os.environ.items() if not k.startswith("MELEE_")}
    env.update({"MELEE_SCENE": run.scene, "MELEE_VOLUME": "0", "MELEE_INPUT": "none",
                "MELEE_PAD_SCRIPT": os.path.join(sb, "pad.lua"), "MELEE_MODS_DIR": run.mods,
                "MELEE_RUN_LABEL": "%s - %s" % (label, run.tag), "MELEE_WINDOW_X": "0", "MELEE_WINDOW_Y": "0",
                "MELEE_WINDOW_W": "640", "MELEE_WINDOW_H": "480"})
    return env


def judge(run, sb, timed_out):
    text = open(os.path.join(sb, "melee-pc.log"), encoding="latin-1").read() if os.path.exists(
        os.path.join(sb, "melee-pc.log")) else ""
    bad = re.search(r"(FATAL|PANIC|ALLOC_FAIL)[^\n]*", text)
    m = re.search(r"ONEP frame ([-\d.]+) ms avg", text)
    run.ms = float(m.group(1)) if m else None
    entered = "ONEP entered" in text
    last_scene = (re.findall(r"scene: enter [^\n]*", text) or ["no scene"])[-1]
    if bad:
        return "CRASH", bad.group(0)[:200]
    if timed_out:
        return "HANG", "no exit within the time limit; last: " + last_scene[:120]
    if run.code != 0:
        return "EXIT", "exit code %s, no fault logged; last: %s" % (run.code, last_scene[:120])
    if not entered:
        return "NOMATCH", last_scene[:160]
    if not m:
        return "NOPERF", "quit without the frame-time line"
    return "PASS", ""


def cdb_stack(sb, env, secs):
    """Rerun under cdbX86 and return the faulting stack (first chance AV / fastfail)."""
    script = os.path.join(sb, "cdb.txt")
    open(script, "w").write('sxe -c "kb 40; q" c0000409\nsxe -c "kb 40; q" av\nsxd ibp\ng\nq\n')
    try:
        p = subprocess.run([CDB, "-cf", script, os.path.join(sb, "melee-pc.exe"), "--iso", ISO_ACE], cwd=sb, env=env,
                           capture_output=True, text=True, timeout=secs)
        out = p.stdout
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("latin-1") if isinstance(e.stdout, bytes) else (e.stdout or "")
    frames = re.findall(r"melee_pc\+0x[0-9a-f]+", out)
    return " ".join(frames[:12]) or out[-400:]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--exe", default=os.path.join(ROOT, "_build", "agents", "alpha", "melee-pc.exe"))
    ap.add_argument("--out", default=os.path.join(ROOT, "_build", "agents", "alpha", "onep"))
    ap.add_argument("--sora-mods", default=os.path.join(ROOT, "_build", "agents", "alpha", "sora", "mods-gd-latest"))
    ap.add_argument("--secs", type=int, default=75, help="per-run time limit")
    ap.add_argument("--max-games", type=int, default=2)
    ap.add_argument("--label", default="alpha / 1P sweep")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--match", default="")
    a = ap.parse_args()
    exe, out = os.path.abspath(a.exe), os.path.abspath(a.out)
    nomods = os.path.join(ROOT, "_build", "nomods")
    os.makedirs(nomods, exist_ok=True)
    runs = plan([("fox", "fox", nomods), ("sora", "ultimatesora", os.path.abspath(a.sora_mods))], a.sora_mods)
    if a.match:
        runs = [r for r in runs if a.match in r.tag]
    if a.plan:
        for r in runs:
            print("%-14s %-44s %s" % (r.tag, r.what, r.scene))
        return 0
    os.makedirs(out, exist_ok=True)
    for i, r in enumerate(runs):
        while games_running() >= a.max_games or free_ram_gb() < 3.0:
            time.sleep(5)
        sb = sandbox(out, exe, r.tag)
        env = env_for(r, sb, a.label)
        p = subprocess.Popen([os.path.join(sb, "melee-pc.exe"), "--iso", ISO_ACE], cwd=sb, env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        timed_out = False
        try:
            r.code = p.wait(timeout=a.secs)
        except subprocess.TimeoutExpired:
            timed_out = True
            p.kill()
            p.wait()
        r.result, r.detail = judge(r, sb, timed_out)
        if r.result in ("EXIT", "HANG") and os.path.exists(CDB):
            while games_running() >= a.max_games:
                time.sleep(5)
            r.stack = cdb_stack(sb, env, a.secs)
        print("[%d/%d] %-14s %-7s %s %s" % (i + 1, len(runs), r.tag, r.result,
                                           "%.2f ms" % r.ms if r.ms is not None else "", r.detail), flush=True)
    with open(os.path.join(out, "results.json"), "w") as f:
        json.dump([vars(r) for r in runs], f, indent=1)
    with open(os.path.join(out, "results.md"), "w") as f:
        f.write("| run | stage | result | frame ms | detail |\n|---|---|---|---|---|\n")
        for r in runs:
            f.write("| %s | %s | %s | %s | %s %s |\n" % (r.tag, r.what, r.result,
                                                      "%.2f" % r.ms if r.ms is not None else "",
                                                      r.detail.replace("|", "/"), ("stack: " + r.stack) if r.stack else ""))
    print("results: %s" % os.path.join(out, "results.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
