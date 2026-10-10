"""Deterministic run parser: no model, no network. Facts are parsed in code.

Jev's docs (how-to-build-with-system-one, model-jaggedness/jev-1.13) say to keep
deterministic facts (PASS/FAIL, exit codes, counts) in code and ask the model only
the judgment that is left. This module extracts those facts from a run directory
(`melee-pc.log`, `exit.json`, `diagnosis.json`, `crashlogs/*.log`), a log file, a
harness `*.run.txt`, or log text, and returns a typed verdict:

  class: pass | clean_no_verdict | test_fail | harness_setup | timeout | fault | unknown
  decided: True when the class is a fact (everything but `fault` and `unknown`)
  cause: for harness_setup the signal id; for timeout load_progress/unexplained
  signature: for `fault`, the bounded crash signature a narrow model question may read

  python tools/jev/runparse.py RUN_DIR_OR_LOG [--expect-mod ID ...]
"""
import argparse
import json
from pathlib import Path
import re

try:
    from . import jev
except ImportError:
    import jev

MAX_LOG = 64 * 1024 * 1024

# --- result lines -----------------------------------------------------------
RESULT_LINE = re.compile(r"\bRESULT\b[:\s]*(?P<v>PASS|FAIL)?")
CHECK_LINE = re.compile(r"\b[A-Z]*CHECK\b.*?\b(?P<v>PASS|FAIL)\b")
TESTS_LINE = re.compile(r"\bTESTS:\s*(?:pass=(?P<p>\d+)\s+fail=(?P<f>\d+)|(?P<x>TIMEOUT))")
CELLS = re.compile(r"\((\d+)\s+cells?\b")
SUMMARY_KV = re.compile(r"^(exit|FATAL)\s+(\d+)\s*$")  # tools/port run summary footer

# --- setup / harness signatures: (id, regex, hard) ---------------------------
SETUP = [
    ("turbo_refused", re.compile(r"turbo: refused|requires a pad script or LAB batch"), False),
    ("scene_rejected", re.compile(r"MELEE_SCENE: rejected"), True),
    ("mod_define_refused", re.compile(r"define refused"), True),
    ("disk_full", re.compile(r"ENOSPC|No space left|not enough space on the disk|disk (?:is )?full", re.I), True),
    ("sandbox_failure", re.compile(r"sandbox is active|retained a launch marker|sandbox.{0,40}(?:denied|failed|cannot|refus)|bwrap:|Operation not permitted", re.I), True),
]
SOFT_NOTE = [("mod_version_mismatch", re.compile(r"geno\.json is Geno v\d+, this build is v\d+"))]

# --- fault signatures -----------------------------------------------------------
BENIGN = re.compile(r"ignored at exit|aurora teardown|Device lost|aurora\[warning\]", re.I)
FAULT = [
    ("assertion", re.compile(r"assertion \".*\" failed|Assertion failed|\bassert(?:ion)? fail", re.I)),
    ("fatal", re.compile(r"\bFATAL\b(?!\s+\d+\s*$)")),
    ("crash", re.compile(r"unhandled exception|access violation|EXCEPTION_[A-Z_]+|crash ?log (?:written|saved)|0xC0000\w{3}|SIGSEGV|segmentation fault", re.I)),
    ("panic", re.compile(r"\bpanic\b|\babort\(\)", re.I)),
    ("stall", re.compile(r"watchdog:.{0,60}(?:stall|stuck|hung|no progress)", re.I)),
    ("script_error", re.compile(r"script.{0,60}(?:\berror\b|traceback)|lua error|attempt to (?:index|call|perform)", re.I)),
]

EXIT_FINAL = re.compile(r"launcher final reason=(?P<r>\S+) code=(?P<c>-?\d+)")
EXIT_FINAL2 = re.compile(r"final exit reason=(?P<r>.+?) code=(?P<c>-?\d+)")
EXIT_PLAIN = re.compile(r"melee-pc: exit (?P<c>-?\d+)")
HEARTBEAT = re.compile(r"heartbeat retrace=(\d+) presented=(\d+)")
MOD_ROW = re.compile(r"gw: mods:\s+(?P<id>[\w.\-]+)\s+(?P<kind>\w+)\s+(?P<ver>[\w.]+)\s+(?P<on>on|off)\s*$")
MOD_COUNT = re.compile(r"gw: mods: .*? - (\d+) mod\(s\)")
SCENE = re.compile(r'MELEE_SCENE="([^"]*)"')
GENO_ID = re.compile(r"geno:([\w.\-]+)/")
NOISE = re.compile(r"heartbeat|AX:|perf:|frame_work|gx: |fx: |hitch", re.I)


def read_text(path, limit=MAX_LOG):
    try:
        with Path(path).open("rb") as s:
            return s.read(limit).decode("utf-8", "replace")
    except OSError:
        return ""


def load_run(source):
    """Return (name, log_text, extras) for a run dir, a file path, or literal text."""
    extras = {}
    if isinstance(source, Path) or (isinstance(source, str) and "\n" not in source and len(source) < 400 and Path(source).exists()):
        p = Path(source)
        if p.is_dir():
            text = read_text(p / "melee-pc.log")
            for name in ("exit.json", "diagnosis.json"):
                try:
                    extras[name] = json.loads(read_text(p / name))
                except ValueError:
                    pass
            crashes = sorted((p / "crashlogs").glob("*.log"), key=lambda q: q.stat().st_mtime) if (p / "crashlogs").is_dir() else []
            if crashes:
                extras["crashlog"] = read_text(crashes[-1], 64 * 1024)
            return p.name, text, extras
        return p.name, read_text(p), extras
    return "text", str(source), extras


def parse_text(text, *, name="text", extras=None, expect_mods=(), crashlog=None):
    extras = extras or {}
    crashlog = crashlog or extras.get("crashlog", "")
    lines = text.splitlines()
    results, counts = [], {"pass": 0, "fail": 0}
    tests, cells = None, 0
    setup, notes, faults = {}, {}, []
    exit_info = {"reason": None, "code": None, "timeout": False}
    beats, mods, mod_count, scene = [], {}, None, ""
    summary = {}
    for i, line in enumerate(lines, 1):
        s = line.strip()
        m = SUMMARY_KV.match(s)
        if m:
            summary[m[1]] = int(m[2])
            continue
        r = RESULT_LINE.search(s)
        if r:
            results.append({"line": i, "verdict": (r["v"] or "").upper() or None, "text": jev.bounded(s, 200)})
            c = CELLS.search(s)
            cells += int(c[1]) if c else 0
        else:
            c = CHECK_LINE.search(s)
            if c:
                results.append({"line": i, "verdict": c["v"], "text": jev.bounded(s, 200)})
        t = TESTS_LINE.search(s)
        if t:
            tests = {"timeout": True} if t["x"] else {"pass": int(t["p"]), "fail": int(t["f"])}
            results.append({"line": i, "verdict": "FAIL" if t["x"] or int(t["f"]) else "PASS", "text": jev.bounded(s, 200)})
        for sid, rx, hard in SETUP:
            if sid not in setup and rx.search(s):
                setup[sid] = {"line": i, "hard": hard, "text": jev.bounded(s, 240)}
        for sid, rx in SOFT_NOTE:
            if sid not in notes and rx.search(s):
                notes[sid] = {"line": i, "text": jev.bounded(s, 240)}
        if not BENIGN.search(s) and not NOISE.search(s[:60]):
            for kind, rx in FAULT:
                if rx.search(s):
                    if kind == "stall" and re.search(r"paused=1|hidden=1|minimized=1", s):
                        break  # watchdog on a deliberately paused/hidden window is not a stall
                    faults.append({"kind": kind, "line": i, "text": jev.bounded(s, 240)})
                    break
        for rx in (EXIT_FINAL, EXIT_FINAL2):
            e = rx.search(s)
            if e:
                exit_info.update(reason=e["r"], code=int(e["c"]))
        e = EXIT_PLAIN.search(s)
        if e and exit_info["code"] is None:
            exit_info["code"] = int(e["c"])
        h = HEARTBEAT.search(s)
        if h:
            beats.append((int(h[1]), int(h[2])))
        mr = MOD_ROW.search(s)
        if mr:
            mods[mr["id"]] = mr["on"] == "on"
        mc = MOD_COUNT.search(s)
        if mc:
            mod_count = int(mc[1])
        sc = SCENE.search(s)
        if sc:
            scene = sc[1]
    for v in results:
        if v["verdict"] == "PASS":
            counts["pass"] += 1
        elif v["verdict"] == "FAIL":
            counts["fail"] += 1
    if "exit" in summary and exit_info["code"] is None:
        exit_info["code"] = summary["exit"]
    ex = extras.get("exit.json")
    if ex and exit_info["code"] is None:
        exit_info.update(reason=ex.get("reason"), code=ex.get("code"))
    diag = extras.get("diagnosis.json") or {}
    if diag.get("verdict"):
        exit_info["diagnosis"] = diag["verdict"]
    exit_info["timeout"] = exit_info["code"] == 124 or str(exit_info["reason"] or "").upper() == "TIMEOUT" or \
        str(diag.get("verdict", "")).upper() == "TIMEOUT" or bool(tests and tests.get("timeout"))

    # mods the scene needs vs what loaded
    wanted = list(dict.fromkeys(list(expect_mods) + GENO_ID.findall(scene)))
    missing = [m for m in wanted if not mods.get(m)]
    if missing:
        setup["mod_missing"] = {"line": 0, "hard": True, "text": "expected mod(s) not loaded/enabled: " + ", ".join(missing)}

    progressing = len(beats) >= 2 and beats[-1][0] > beats[0][0] and beats[-1][1] > beats[0][1]
    if crashlog.strip() and not any(f["kind"] in ("fatal", "crash") for f in faults):
        faults.append({"kind": "crash", "line": 0, "text": jev.bounded(crashlog.strip().splitlines()[0], 240)})

    # --- classification (ordered; first match wins) ---
    hard_setup = [k for k, v in setup.items() if v["hard"]]
    soft_setup = [k for k, v in setup.items() if not v["hard"]]
    clazz, decided, cause, why = "unknown", False, None, []
    if hard_setup and counts["pass"] and not counts["fail"] and not faults:
        hard_setup = []  # the run produced PASS verdicts: a setup warning does not void them (kept in `setup`)
    if hard_setup and faults:
        clazz, cause, why = "fault", "setup_with_fault", ["hard setup signal(s) %s AND fault evidence: the fault needs reading" % hard_setup]
    elif hard_setup:
        clazz, decided, cause, why = "harness_setup", True, hard_setup[0], ["hard setup signal(s): " + ", ".join(hard_setup)]
    elif counts["fail"]:
        clazz, decided, why = "test_fail", True, ["%d FAIL result line(s)" % counts["fail"]]
    elif faults:
        clazz, why = "fault", ["fault evidence: %s" % faults[0]["kind"]]
    elif exit_info["timeout"]:
        clazz, decided = "timeout", True
        if soft_setup:
            cause, why = soft_setup[0], ["timeout with soft setup signal(s): " + ", ".join(soft_setup)]
        else:
            cause = "load_progress" if progressing else "unexplained"
            why = ["exit TIMEOUT code=124; heartbeat %s" % ("advancing" if progressing else "not confirmed advancing")]
    elif counts["pass"]:
        clazz, decided, why = "pass", True, ["%d PASS result line(s), no FAIL, no fault, exit %s" % (counts["pass"], exit_info["code"])]
    elif exit_info["code"] == 0:
        clazz, decided, why = "clean_no_verdict", True, ["clean exit code 0; no PASS/FAIL line (%d RESULT-ish lines); no fault evidence" % len(results)]
    else:
        why = ["no result lines, no fault, exit code %s" % exit_info["code"]]
    if exit_info["code"] not in (None, 0, 124) and clazz in ("pass", "clean_no_verdict"):
        clazz, decided, why = "unknown", False, ["results say pass but exit code is %s" % exit_info["code"]]

    out = {"run": name, "class": clazz, "decided": decided, "cause": cause, "why": why,
           "results": {"counts": counts, "tests": tests, "cells": cells or None, "lines": results[-8:]},
           "exit": exit_info, "setup": setup, "notes": notes,
           "faults": faults[:6], "fault_count": len(faults),
           "heartbeat": {"n": len(beats), "last": beats[-1] if beats else None, "progressing": progressing},
           "mods": {"loaded": sorted(k for k, v in mods.items() if v), "expected": wanted, "missing": missing},
           "scene": jev.bounded(scene, 200) if scene else None}
    if clazz == "fault":
        out["signature"] = signature(lines, faults, crashlog)
    return out


def signature(lines, faults, crashlog="", before=10, cap=1800):
    """Bounded crash signature: first fault line, location hints, the last `before`
    non-noise lines preceding it, and the head of the crash log."""
    f = faults[0]
    idx = max(0, f["line"] - 1) if f["line"] else len(lines)
    ctx = [l.strip() for l in lines[max(0, idx - 60):idx] if l.strip() and not NOISE.search(l[:60])][-before:]
    hints = re.findall(r"(?:in|at)\s+([\w\\/.]+\.\w+)(?:\s+on line\s+(\d+))?|assertion \"([^\"]+)\"", f["text"])
    sig = {"kind": f["kind"], "fault_line": f["text"],
           "locations": [" ".join(x for x in h if x) for h in hints][:3], "preceding": [jev.bounded(c, 200) for c in ctx]}
    if crashlog.strip():
        sig["crashlog_head"] = [jev.bounded(l.strip(), 200) for l in crashlog.strip().splitlines()[:12]]
    while len(json.dumps(sig)) > cap and sig["preceding"]:
        sig["preceding"] = sig["preceding"][1:]
    return jev.sanitize(sig)


def parse(source, **kw):
    name, text, extras = load_run(source)
    return parse_text(text, name=name, extras=extras, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", type=Path)
    ap.add_argument("--expect-mod", action="append", default=[], help="mod id the run must have loaded (repeatable)")
    a = ap.parse_args()
    if not a.path.exists():
        ap.exit(2, "runparse: missing input\n")
    print(json.dumps(jev.sanitize(parse(a.path, expect_mods=a.expect_mod)), indent=2))


if __name__ == "__main__":
    main()
