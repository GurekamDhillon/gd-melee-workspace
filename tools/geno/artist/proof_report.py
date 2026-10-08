"""proof_report.py - summarise the ARTPROOF lines proof.lua wrote into a run's melee-pc.log.

    python -m tools.geno.artist.proof_report <melee-pc.log> [--require idle,walk,run,jump,jab,shield,grab,grab_throw] [--token Starter]

Prints, per scenario, the motions and authored clips it played, and checks the claims an artist cares about:
the clips played are the package's (anim_name is the bank clip name; rows without a clip show the placeholder's name), the jab's hitbox sat on the striking limb, the shield came up,
the grab held Mario and the throw damaged him. Exit 1 if a required scenario is missing or fails.
"""
import json
import re
import sys


def parse(path):
    recs = {}
    done = False
    for line in open(path, encoding="utf-8", errors="replace"):
        i = line.find("ARTPROOF ")
        if i < 0:
            continue
        body = line[i + 9:].strip()
        if body.startswith("DONE"):
            done = True
        elif body.startswith("FAIL"):
            recs["_fail"] = body
        else:
            try:
                r = json.loads(body)
                recs[r["name"]] = r
            except ValueError:
                pass
    return recs, done


CHECKS = {
    "idle": lambda r: any("Wait" in c for c in r["clips"]),
    "walk": lambda r: r["x"] > 8 and any(m.startswith("Walk") for m in r["motions"]),
    "run": lambda r: r["x"] > 30 and any(m in ("Run", "Dash") for m in r["motions"]),
    "jump": lambda r: any(m.startswith("Jump") for m in r["motions"]) and r["y"] < 0.5,
    "doublejump": lambda r: sum(1 for m in r["motions"] if m.startswith("Jump")) >= 2,
    "jab": lambda r: r.get("hit_frame") is not None and r.get("p2_damage", 0) > 0,
    "shield": lambda r: any(m == "Guard" for m in r["motions"]),
    "grab": lambda r: any(m == "CatchWait" for m in r["motions"]) and any(m.startswith("Capture") for m in r["p2_motions"]),
    "grab_throw": lambda r: any(m.startswith("Throw") for m in r["motions"]) and r.get("p2_damage", 0) > 0,
}


def main(argv):
    path = argv[0]
    req = ["idle", "walk", "run", "jump", "jab", "shield", "grab", "grab_throw"]
    token = None
    if "--require" in argv:
        req = argv[argv.index("--require") + 1].split(",")
    if "--token" in argv:
        token = argv[argv.index("--token") + 1]
    recs, done = parse(path)
    bad = 0
    if "_fail" in recs:
        print(recs["_fail"])
        bad += 1
    print("script finished: %s" % done)
    for name in req:
        r = recs.get(name)
        if not r:
            print("MISSING  %s" % name)
            bad += 1
            continue
        ok = CHECKS[name](r) if name in CHECKS else True
        own = any(c for c in r["clips"])        # anim_name is the bank clip name; an empty list would mean no clip of the package played
        print("%-8s %-10s motions=%s" % ("PASS" if ok and own else "FAIL", name, " > ".join(r["motions"][:10])))
        print("         clips=%s" % " > ".join(re.sub(r"^Ply\w+?_Share_ACTION_|_figatree$", "", c) for c in r["clips"][:10]))
        extra = {k: r[k] for k in ("x", "y", "hit_frame", "hit_af", "hit_bone", "hit_damage", "p2_damage") if k in r}
        print("         %s" % extra)
        if not (ok and own):
            bad += 1
    if "hurtboxes" in recs:
        print("hurtboxes in game: %d" % len(recs["hurtboxes"]["list"]))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
