"""python -m tools.geno.artist <validate|build|run-command|clips> ...   (see README.md and docs/geno-artist-spec.md)"""
import argparse
import sys

from . import pipeline, spec, validate


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tools.geno.artist")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="check the character before building")
    v.add_argument("config")
    v.add_argument("--json", action="store_true")
    v.add_argument("-v", "--verbose", action="store_true")
    b = sub.add_parser("build", help="validate, convert, build, install into an isolated test mods folder")
    b.add_argument("config")
    b.add_argument("--out")
    b.add_argument("--export", action="store_true", help="re-export the glb from art.blend even if it is newer")
    b.add_argument("--strict", action="store_true", help="warnings stop the build too")
    n = sub.add_parser("new", help="scaffold a starter .blend and fighter.json")
    n.add_argument("dest")
    n.add_argument("--key", required=True)
    n.add_argument("--name")
    n.add_argument("--params", help="proportions / bone names / colours (blender/make_starter.py)")
    r = sub.add_parser("run-command", help="print the command that opens the fighter in the LAB")
    r.add_argument("config")
    r.add_argument("--out")
    c = sub.add_parser("clips", help="print the clip checklist (tiers, fallbacks)")
    c.add_argument("--tier", default="prototype,recommended,finished")
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        return validate.main([a.config] + (["--json"] if a.json else []) + (["-v"] if a.verbose else []))
    if a.cmd == "build":
        code, _ = pipeline.build(a.config, a.out, strict=a.strict, force_export=a.export)
        return code
    if a.cmd == "new":
        pipeline.new_character(a.dest, a.key, a.name or a.key.title(), a.params)
        return 0
    if a.cmd == "run-command":
        from . import model
        f = model.load(a.config)
        print(pipeline.run_command(f, pipeline.out_dir(f, a.out)))
        return 0
    if a.cmd == "clips":
        want = a.tier.split(",")
        for row in spec.clip_table()["rows"]:
            if row["tier"] in want:
                print("%-12s %-26s fallback: %s%s" % (row["tier"], row["name"], ", ".join(row.get("fallback", [])) or "-",
                                                      ("  [%s]" % ("loop" if row.get("loop") else "once")) if "loop" in row else ""))
        return 0


if __name__ == "__main__":
    sys.exit(main())
