"""courier_moves.py - give the Courier (base "none") the Striker's move set, retargeted onto its own skeleton.

    python -m tools.geno.courier_moves [--striker DIR] [--courier DIR]

Reads the Striker fixture's scripts (`moves/*.genoasm`, written against the Mario skeleton: `joint=N` is a Mario fp->parts
index) and writes the Courier's scripts: every `joint=N` is moved to the Courier's joint that plays the same ROLE (the Mario
limb: the fixture's `retarget.json` "roles" table, joint names), per-hitbox overrides from the same file ("hitboxes":
the Nth hitbox of a move gets its own Courier joint and offsets where the clip strikes with a different limb than
Mario's), and `PUT ANIM_RATE x` is set to 1.0 (the Courier's
clips are authored at rate 1.0; 1.2-1.45 was tuned for Mario's clips). The `.words` are compiled with tools.geno.asm. The
Courier's geno.json then carries the Striker's `jumps`, `special_attributes`, `states`, `specials` and `subactions` (its
`fx_bindings` stay with the Striker: they name Mario joints and the Striker's effect files).

No game data: the Mario joint indices in retarget.json are the numbers the Striker's scripts already use (the retail
fighter's parts table as printed by `gd.joints` in the LAB); everything else is the Courier's own.
"""
import argparse, json, os, re, subprocess, sys

def joint_map(plan, retarget):
    """Mario joint index -> Courier joint index, by the LIMB each joint is (retarget.json "roles": names, not the part table:
    the part table folds the Courier's three-bone arm onto Mario's four parts, which put a Mario hand hitbox on the forearm)."""
    names = {j["name"]: i for i, j in enumerate(plan["joints"])}
    return {int(k): names[v] for k, v in retarget["roles"].items()}


def retarget_script(text, jm, move, retarget, plan, report):
    names = {j["name"]: i for i, j in enumerate(plan["joints"])}
    ov = retarget.get("hitboxes", {}).get(move, {})
    state = {"n": -1}

    def line(m):
        txt = m.group(0)
        if not txt.startswith("hitbox slot="):
            return txt
        state["n"] += 1
        o = ov.get(str(state["n"]))
        jn = re.search(r"joint=(\d+)", txt)
        if jn is None:
            return txt
        n = int(jn.group(1))
        if n not in jm:
            report.append("joint %d has no role" % n)
        else:
            txt = txt.replace(jn.group(0), "joint=%d" % jm[n], 1)
        if o:
            if "joint" in o:
                txt = re.sub(r"joint=\d+", "joint=%d" % names[o["joint"]], txt, count=1)
            for k in ("x", "y", "z", "size"):
                if k in o:
                    if re.search(r" %s=" % k, txt):
                        txt = re.sub(r" %s=-?[0-9.]+" % k, " %s=%s" % (k, o[k]), txt, count=1)
                    else:
                        txt = txt.replace(" angle=", " %s=%s angle=" % (k, o[k]), 1)
        return txt

    text = re.sub(r"(?m)^hitbox slot=.*$", line, text)
    return re.sub(r"(?m)^PUT ANIM_RATE\s+[0-9.]+", "PUT ANIM_RATE 1.0", text)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--striker", default=None)
    ap.add_argument("--courier", default=None)
    a = ap.parse_args(argv)
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    game = os.environ.get("GW_MELEE", os.path.join(root, "melee"))
    mods = os.path.join(game, "pc", "geno", "mods")
    striker = a.striker or os.path.join(mods, "vanilla-striker")
    courier = a.courier or os.path.join(mods, "vanilla-courier")
    plan = json.load(open(os.path.join(courier, "files", "plan.json"), encoding="utf-8"))
    retarget = json.load(open(os.path.join(courier, "retarget.json"), encoding="utf-8"))
    jm = joint_map(plan, retarget)
    os.makedirs(os.path.join(courier, "moves"), exist_ok=True)
    report, n = [], 0
    for f in sorted(os.listdir(os.path.join(striker, "moves"))):
        if not f.endswith(".genoasm"):
            continue
        src = open(os.path.join(striker, "moves", f), encoding="utf-8").read()
        dst = os.path.join(courier, "moves", f)
        open(dst, "w", encoding="utf-8", newline="\n").write(retarget_script(src, jm, f[:-len('.genoasm')], retarget, plan, report))
        subprocess.check_call([sys.executable, "-m", "tools.geno.asm", dst, "-o", dst[:-len(".genoasm")] + ".words", "--words"],
                              cwd=root)
        n += 1
    sj = json.load(open(os.path.join(striker, "geno.json"), encoding="utf-8"))["fighters"][0]
    cp = os.path.join(courier, "geno.json")
    cj = json.load(open(cp, encoding="utf-8"))
    cf = cj["fighters"][0]
    for k in ("jumps", "special_attributes", "states", "specials", "subactions"):
        if k in sj:
            cf[k] = sj[k]
    open(cp, "w", encoding="utf-8", newline="\n").write(json.dumps(cj, indent=2) + "\n")
    print("courier_moves: %d scripts retargeted (%d joint notes), geno.json carries the Striker's states/specials/subactions" % (n, len(report)))
    for r in sorted(set(report)):
        print("  note:", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
