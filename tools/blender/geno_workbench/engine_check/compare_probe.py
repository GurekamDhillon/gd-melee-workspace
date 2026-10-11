"""Compare a projectile probe log with the path the Blender add-on predicts (projectiles.trajectory).

    python compare_probe.py MELEE_LOG GAMEPLAY_JSON ARTICLE [--kind N]

The log rows come from projectile_probe/scripts/probe.lua:
    PROJPROBE spawn tick=T kind=K id=I px= py= x= y= vx= vy= facing=
    PROJPROBE f=T kind=K id=I x= y= vx= vy= alive=A
The first article of the kind is taken.  For each logged life frame A the engine position is compared with the
prediction at index A + shift; the shift (0 or 1: whether the first row is read before or after the first item tick)
with the smaller error is reported.  Prints COMPARE lines; exit 0 when the worst error is below --tol.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import projectiles as P  # noqa: E402

KV = re.compile(r"(\w+)=(-?[\d.]+|\w+)")


def rows(text, kind=None):
    spawn, frames = None, {}
    for line in text.splitlines():
        if "PROJPROBE" not in line:
            continue
        body = line.split("PROJPROBE", 1)[1].strip()
        data = {k: v for k, v in KV.findall(body)}
        if body.startswith("spawn"):
            if kind is not None and int(data["kind"]) != kind:
                continue
            if spawn is None:
                spawn = {k: float(v) if k not in ("facing",) else v for k, v in data.items()}
        elif body.startswith("f="):
            if spawn is None or int(data["id"]) != int(spawn["id"]):
                continue
            frames[int(data["alive"])] = (float(data["x"]), float(data["y"]), float(data["vx"]), float(data["vy"]))
    return spawn, frames


def compare(text, article, kind=None, facing=1):
    spawn, frames = rows(text, kind)
    if spawn is None or not frames:
        return None
    path = P.trajectory(article, base=(spawn["px"], spawn["py"]), facing=facing)
    best = None
    for shift in (0, 1, -1):
        errs = [max(abs(x - path[a + shift][0]), abs(y - path[a + shift][1]))
                for a, (x, y, _, _) in frames.items() if 0 <= a + shift < len(path)]
        if errs:
            worst = max(errs)
            if best is None or worst < best[1]:
                best = (shift, worst, len(errs))
    return {"spawn": spawn, "frames": len(frames), "max_alive": max(frames), "shift": best[0], "max_error": best[1],
            "compared": best[2], "first_v": frames[min(frames)][2:], "last": frames[max(frames)]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("log"); ap.add_argument("gameplay"); ap.add_argument("article")
    ap.add_argument("--kind", type=int)
    ap.add_argument("--tol", type=float, default=0.05)
    args = ap.parse_args(argv)
    doc = json.loads(Path(args.gameplay).read_text(encoding="utf-8"))
    arts = P.articles_of(doc)
    index = next(i for i, a in enumerate(arts) if a["name"] == args.article)
    result = compare(Path(args.log).read_text(encoding="utf-8", errors="replace"), arts[index],
                     args.kind if args.kind is not None else index)
    if result is None:
        print("COMPARE FAIL no probe rows for", args.article)
        return 1
    print("COMPARE article=%s frames_logged=%d max_alive=%d shift=%d max_error=%.4f first_velocity=%s" % (
        args.article, result["frames"], result["max_alive"], result["shift"], result["max_error"], result["first_v"]))
    ok = result["max_error"] <= args.tol and result["max_alive"] <= int(P.effective(arts[index], "lifetime"))
    print("COMPARE", "PASS" if ok else "FAIL", "lifetime=%s tol=%s" % (P.effective(arts[index], "lifetime"), args.tol))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
