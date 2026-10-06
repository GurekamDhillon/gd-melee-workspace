"""courier_moves.py - give the Courier (base "none") the Striker's move set, retargeted onto its own skeleton.

    python -m tools.geno.courier_moves [--striker DIR] [--courier DIR]

Reads the Striker fixture's scripts (`moves/*.genoasm`, written against the Mario skeleton: `joint=N` is a Mario fp->parts
index) and writes the Courier's scripts: every `joint=N` is moved to the Courier's joint that plays the same ROLE (the Mario
joint's Melee part, then the Courier's part_to_joint from its plan.json), and `PUT ANIM_RATE x` is set to 1.0 (the Courier's
clips are authored at rate 1.0; 1.2-1.45 was tuned for Mario's clips). The `.words` are compiled with tools.geno.asm. The
Courier's geno.json then carries the Striker's `jumps`, `special_attributes`, `states`, `specials` and `subactions` (its
`fx_bindings` stay with the Striker: they name Mario joints and the Striker's effect files).

No game data: the Mario joint -> part table below is the retail fighter's parts table as printed by `gd.joints` in the LAB
(numbers only, read from a running game), the same numbers the Striker's scripts already use.
"""
import argparse, json, os, re, subprocess, sys

# Mario fp->parts index -> Fighter_Part name (ftparts: part_to_joint of fighter kind 0, printed from the running game)
MARIO_JOINT_PART = {
    0: "TopN", 1: "TransN", 2: "XRotN", 3: "YRotN", 4: "HipN", 5: "WaistN",
    47: "LLegJA", 48: "LLegJ", 49: "LKneeJ", 50: "LFootJA", 51: "LFootJ",
    53: "RLegJA", 54: "RLegJ", 55: "RKneeJ", 56: "RFootJA", 57: "RFootJ",
    6: "LShoulderJA", 7: "LShoulderJ", 8: "LArmJ", 9: "LHandN", 10: "L1stNa", 11: "L1stNb", 12: "L2ndNa", 13: "L2ndNb",
    14: "L3rdNa", 15: "L3rdNb", 16: "L4thNa", 17: "L4thNb", 18: "LThumbNa", 19: "LHandNb", 20: "NeckN", 22: "HeadN",
    23: "RShoulderN", 29: "RShoulderJA", 30: "RShoulderJ", 31: "RArmJ", 32: "RHandN", 33: "R1stNa", 34: "R1stNb",
    35: "R2ndNa", 36: "R2ndNb", 37: "R3rdNa", 38: "R3rdNb", 39: "R4thNa", 40: "R4thNb", 41: "RThumbNa", 43: "RHandNb",
    44: "ThrowN",
}
PART_ORDER = ("TopN TransN XRotN YRotN HipN WaistN LLegJA LLegJ LKneeJ LFootJA LFootJ RLegJA RLegJ RKneeJ RFootJA RFootJ "
              "BustN LShoulderN LShoulderJA LShoulderJ LArmJ LHandN L1stNa L1stNb L2ndNa L2ndNb L3rdNa L3rdNb L4thNa L4thNb "
              "LThumbNa LThumbNb LHandNb NeckN HeadN RShoulderN RShoulderJA RShoulderJ RArmJ RHandN R1stNa R1stNb R2ndNa "
              "R2ndNb R3rdNa R3rdNb R4thNa R4thNb RThumbNa RThumbNb RHandNb ThrowN TransN2").split()


def joint_map(plan):
    p2j = plan["parts"]["part_to_joint"]
    out = {}
    for mj, part in MARIO_JOINT_PART.items():
        cj = p2j[PART_ORDER.index(part)]
        out[mj] = cj if cj != 255 else p2j[PART_ORDER.index("HipN")]
    return out


def retarget(text, jm, report):
    def j(m):
        n = int(m.group(1))
        if n not in jm:
            report.append("joint %d has no role" % n)
            return m.group(0)
        return "joint=%d" % jm[n]
    text = re.sub(r"joint=(\d+)", j, text)
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
    jm = joint_map(plan)
    os.makedirs(os.path.join(courier, "moves"), exist_ok=True)
    report, n = [], 0
    for f in sorted(os.listdir(os.path.join(striker, "moves"))):
        if not f.endswith(".genoasm"):
            continue
        src = open(os.path.join(striker, "moves", f), encoding="utf-8").read()
        dst = os.path.join(courier, "moves", f)
        open(dst, "w", encoding="utf-8", newline="\n").write(retarget(src, jm, report))
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
