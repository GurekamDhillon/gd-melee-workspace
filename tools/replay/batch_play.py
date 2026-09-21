#!/usr/bin/env python3
"""Play many Slippi replays through the port and report crashes, asserts and hangs.

    python tools/replay/batch_play.py --exe-dir C:/gdm/_build/agents/slpcrash [--count 40]
        [--csv _build/replay_corpus.csv] [--jobs 3] [--only path1.slp,path2.slp] [--out name]

Accuracy is not judged here (first_div.py does that): a replay that diverges but plays to its last
frame passes. What fails is a run that FATALs or asserts, stops advancing, or dies before the
replay's end. Each run goes through _build/selftest.ps1 (-ExitOnDeath, -StopOnLog on the replay
module's "past the replay's last frame"), with MELEE_SLP and MELEE_STATE_TRACE set, so the sandbox,
map and log are the usual ones under _build/runs/<tag>.

The sample is stratified from the survey CSV (tools/replay/survey.py): every character present,
every stage id, doubles, and the item/projectile-heavy characters, preferring shorter games.
"""
from __future__ import annotations

import argparse
import bisect
import concurrent.futures as cf
import csv
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "_build"
SELFTEST = BUILD / "selftest.ps1"
BAD = re.compile(r"FATAL|access violation|assertion|spinning|panic|outside blob code range|"
                 r"unimplemented opcode|resolver returned NULL|aurora fatal|aurora\[fatal\]|"
                 r"HSD_ASSERT|ftPartsRemap: no parts table")
EXTRA = {14, 12, 15, 16, 3, 6, 21, 11, 5, 1}  # ICs Peach Puff Samus G&W Link YLink Ness Bowser DK


def load_rows(path: Path):
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                lf = int(r["last_frame"] or 0)
            except ValueError:
                continue
            if lf < 600:  # aborted games: nothing to learn
                continue
            rows.append({"path": r["path"], "stage": int(r["stage"]), "n": int(r["nplayers"]),
                         "chars": [int(c) for c in r["chars"].split()], "last": lf})
    return rows


def sample(rows, count):
    rows = sorted(rows, key=lambda r: r["last"])  # shorter first within each need
    chosen, seen = [], set()

    def take(pred, k):
        n = 0
        for r in rows:
            if n >= k or len(chosen) >= count:
                return
            if r["path"] not in seen and pred(r):
                chosen.append(r)
                seen.add(r["path"])
                n += 1

    for st in sorted({r["stage"] for r in rows}):
        take(lambda r, st=st: r["stage"] == st, 1)
    for ch in sorted({c for r in rows for c in r["chars"]}):
        take(lambda r, ch=ch: ch in r["chars"] and not any(ch in c["chars"] for c in chosen), 1)
    take(lambda r: r["n"] >= 4, 6)
    for ch in sorted(EXTRA):
        take(lambda r, ch=ch: ch in r["chars"], 1)
    take(lambda r: True, count)
    return chosen[:count]


def load_map(path: Path):
    syms = []
    pat = re.compile(r"\s*[0-9a-f]{4}:[0-9a-f]{8}\s+(\S+)\s+([0-9a-f]{8})\s")
    with open(path, errors="replace") as fh:
        for line in fh:
            m = pat.match(line)
            if m:
                syms.append((int(m.group(2), 16), m.group(1)))
    syms.sort()
    return syms


def symbolize(log: str, map_path: Path, n=10):
    i = log.find("FATAL")
    if i < 0 or not map_path.exists():
        return ""
    syms = load_map(map_path)
    keys = [a for a, _ in syms]
    out = []
    for h in re.findall(r"rva 0x([0-9A-Fa-f]{8})", log[i:i + 4000])[:n]:
        t = int(h, 16)
        j = bisect.bisect_right(keys, t) - 1
        if j >= 0:
            out.append("%s+0x%X" % (syms[j][1].lstrip("_"), t - syms[j][0]))
    return " < ".join(out)


def run_one(r, idx, exe_dir, prefix):
    tag = f"{prefix}{idx:03d}"
    rundir = BUILD / "runs" / tag
    rundir.mkdir(parents=True, exist_ok=True)
    trace = rundir / "trace.csv"
    if trace.exists():
        trace.unlink()
    env = dict(os.environ)
    slp = Path(r["path"])
    env["MELEE_SLP"] = str(slp if slp.is_absolute() else (ROOT / slp).resolve())
    env["MELEE_STATE_TRACE"] = str(trace)
    # real time plus boot and the loading hold, with headroom: with several games on the machine
    # the port can fall to ~40 fps and catch up logic frames without rendering them
    secs = int(r["last"] / 60 * 1.8) + 60
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SELFTEST),
           "-Disc", "vanilla", "-NoMods", "-ExeDir", exe_dir, "-Seconds", str(secs), "-Tag", tag,
           "-CaptureAt", "99999", "-ExitOnDeath", "-StopOnLog", "past the replay's last frame"]
    t0 = time.time()
    subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=secs + 180)
    log_path = rundir / "melee-pc.log"
    log = log_path.read_text(errors="replace") if log_path.exists() else ""
    reached = None
    if trace.exists():
        with open(trace, errors="replace") as fh:
            for line in fh:
                head = line.split(",", 1)[0]
                if head.lstrip("-").isdigit():
                    reached = int(head)
    bad = [ln.strip() for ln in log.splitlines() if BAD.search(ln)]
    done = "past the replay's last frame" in log
    status = "OK" if done and not bad else ("CRASH" if bad else "SHORT")
    if not done and all("spinning" in b for b in bad) and reached is not None and reached > 0:
        status = "TIMEOUT"  # still advancing when the budget ran out: slow, not dead
    if done and bad and all("spinning" in b for b in bad):
        status = "OK*"  # completed; the only flag is a watchdog stall (boot contention), not a fault
    if "no scene requested" in log:
        status = "NOSCENE"  # the replay never became the scene: a harness fault, not a finding
    stack = symbolize(log, rundir / "melee-pc.map")
    # ~40 MB of copied exe/dlls/pipeline caches per sandbox; the log, trace and map are what matter
    for f in rundir.iterdir():
        if f.is_file() and (f.suffix.lower() in (".dll", ".exe") or ".db" in f.name
                            or f.name.endswith(".core")):
            try:
                f.unlink()
            except OSError:
                pass
    return {"tag": tag, "path": r["path"], "stage": r["stage"], "chars": " ".join(map(str, r["chars"])),
            "last": r["last"], "reached": reached, "status": status,
            "bad": " | ".join(bad[:3])[:300], "stack": stack,
            "secs": int(time.time() - t0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe-dir", required=True)
    ap.add_argument("--csv", default=str(BUILD / "replay_corpus.csv"))
    ap.add_argument("--count", type=int, default=40)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="batch")
    ap.add_argument("--prefix", default="slpb")
    ap.add_argument("--random", action="store_true",
                    help="random sample (long games and doubles weighted up) instead of stratified")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--exclude", default="", help="batch CSVs whose replays are skipped")
    args = ap.parse_args()
    rows = load_rows(Path(args.csv))
    for ex in [e for e in args.exclude.split(",") if e]:
        with open(ex, newline="") as fh:
            done_paths = {r["path"] for r in csv.DictReader(fh)}
        rows = [r for r in rows if r["path"] not in done_paths]
    if args.random:
        import random
        rng = random.Random(args.seed)
        weights = [r["last"] * (2 if r["n"] >= 4 else 1) for r in rows]
        picked, pool = [], list(range(len(rows)))
        while pool and len(picked) < args.count:
            i = rng.choices(pool, [weights[j] for j in pool])[0]
            pool.remove(i)
            picked.append(rows[i])
    elif args.only:
        want = [p.strip() for p in args.only.split(",") if p.strip()]
        picked = [r for r in rows if any(r["path"].endswith(w) or r["path"] == w for w in want)]
    if not args.random and not args.only:
        picked = sample(rows, args.count)
    outdir = BUILD / "replay_batch"
    outdir.mkdir(exist_ok=True)
    out = outdir / f"{args.out}.csv"
    print(f"{len(picked)} replays, {args.jobs} at a time -> {out}")
    results = []
    with cf.ThreadPoolExecutor(args.jobs) as ex:
        futs = {ex.submit(run_one, r, i, args.exe_dir, args.prefix): r for i, r in enumerate(picked)}
        for f in cf.as_completed(futs):
            res = f.result()
            results.append(res)
            print(f"{res['status']:5} {res['tag']} reached {res['reached']}/{res['last']} "
                  f"chars {res['chars']} stage {res['stage']} {res['secs']}s  {res['stack'][:120]}",
                  flush=True)
            with open(out, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(res.keys()))
                w.writeheader()
                w.writerows(sorted(results, key=lambda x: x["tag"]))
    bad = [r for r in results if not r["status"].startswith("OK")]
    print(f"\n{len(results) - len(bad)} of {len(results)} OK")
    for r in sorted(bad, key=lambda x: x["tag"]):
        print(f"  {r['status']} {r['tag']} {r['path']}\n    {r['bad']}\n    {r['stack']}")


if __name__ == "__main__":
    main()
