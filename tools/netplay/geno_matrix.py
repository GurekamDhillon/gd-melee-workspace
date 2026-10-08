#!/usr/bin/env python3
"""geno_matrix.py - the Geno slice 7 online matrix: scripted two-client matches (geno_pair.py), one after another.

    python tools/netplay/geno_matrix.py --exe <melee-pc.exe> --mods <dir with the six fixtures> [--only name,name] [--soak]

Needs GW_BUILD_ROOT (the lane's build root; results go to <root>/net/<name>/). Two games at a time, never more: scenarios run
one by one. Fighter numbers are the resident aliases of the six fixtures in one folder (aliases follow the keys' order, highest
first): caster 127, charger 126, courier 125, hero 124, riposte 123, striker 122; retail Fox 2 and Marth 9. The "less" folder holds
hero and striker only (hero 127, striker 126), so a pairing across the two folders plays one fighter under two different aliases.

Every line of the result is geno_pair.py's verdict (play = a match ran on both sides, no DESYNC, every confirmed-frame checksum
the two sides share agrees) with the number of shared confirmed frames and what the observer saw (distinct Geno states each side
entered, Lua faults).
"""
import argparse, json, os, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
S1 = "lag=60,jitter=15,loss=5"
S2 = "lag=100,jitter=40,loss=10,burst=3,dup=2,spike=6000:350"
LAN = "off"
CK = {"caster": 127, "charger": 126, "courier": 125, "hero": 124, "riposte": 123, "striker": 122, "fox": 2, "marth": 9}
LESS = {"hero": 127, "striker": 126}

# name, host, guest, sim, seconds, [mods for the guest: "all" | "less"]
SCEN = [
    ("mir_striker", "striker", "striker", S1, 110, "all"),
    ("mir_courier", "courier", "courier", S1, 110, "all"),
    ("mir_charger", "charger", "charger", S2, 110, "all"),
    ("mir_riposte", "riposte", "riposte", S1, 110, "all"),
    ("mir_caster", "caster", "caster", S1, 110, "all"),
    ("striker_v_fox", "striker", "fox", S1, 110, "all"),
    ("fox_v_courier", "fox", "courier", S2, 110, "all"),
    ("charger_v_marth", "charger", "marth", S1, 110, "all"),
    ("marth_v_riposte", "marth", "riposte", S2, 110, "all"),
    ("courier_v_striker", "courier", "striker", S1, 110, "all"),
    ("charger_v_riposte", "charger", "riposte", S2, 110, "all"),
    ("caster_v_fox", "caster", "fox", S1, 110, "all"),
    ("alias_striker", "striker", "striker", S1, 110, "less"),
    ("alias_hero_v_striker", "hero", "striker", S2, 110, "less"),
    ("lan_striker", "striker", "striker", LAN, 90, "all"),
]
SOAK = [
    ("soak_courier_v_charger", "courier", "charger", S1, 600, "all"),
    ("soak_striker_v_riposte", "striker", "riposte", S2, 600, "all"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--exe", required=True)
    ap.add_argument("--mods", required=True, help="folder holding mods-a (all six) and mods-less (hero, striker)")
    ap.add_argument("--only", default="")
    ap.add_argument("--soak", action="store_true", help="run the two 10 minute soaks instead of the matrix")
    ap.add_argument("--prefix", default="m_")
    a = ap.parse_args()
    want = set(filter(None, a.only.split(",")))
    rows = []
    for i, (name, h, g, sim, secs, gm) in enumerate(SOAK if a.soak else SCEN):
        if want and name not in want:
            continue
        gck = LESS[g] if gm == "less" else CK[g]
        cmd = [sys.executable, os.path.join(ROOT, "tools", "netplay", "geno_pair.py"), a.prefix + name, "--host-ck", str(CK[h]),
               "--guest-ck", str(gck), "--mods-host", os.path.join(a.mods, "mods-a"),
               "--mods-guest", os.path.join(a.mods, "mods-less" if gm == "less" else "mods-a"), "--net-sim", sim,
               "--seconds", str(secs), "--seed", str(100 + 7 * i), "--exe", a.exe, "--min-frames", str(secs * 18)]
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = os.path.join(os.environ["GW_BUILD_ROOT"], "net", a.prefix + name, "summary.json")
        try:
            s = json.load(open(out))
        except (OSError, ValueError):
            s = {"verdict": "NO SUMMARY", "stderr": r.stderr[-300:]}
        cov = s.get("coverage", {})
        geno = {k: [x.split("geno=")[1].split()[0] for x in v[-2:]] for k, v in cov.items() if v}
        row = "%-24s %-8s %s v %s  sim=%s  frames=%s mismatch=%s desync=%s geno=%s crash=%s (%ds)" % (
            name, s.get("verdict"), h, g, "lan" if sim == "off" else sim.split(",")[0],
            s.get("confirmed_frames", {}).get("shared"), s.get("confirmed_frames", {}).get("mismatching"),
            sum(s.get("desyncs", {}).values()) if s.get("desyncs") else "?", geno, s.get("crash"), time.time() - t0)
        print(row, flush=True)
        rows.append(row)
    return 0 if all(" play " in r for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
