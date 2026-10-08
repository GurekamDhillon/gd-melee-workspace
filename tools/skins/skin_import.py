#!/usr/bin/env python3
"""Turn costume DATs (.dat/.usd) into skin mod folders, or lint one. See README.md.

    skin_import.py INPUT [--out MODS_DIR] [--id ID] [--name NAME] [--target retail:fox|mex:PlWf.dat|geno:KEY]
                   [--joint S] [--matanim S] [--csp a.png] [--stock b.png] [--team red|blue|green] [--author A]
    skin_import.py INPUT_MOD_DIR --lint-only

INPUT is one costume file or a folder of them (one skin mod per file; the id comes from the file stem).
Nothing here reads or writes a disc image.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skinlib  # noqa: E402

REFUSE_PARTNER = ("Ice Climbers / Sheik costumes belong with Popo / Zelda: target popo or zelda "
                  "and pass the partner with the main one")
PARTNER_ONLY = ("seak", "nana")
COSTUME_EXT = (".dat", ".usd")
DISC_EXT = (".iso", ".gcm", ".ciso", ".wbfs", ".gcz", ".rvz")
TARGET_KINDS = ("retail", "mex", "geno")


def parse_target(s):
    kind, sep, value = s.partition(":")
    if not sep or kind not in TARGET_KINDS or not value:
        raise argparse.ArgumentTypeError("--target is retail:NAME, mex:PlWf.dat or geno:KEY")
    return {kind: value}


def slug(stem):
    return re.sub(r"[^a-z0-9_-]+", "-", stem.lower()).strip("-")


def ascii_name(s):
    """Printable ASCII only, 23 characters at most; never empty."""
    kept = "".join(ch for ch in s if 0x20 <= ord(ch) <= 0x7E).strip()
    return kept[:skinlib.NAME_MAX] or "Costume"


def import_one(path, args, mod_id, name):
    with open(path, "rb") as fp:
        raw = fp.read()

    if args.target is None:
        info = skinlib.classify_costume(raw)
        target = {"retail": info["fighter"]}
        joint, matanim = info["joint"], info["matanim"]
    else:
        target = args.target
        try:
            sym = skinlib.costume_symbols(raw)
            found_joint, found_matanim = sym["joint"], sym["matanim"]
        except ValueError:
            if not args.joint:
                raise ValueError("no Ply<Fighter>5K<Colour>_Share_joint symbol in the file; "
                                 "pass --joint (and --matanim)") from None
            found_joint, found_matanim = None, None
        joint = args.joint or found_joint
        matanim = args.matanim or found_matanim
        if joint is None:
            raise ValueError("no joint symbol: pass --joint")

    if target.get("retail") in PARTNER_ONLY:
        raise ValueError(REFUSE_PARTNER)

    if not skinlib.MOD_ID.match(mod_id):
        raise ValueError(f"mod id {mod_id!r} is not usable: pass --id (lowercase letters, digits, - _)")

    costume = dict(name=ascii_name(name), src_dat=path, joint=joint, matanim=matanim,
                   team=args.team, csp_png=args.csp, stock_png=args.stock)
    mod_dir = skinlib.write_skin_mod(args.out, mod_id, name, target, [costume], authors=args.author)
    problems = skinlib.lint_skin_mod(mod_dir)
    if problems:
        raise ValueError("written mod does not lint: " + "; ".join(problems))
    kind, value = next(iter(target.items()))
    print(f"skin {mod_id}: {kind}:{value} {name}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Import costume DATs as skin mods, or lint a skin mod.")
    ap.add_argument("input", help="a costume file, a folder of them, or (with --lint-only) a mod folder")
    ap.add_argument("--out", default="mods", help="mods folder to write into (default ./mods)")
    ap.add_argument("--id", help="mod id (single file only)")
    ap.add_argument("--name", help="display name (single file only)")
    ap.add_argument("--target", type=parse_target,
                    help="retail:fox | mex:PlWf.dat | geno:KEY (default: classify the DAT as a retail fighter)")
    ap.add_argument("--joint", help="joint symbol, when the DAT does not carry a Ply symbol")
    ap.add_argument("--matanim", help="matanim symbol, with --joint")
    ap.add_argument("--csp", help="CSP PNG (single file only)")
    ap.add_argument("--stock", help="stock icon PNG, 24x24 (single file only)")
    ap.add_argument("--team", choices=skinlib.TEAMS)
    ap.add_argument("--author", default="")
    ap.add_argument("--lint-only", action="store_true", help="lint INPUT as a skin mod folder")
    args = ap.parse_args(argv)

    if args.lint_only:
        problems = skinlib.lint_skin_mod(args.input)
        for p in problems:
            print(p)
        if problems:
            return 1
        print("clean")
        return 0

    if args.input.lower().endswith(DISC_EXT):
        ap.error("refusing a disc image: give a costume .dat or .usd")

    if os.path.isdir(args.input):
        if args.id or args.name or args.csp or args.stock:
            ap.error("--id, --name, --csp and --stock apply to a single file, not a folder")
        files = sorted(os.path.join(args.input, n) for n in os.listdir(args.input)
                       if n.lower().endswith(COSTUME_EXT))
        if not files:
            ap.error(f"no .dat or .usd files in {args.input}")
        single = False
    else:
        files = [args.input]
        single = True

    rc = 0
    seen = set()
    for path in files:
        stem = os.path.splitext(os.path.basename(path))[0]
        mod_id = args.id if single and args.id else slug(stem)
        name = args.name if single and args.name else stem
        try:
            if mod_id in seen:
                raise ValueError(f"two files give the id {mod_id!r}")
            seen.add(mod_id)
            import_one(path, args, mod_id, name)
        except (ValueError, RuntimeError, OSError) as e:
            print(f"skin_import: {path}: {e}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
