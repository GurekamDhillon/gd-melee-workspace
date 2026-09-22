#!/usr/bin/env python3
"""Drive every item of the frontend's menu tree to its destination and back.

    python tools/port/fe_menu_sweep.py --disc vanilla --exe-dir _build/agents/menus
    python tools/port/fe_menu_sweep.py --disc ace --only "VS/"          # a subset
    python tools/port/fe_menu_sweep.py --disc vanilla --list            # print the plan

For each item it writes a pad script (_build/tmp/fe_sweep/<disc>/<n>.txt) that boots to the
main menu (MELEE_SCENE=mode=menu), walks the tree to the item the way a player would, presses
A, waits, then presses B (up to three times) - and runs it through _build/selftest.ps1. Then it
reads the run's log and checks:

  game mode   "scene: enter mode=<GM_...>"  and, after B, the menus reopen on that item
  submenu     "frontend: menu <title>"      opened
  native      mnmain opened (kind, selection); B returns through mn_80229894 and the menus
              reopen on the item
  MATCH SETUP the setup screen shows; B goes back to VS with the cursor on MELEE

The navigation model is the frontend's own (gmfrontend_menus.inc): hubs cycle through tiles in
rank order (the hero first, then vanilla order) with Down; lists go top to bottom; every menu
opens on its first visible item. Locked items (All-Star, Sound Test) are assumed visible, which
is true of the shared unlocked card selftest.ps1 seeds each sandbox with - a locked card shows
up as a failed check for those two items, and the run log says "N of M items shown".
"""
import argparse
import os
import re
import subprocess
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (kind, title, style, hero_sel, back(kind, sel) or None, items)
# item: (sel, label, act, arg)   act: sub / mode / native / setup
MENUS = {
    0: ("MAIN MENU", "hub", 1, None, [
        (0, "SOLO", "sub", 1), (1, "VERSUS", "sub", 2), (2, "COLLECTION", "sub", 3),
        (3, "OPTIONS", "sub", 4), (4, "DATA", "sub", 5)]),
    1: ("SOLO", "hub", 0, (0, 0), [
        (0, "REGULAR MATCH", "sub", 6), (1, "EVENT MATCH", "native", None),
        (3, "STADIUM", "sub", 9), (4, "TRAINING", "mode", "GM_TRAINING")]),
    6: ("REGULAR MATCH", "hub", 0, (1, 0), [
        (0, "CLASSIC", "mode", "GM_CLASSIC"), (1, "ADVENTURE", "mode", "GM_ADVENTURE"),
        (2, "ALL-STAR", "mode", "GM_ALLSTAR")]),
    9: ("STADIUM", "hub", 0, (1, 3), [
        (0, "TARGET TEST", "mode", "GM_TARGET_TEST"),
        (1, "HOME-RUN CONTEST", "mode", "GM_HOME_RUN_CONTEST"),
        (2, "MULTI-MAN MELEE", "sub", 33)]),
    33: ("MULTI-MAN MELEE", "list", 0, (9, 2), [
        (0, "10-MAN MELEE", "mode", "GM_10MAN_VS"), (1, "100-MAN MELEE", "mode", "GM_100MAN_VS"),
        (2, "3-MINUTE MELEE", "mode", "GM_3MIN_VS"), (3, "15-MINUTE MELEE", "mode", "GM_15MIN_VS"),
        (4, "ENDLESS MELEE", "mode", "GM_ENDLESS_VS"), (5, "CRUEL MELEE", "mode", "GM_CRUEL_VS")]),
    2: ("VERSUS", "hub", 0, (0, 1), [
        (0, "MELEE", "setup", "GM_VS"), (1, "TOURNAMENT", "mode", "GM_TOURNAMENT"),
        (2, "SPECIAL MELEE", "sub", 12), (3, "RULES", "native", None),
        (4, "NAME ENTRY", "native", None)]),
    12: ("SPECIAL MELEE", "list", 0, (2, 2), [
        (0, "CAMERA MODE", "mode", "GM_CAMERA_MODE"), (1, "STAMINA MODE", "mode", "GM_STAMINA_VS"),
        (2, "SUPER SUDDEN DEATH", "mode", "GM_SUPER_SUDDEN_DEATH_VS"),
        (3, "GIANT MELEE", "mode", "GM_GIANT_VS"), (4, "TINY MELEE", "mode", "GM_TINY_VS"),
        (5, "INVISIBLE MELEE", "mode", "GM_INVISIBLE_VS"),
        (6, "FIXED-CAMERA MODE", "mode", "GM_CAMERA_VS"),
        (7, "SINGLE-BUTTON MODE", "mode", "GM_SINGLE_BUTTON_VS"),
        (8, "LIGHTNING MELEE", "mode", "GM_LIGHTNING_VS"), (9, "SLO-MO MELEE", "mode", "GM_SLOMO_VS")]),
    3: ("COLLECTION", "hub", 3, (0, 2), [
        (0, "GALLERY", "mode", "GM_TOY_GALLERY"), (1, "LOTTERY", "mode", "GM_TOY_LOTTERY"),
        (3, "COLLECTION", "mode", "GM_TOY_COLLECTION")]),
    4: ("OPTIONS", "list", 0, (0, 3), [
        (0, "RUMBLE", "native", None), (1, "SOUND", "native", None),
        (2, "SCREEN DISPLAY", "native", None), (4, "LANGUAGE", "native", None),
        (5, "ERASE DATA", "native", None)]),
    5: ("DATA", "hub", 3, (0, 4), [
        (0, "SNAPSHOTS", "native", None), (1, "MOVIES", "native", None),
        (2, "SOUND TEST", "native", None), (3, "RECORDS", "sub", 28),
        (4, "SPECIAL MESSAGES", "native", None)]),
    28: ("RECORDS", "list", 0, (5, 3), [
        (0, "VS. RECORDS", "native", None), (1, "BONUS RECORDS", "native", None),
        (2, "MISC. RECORDS", "native", None)]),
}


def ranks(kind):
    title, style, hero, back, items = MENUS[kind]
    if style == "list":
        return list(range(len(items)))
    order = [i for i, it in enumerate(items) if it[0] == hero] or [0]
    order += [i for i in range(len(items)) if i != order[0]]
    r = [0] * len(items)
    for rank, i in enumerate(order):
        r[i] = rank
    return r


def downs(kind, frm, to):
    r = ranks(kind)
    return (r[to] - r[frm]) % len(r)


def path_to(kind):
    """[(menu kind, item index)] from Main to open `kind`."""
    if kind == 0:
        return []
    for k, m in MENUS.items():
        for i, it in enumerate(m[4]):
            if it[2] == "sub" and it[3] == kind:
                return path_to(k) + [(k, i)]
    raise KeyError(kind)


def press(lines, button, hold=6, gap=16):
    lines.append("%d %s 0 0" % (hold, button))
    lines.append("%d 0000 0 0" % gap)


def pad_for(kind, idx, backs):
    lines = ["# fe_menu_sweep: %s / %s" % (MENUS[kind][0], MENUS[kind][4][idx][1]),
             "300 0000 0 0"]
    for k, i in path_to(kind) + [(kind, idx)]:
        for _ in range(downs(k, 0, i)):
            press(lines, "0004")
        press(lines, "0100", gap=110 if (k, i) != (kind, idx) else 400)
    for _ in range(backs):
        press(lines, "0200", gap=200)
    lines.append("200 0000 0 0")
    return "\n".join(lines) + "\n"


def plan():
    out = []
    for kind, m in MENUS.items():
        for i, it in enumerate(m[4]):
            out.append((kind, i))
    return out


def check(kind, idx, log):
    title, style, hero, back, items = MENUS[kind]
    sel, label, act, arg = items[idx]
    esc = re.escape
    reopened = re.search(r'frontend: menu %s \(kind %d.*cursor on "%s"' % (esc(title), kind, esc(label)),
                         log.split('confirm "%s"' % label, 1)[-1]) is not None
    if act == "mode":
        entered = re.search(r"scene: enter mode=%s\(" % arg, log) is not None
        return entered and reopened, "entered %s: %s, back on the item: %s" % (arg, entered, reopened)
    if act == "sub":
        sub = MENUS[arg][0]
        opened = re.search(r"frontend: menu %s \(kind %d" % (esc(sub), arg), log) is not None
        return opened and reopened, "opened %s: %s, back on the item: %s" % (sub, opened, reopened)
    if act == "native":
        opened = ("frontend opens native screen kind %d selection %d" % (kind, sel)) in log
        returned = ("native screen backs out to (kind %d, sel %d)" % (kind, sel)) in log
        return opened and returned and reopened, \
            "native opened: %s, backed out: %s, back on the item: %s" % (opened, returned, reopened)
    if act == "setup":
        shown = "frontend: -> MATCH SETUP" in log and "scene: enter mode=GM_FRONTEND" in log.split("-> MATCH SETUP", 1)[-1]
        return shown and reopened, "MATCH SETUP: %s, back on the item: %s" % (shown, reopened)
    return False, "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", default="vanilla")
    ap.add_argument("--exe-dir", default=os.path.join(ROOT, "_build", "agents", "menus"))
    ap.add_argument("--only", default="", help="substring of 'MENU TITLE/ITEM LABEL'")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--seconds", type=int, default=0)
    a = ap.parse_args()
    todo = [(k, i) for k, i in plan()
            if a.only in "%s/%s" % (MENUS[k][0], MENUS[k][4][i][1])]
    outdir = os.path.join(ROOT, "_build", "tmp", "fe_sweep", a.disc)
    os.makedirs(outdir, exist_ok=True)
    jobs = []
    for n, (k, i) in enumerate(todo):
        act = MENUS[k][4][i][2]
        backs = {"mode": 3, "native": 3, "sub": 1, "setup": 1}[act]
        pad = os.path.join(outdir, "%02d.txt" % n)
        with open(pad, "w") as f:
            f.write(pad_for(k, i, backs))
        jobs.append((n, k, i, pad))
        if a.list:
            print("%02d  %-16s %-20s %s" % (n, MENUS[k][0], MENUS[k][4][i][1], act))
    if a.list:
        return 0
    results = {}
    lock = threading.Lock()

    def run(job):
        n, k, i, pad = job
        tag = "fesweep_%s_%02d" % (a.disc, n)
        frames = sum(int(l.split()[0]) for l in open(pad) if l[:1].isdigit())
        secs = a.seconds or frames // 60 + 8
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               os.path.join(ROOT, "_build", "selftest.ps1"), "-Scene", "mode=menu",
               "-Disc", a.disc, "-ExeDir", a.exe_dir, "-Tag", tag, "-Pad", pad,
               "-Seconds", str(secs), "-CaptureAt", "0", "-KeepAfterEnd"]
        env = dict(os.environ, MELEE_PAD_IGNORE_ADAPTER="1")
        p = subprocess.run(cmd, capture_output=True, text=True, env=env)
        logp = os.path.join(ROOT, "_build", "runs", tag, "melee-pc.log")
        log = open(logp, encoding="utf-8", errors="replace").read() if os.path.exists(logp) else ""
        ok, why = check(k, i, log)
        faults = "RESULT: OK" not in p.stdout
        with lock:
            results[n] = (ok and not faults, why + ("" if not faults else "  [selftest PROBLEM]"))
            print("%s %02d %-16s %-20s %s" % ("PASS" if results[n][0] else "FAIL", n,
                                              MENUS[k][0], MENUS[k][4][i][1], results[n][1]),
                  flush=True)

    pending = list(jobs)
    threads = []

    def worker():
        while True:
            with lock:
                if not pending:
                    return
                job = pending.pop(0)
            run(job)

    for _ in range(a.jobs):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    npass = sum(1 for v in results.values() if v[0])
    print("\n%s: %d/%d items reached their destination and came back" % (a.disc, npass, len(results)))
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
