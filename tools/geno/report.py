"""Effective-graph report for a native definition: which of the 351 motion rows and which special
entries are the author's, which are inherited from the donor preset. Offline; reads the package and the
decomp sources only (never a disc).

    python -m tools.geno.report melee/pc/geno/mods/vanilla-striker
    python -m tools.geno.report melee/pc/geno/mods/vanilla-striker --frames    # per-overlay frame data
    python -m tools.geno.report melee/pc/geno/mods/vanilla-striker --json

A row is `own` when the package replaces its script (an overlay on its animation row), declares a
common_states row for it, or binds a Geno state to it; `inherited` otherwise; the Mario special rows
341..350 are `donor-special (unreachable)` once the special entry that leads to them is bound.
The slice-2 definition of "not donor-dependent": zero DONOR special entries and every common attack
row `own`.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from . import check, script

ROOT = Path(__file__).resolve().parents[2]
MELEE = ROOT / "melee"
# the eight special entries, the Mario motion row each one leads to when unbound (ftMr_MS_*), and the keys
SPECIAL_ROWS = {"n": 343, "air_n": 344, "s": 345, "air_s": 346, "hi": 347, "air_hi": 348, "lw": 349, "air_lw": 350}
# the common attack rows slice 2 asks a move-set author to own (the donor's angled-blend rows are not listed)
ATTACK_ROWS = {44: "jab 1", 45: "jab 2", 46: "jab 3", 50: "dash attack", 51: "forward tilt (up)", 53: "forward tilt",
               55: "forward tilt (down)", 56: "up tilt", 57: "down tilt", 58: "forward smash (up)", 60: "forward smash",
               62: "forward smash (down)", 63: "up smash", 64: "down smash", 65: "neutral air", 66: "forward air",
               67: "back air", 68: "up air", 69: "down air", 212: "grab", 214: "dash grab", 217: "pummel",
               219: "forward throw", 220: "back throw", 221: "up throw", 222: "down throw"}


MARIO_SPECIALS = {341: "AppealSR", 342: "AppealSL", 343: "SpecialN", 344: "SpecialAirN", 345: "SpecialS", 346: "SpecialAirS",
                  347: "SpecialHi", 348: "SpecialAirHi", 349: "SpecialLw", 350: "SpecialAirLw"}


def motion_subactions():
    """motion row -> (motion name, the subaction (animation row) its Mario row plays), from the decomp."""
    fwd = (MELEE / "src/melee/ft/kinds/ftCommon/forward.h").read_text(encoding="utf-8", errors="replace")

    def enum(marker):
        i = fwd.index(marker)
        st = fwd.rfind("enum", 0, i)
        body = fwd[fwd.index("{", st) + 1:fwd.index("}", st)]
        v, out = 0, {}
        for line in body.split("\n"):
            line = line.strip().rstrip(",")
            if not line or line.startswith("//"):
                continue
            if "=" in line:
                k, val = line.split("=")
                line, v = k.strip(), int(val, 0)
            out[line] = v
            v += 1
        return out
    sm = enum("ftCo_SM_Attack11")
    text = (MELEE / "src/melee/ft/ftmotionstates.c").read_text(encoding="utf-8", errors="replace")
    rows = {}
    for name, idx, sub in re.findall(r"// (ftCo_MS_\w+) = (\d+)\s*\n\s*(\w+),", text):
        rows[int(idx)] = (name[len("ftCo_MS_"):], sm.get(sub, -1))
    return rows


def load(path):
    base = Path(path)
    if base.is_file():
        base = base.parent
    data = check.load_json(base / "geno.json")
    return base, data


def overlay_words(base, overlay):
    if "words" in overlay:
        return [script.word(w) for w in overlay["words"]]
    return script.read_words((base / overlay["file"]).read_text(encoding="utf-8-sig"))


def frames(words):
    """Hitbox windows and the IASA frame of a script, in script frames (the hitbox is live from readout
    action frame N-2: docs/geno.md section 22). Straight-line walk: loops and conditions are not followed."""
    out = dict(rate=None, hitboxes=[], iasa=None, end=0)
    frame, live = 0, {}
    for line in script.disassemble(words).splitlines():
        line = line.strip()
        if not line:
            continue
        head = line.split()[0]
        if head == "wait":
            frame += int(line.split()[1])
        elif head == "wait_until":
            frame = int(line.split()[1])
        elif head == "PUT" and "ANIM_RATE" in line:
            out["rate"] = round(float(line.split()[-1]), 3)
        elif head == "hitbox":
            if "raw=" in line:
                w = [int(x, 16) for x in line.split("raw=")[1].split(",")]
                f = dict(slot=(w[0] >> 23) & 7, joint=(w[0] >> 11) & 255, damage=w[0] & 1023, size=(w[1] >> 16) / 256.0,
                         angle=(w[3] >> 23) & 511, kbg=(w[3] >> 14) & 511, bkb=(w[4] >> 23) & 511, element=(w[4] >> 18) & 31)
                f["raw"] = True
            else:
                f = {k: (float(v) if "." in v else int(v)) for k, v in (t.split("=") for t in line.split()[1:])}
            f["start"] = frame
            live[f["slot"]] = f
        elif head in ("hitboxes_clear", "clear_hitboxes"):
            for f in live.values():
                f["end"] = frame
                out["hitboxes"].append(f)
            live = {}
        elif head == "iasa":
            out["iasa"] = frame
    for f in live.values():
        f["end"] = None
        out["hitboxes"].append(f)
    out["end"] = frame
    return out


def build(path):
    base, data = load(path)
    fighter = next((f for f in data["fighters"] if "define" in f), None)
    if fighter is None:
        raise ValueError("no define entry in " + str(path))
    rows = motion_subactions()
    overlays = {o["index"]: o for o in fighter.get("subactions", [])}
    common = {r["motion"]: r for r in fighter.get("common_states", [])}
    states = {s.get("name", ""): i for i, s in enumerate(fighter.get("states", []))}
    state_subs = {s["subaction"] for s in fighter.get("states", []) if isinstance(s.get("subaction"), int)}
    specials = fighter.get("specials", {})
    entries = {}
    for key in SPECIAL_ROWS:
        target = specials.get(key)
        if target is None and key.startswith("air_"):
            target = specials.get(key[4:])
        if isinstance(target, dict):
            target = "select " + target["select"]
        entries[key] = target if target is not None else "DONOR"
    table = []
    for motion in range(351):
        name, sub = rows.get(motion, (MARIO_SPECIALS.get(motion, "motion%d" % motion), -1))
        if motion in common:
            kind = "own (common_states row)"
        elif sub in overlays and sub >= 0:
            kind = "own (script overlay on row %d)" % sub
        elif sub in state_subs:
            kind = "own (Geno state animation)"
        elif motion in SPECIAL_ROWS.values():
            key = next(k for k, v in SPECIAL_ROWS.items() if v == motion)
            kind = "inherited" if entries[key] == "DONOR" else "donor-special (unreachable)"
        else:
            kind = "inherited"
        table.append(dict(motion=motion, name=name, subaction=sub, kind=kind))
    attack = {m: table[m]["kind"].startswith("own") for m in ATTACK_ROWS}
    donor = [k for k, v in entries.items() if v == "DONOR"]
    return dict(package=str(base), define=fighter["define"]["key"], attributes=sorted(fighter.get("attributes", {})),
                special_attributes=len(fighter.get("special_attributes", [])), rows=table, specials=entries,
                attack_rows_own=sum(attack.values()), attack_rows_total=len(attack),
                attack_rows_missing=[ATTACK_ROWS[m] for m, ok in attack.items() if not ok],
                donor_free=not donor and all(attack.values()),
                counts={k: sum(1 for r in table if r["kind"].split(" ")[0] == k) for k in ("own", "inherited", "donor-special")},
                overlays=len(overlays), states=sorted(states, key=states.get)), base, fighter


def frame_table(base, fighter):
    out = []
    for o in fighter.get("subactions", []):
        info = frames(overlay_words(base, o))
        out.append(dict(index=o["index"], tag=o.get("move_tag", ""), **info))
    return out


def text(report):
    lines = ["definition %s (%s)" % (report["define"], report["package"]),
             "attributes set: %d (%s)" % (len(report["attributes"]), ", ".join(report["attributes"])) if report["attributes"] else "attributes set: 0",
             "special attributes set: %d" % report["special_attributes"], "", "motion rows (0..350):"]
    for r in report["rows"]:
        if r["kind"] != "inherited":
            lines.append("  %3d %-24s %s" % (r["motion"], r["name"], r["kind"]))
    c = report["counts"]
    lines.append("  ... %d rows inherited, %d own, %d donor-special rows unreachable" % (c["inherited"], c["own"], c["donor-special"]))
    lines += ["", "special entries:"]
    for key, target in report["specials"].items():
        lines.append("  %-7s %s" % (key, target))
    lines += ["", "common attack rows owned: %d of %d%s" % (report["attack_rows_own"], report["attack_rows_total"],
              "" if not report["attack_rows_missing"] else "  (inherited: " + ", ".join(report["attack_rows_missing"]) + ")"),
              "donor-free (no DONOR special, every attack row own): %s" % ("yes" if report["donor_free"] else "NO")]
    return "\n".join(lines)


def frames_text(rows):
    lines = ["", "overlays (script frames; the hitbox is live from readout action frame N-2):"]
    for r in rows:
        boxes = "; ".join("slot%d j%d %s%% sz %.1f ang %s f%s-%s" % (b.get("slot", 0), b.get("joint", 0), b.get("damage", "?"), b.get("size", 0),
                          b.get("angle", "?"), b["start"], b.get("end", "?")) for b in r["hitboxes"])
        lines.append("  row %3d %-11s rate %-5s iasa %-4s %s" % (r["index"], r["tag"], r["rate"] if r["rate"] else "-", r["iasa"] if r["iasa"] is not None else "-", boxes))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("package")
    ap.add_argument("--frames", action="store_true", help="per-overlay hitbox windows, damage, angle, size and IASA frame")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report, base, fighter = build(args.package)
    if args.frames:
        report["frames"] = frame_table(base, fighter)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(text(report))
        if args.frames:
            print(frames_text(report["frames"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
