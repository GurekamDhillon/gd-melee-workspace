"""Accuracy table for the Jev tools on local artifacts with known truth (2026-10-09).

Needs the main checkout's untracked _build/ logs and ports/goku-xv2 docs, so it is a
manual evaluation, not a unit test. Offline by default (code layer + deterministic stubs);
`--live` uses TYPESAFE_API_KEY (sends only the tools' redacted, bounded payloads).

  python tools/jev/eval_local.py [--root "E:/Projects/Melee Workspace"] [--live]
"""
import argparse
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).parent))
import coverage  # noqa: E402
import runparse  # noqa: E402
import triage_run  # noqa: E402

PASS_OK = {"pass", "clean_no_verdict"}

# (run path under _build, truth label, accepted triage `choice` values, note)
RUNS = [
    ("agents/goku-polish/runs/bairlane-captain", "setup: v11 geno.json vs v10 build, scene rejected, then TIMEOUT", {"harness_artifact"}),
    ("agents/goku-polish/runs/bairlane-fox", "same", {"harness_artifact"}),
    ("agents/goku-polish/runs/bairlane-mars", "same", {"harness_artifact"}),
    ("agents/goku-polish/runs/bairlane-purin", "same", {"harness_artifact"}),
    ("agents/goku-polish/runs/bairlane-shield-captain", "same", {"harness_artifact"}),
    ("agents/goku-polish/runs/bairlane-shield-fox", "same", {"harness_artifact"}),
    ("agents/goku-polish/runs/bairfinal-fox", "same", {"harness_artifact"}),
    ("agents/goku-polish/runs/fin-gtrace", "PASSed (RESULT PASS DONE)", {"pass"}),
    ("agents/goku-polish/runs/fin-landing", "PASSed (LANDCHECK RESULT PASS)", {"pass"}),
    ("agents/goku-polish/runs/punch-landing", "PASSed per owner (cases=40 sinking=0, clean exit)", {"pass"}),
    ("agents/goku-polish/runs/punch-grab-fox", "PASSed (27 GRABCHECK PASS)", {"pass"}),
    ("agents/goku-polish/runs/grabcheck", "PASSed", {"pass"}),
    ("wb-demo/GDMelee/userdata/runs/d6d30f4d-0588-42ea-a6a7-874c30f7e2b8", "setup: scene rejected, goku-xv2 not in mods", {"harness_artifact"}),
    ("goku-xv2/combo/results/base1-fox.run.txt", "turbo refused + Geno_DefinePlanInt assertion (mod define failure)", {"mod_content", "needs_human"}),
    ("agents/goku-polish/runs/ledge1", "Lua error: global 'os' is nil at script load, then TIMEOUT", {"script_bug", "needs_human"}),
    ("agents/goku-polish/runs/ledge2", "ran clean (turbo refused note only)", {"pass"}),
    ("agents/geno-thrown/runs/gt-suite", "tests PASS; paused-window watchdog line is not a stall", {"pass", "needs_human"}),
]


def eval_triage(build, live):
    rows, ok = [], 0
    for rel, truth, accept in RUNS:
        p = build / rel
        if not p.exists():
            rows.append((rel, truth, "(missing)", "-", False))
            continue
        name, text, extras = runparse.load_run(p)
        parsed = runparse.parse_text(text, name=name, extras=extras)
        r = triage_run.classify({}, text, parsed=parsed, offline=not live)
        good = r["choice"] in accept
        ok += good
        rows.append((rel.split("/")[-1], truth, "%s/%s" % (r["choice"], r.get("cause") or r.get("option") or r["source"]), r["band"], good))
    return rows, ok


def read(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def eval_coverage(root, build, live):
    out = []
    pl = read(root / "ports/goku-xv2/PUNCHLIST-2026-10-09.md")
    brief = "\n".join(l for l in pl.splitlines() if re.match(r"\s*\d+\.", l))
    hand = read(root / "ports/goku-xv2/HANDOFF.md")
    report = hand[hand.index("## 2026-10-09 punch-list pass"):]
    truth = {1: "done", 2: "owed", 3: "done", 4: "owed", 5: "unaddressed", 6: "owed", 7: "done", 8: "done", 9: "owed",
             10: "unaddressed", 11: "done", 12: "done", 13: "owed", 14: "unaddressed"}
    res = coverage.coverage(brief, report, offline=not live)
    anchors = {1: "Ground blend", 3: "Ground blend", 7: "Landing sink", 8: "Emblem", 11: "Bair reach", 12: "Landing lag",
               2: "Re-pick", 4: "Re-pick", 6: "Re-pick", 9: "Re-pick", 13: "Re-pick"}
    reqs = coverage.requirements(brief)
    got = [r for r in reqs if r["ref"] in anchors and anchors[r["ref"]] in " ".join(coverage.retrieve(r["text"], report, ref=r["ref"])[0])]
    print("RETRIEVAL (code only), HANDOFF vs PUNCHLIST: anchor passage retrieved for %d/%d requirements that have one" % (len(got), len(anchors)))
    truth = {int(r["id"][1:]): truth[r["ref"]] for r in reqs}
    out.append(("HANDOFF punch-list pass vs PUNCHLIST", res, truth))
    routes = read(build / "goku-xv2/combo/results/fin-routes.md")
    rbrief = "\n".join("- Run the light5-finisher route tests against %s" % n for n in ("Fox", "Captain Falcon", "Jigglypuff", "Marth", "Peach"))
    rtruth = {1: "done", 2: "done", 3: "done", 4: "done", 5: "unaddressed"}
    out.append(("fin-routes.md vs 5 matchups (Peach never run)", coverage.coverage(rbrief, routes, offline=not live), rtruth))
    nores = read(build / "goku-xv2/combo/results/bairlane.md")
    btruth = {i: "not_done" for i in range(1, 5)}
    bbrief = "\n".join("- Run the bair lane combo tests against %s" % n for n in ("Fox", "Captain Falcon", "Jigglypuff", "Marth"))
    out.append(("bairlane.md (all NO RESULT) vs 4 matchups", coverage.coverage(bbrief, nores, offline=not live), btruth))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path("E:/Projects/Melee Workspace"))
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    build = a.root / "_build"
    rows, ok = eval_triage(build, a.live)
    print("TRIAGE (%s)" % ("live" if a.live else "offline: code layer + stub"))
    for r in rows:
        print("  %-4s %-30s %-34s band=%-7s | %s" % ("ok" if r[4] else "MISS", r[0][:30], r[2][:34], r[3], r[1][:70]))
    print("  triage accuracy: %d/%d" % (ok, len(rows)))
    calib, sweep = [], []
    for title, res, truth in eval_coverage(a.root, build, a.live):
        good = 0
        print("COVERAGE %s%s" % (title, "" if a.live else "  [offline keyword stub, NOT Jev: measures plumbing only]"))
        for r in res["requirements"]:
            n = int(r["id"][1:])
            want = truth[n]
            got = r["status"]
            hit = got == want or (want == "not_done" and got != "done")
            good += hit
            print("  %-4s %-3s want=%-11s got=%-11s%s" % ("ok" if hit else "MISS", r["id"], want, got, " (human)" if r["needs_human_read"] else ""))
        print("  accuracy: %d/%d; flagged for human read: %d" % (good, len(truth), len(res["needs_human_read"])))
        for r in res["requirements"]:
            want = truth[int(r["id"][1:])]
            hit = r["status"] == want or (want == "not_done" and r["status"] != "done")
            if "p" in r:
                calib.append((min(abs(2 * v - 1) for v in r["p"].values()), hit, r["needs_human_read"]))
                sweep.append((r["p"], want))
    if calib:
        print("CALIBRATION (coverage, margin = min |2p-1| over the 3 nouls; correct = status matches truth)")
        for lo, hi in ((0, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 1.01)):
            b = [c for c in calib if lo <= c[0] < hi]
            if b:
                print("  margin %.1f-%.1f: n=%d correct=%d  flagged=%d" % (lo, min(hi, 1), len(b), sum(c[1] for c in b), sum(c[2] for c in b)))
        unflag = [c for c in calib if not c[2]]
        print("  threshold sweep (noul_yes; noul_no = 1 - yes): correct / flagged / confidently-wrong of %d" % len(sweep))
        for y in (0.6, 0.7, 0.8, 0.9):
            c = f = w = 0
            for pr, want in sweep:
                st, human, _ = coverage.combine({k: {"noul": v} for k, v in pr.items()}, {"noul_yes": y, "noul_no": 1 - y})
                ok_ = st == want or (want == "not_done" and st != "done")
                c += ok_ and not human
                f += human
                w += (not ok_) and (not human)
            print("    yes>=%.1f: correct=%d flagged=%d confidently_wrong=%d" % (y, c, f, w))
        print("  not flagged: n=%d correct=%d | flagged: n=%d correct=%d" % (len(unflag), sum(c[1] for c in unflag), len(calib) - len(unflag), sum(c[1] for c in calib if c[2])))


if __name__ == "__main__":
    main()
