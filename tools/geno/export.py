"""Export editable move scripts from the user's disc to an external directory."""
import argparse
import json
import os
from pathlib import Path
import re
import struct
import sys
from . import script, schema

HEADER = "# Derived from the user's own disc image; must not be shared or committed.\n"


def safe_output(path):
    path = Path(path).resolve()
    if path.is_relative_to(schema.ROOT.resolve()):
        raise ValueError("disc-derived output must be outside both repositories, including _build; give an external --out path")
    return path


def write_scripts(scripts, out):
    out = safe_output(out)
    pending = []
    for name, words in scripts.items():
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError("unsafe output name")
        pending.append((out / (name + ".genoasm"), HEADER + script.disassemble(words)))
    for path, _ in pending:
        if path.exists():
            raise ValueError("export would overwrite an existing file; choose a fresh directory")
    out.mkdir(parents=True, exist_ok=True)
    for path, text in pending:
        path.write_text(text, encoding="utf-8")


def disc_path(iso=None, variable="GW_ISO_VANILLA"):
    if iso:
        return iso
    value = os.environ.get(variable)
    if value:
        return value
    env = schema.ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"\s*(?:export\s+)?" + re.escape(variable) + r"\s*=\s*(.*?)\s*$", line)
            if m:
                value = m[1].strip()
                if value.startswith(('"', "'")) and value.endswith(value[0]):
                    return value[1:-1]
                return value.split(" #", 1)[0].strip()
    raise ValueError(f"set {variable} or pass --iso (the image path is never logged)")


def read_script(archive, start):
    words = []
    offset = start
    for _ in range(2000):  # scan_ftcmd_opcodes.py walk guard
        if offset < 0 or offset + 4 > archive.data_size or offset % 4:
            raise ValueError("script points outside archive data or is unaligned")
        first = archive.u32(offset)
        op = first >> 26
        if op > 59:
            raise ValueError(f"unsupported opcode {op}")
        if op in (5, 7):
            raise ValueError("Subroutine/Goto uses relocated archive pointers; portable overlay export is unsupported for this row")
        if op == 6:
            raise ValueError("standalone Return has no portable caller")
        length = max(1, first >> 16 & 15) if op == 59 else script.LENGTHS[op]
        if offset + 4 * length > archive.data_size:
            raise ValueError("truncated archive script")
        words.extend(archive.u32(offset + 4 * i) for i in range(length))
        offset += length * 4
        if op == 0:
            script.disassemble(words)
            return words
    raise ValueError("script has no End within the reader's 2000-command safety bound")


def read_fighter(disc, fighter, rows, *, archive_factory=None, table_kind="action"):
    from tools.mex_port.mex_hsd import Archive
    archive_factory = archive_factory or Archive
    filename = schema.S["vanilla"].get(fighter.lower(), fighter)
    if not re.fullmatch(r"Pl[^/\\]+\.(dat|usd)", filename, re.I):
        raise ValueError("fighter must be a vanilla name/alias or an exact Pl*.dat archive on the disc")
    ar = archive_factory(disc.read(filename))
    roots = [off for name, off in ar.publics if name.startswith("ftData") and not name.startswith("ftDataKirbyCopy")]
    if table_kind == "ftcmd":
        tables = [off for name, off in ar.publics if name == "ftcmd"]
    elif len(roots) == 1:
        pointer = roots[0] + (0x0C if table_kind == "action" else 0x14)
        tables = [ar.u32(pointer)] if pointer in ar.reloc_set else []
    else:
        tables = []
    if len(tables) != 1:
        raise ValueError("fighter table is absent or ambiguous; supported layouts: ftData+0x0C action, +0x14 demo, or public ftcmd")
    base = tables[0]
    scripts, manifest = {}, []
    for row in rows:
        row = script.integer(row, 0, 1023)
        off = base + row * 0x18
        if off + 0x18 > ar.data_size:
            raise ValueError(f"row {row} lies outside the archive")
        if off not in ar.reloc_set or off + 0xC not in ar.reloc_set:
            raise ValueError(f"row {row} has no relocated animation name and script; empty/custom table layouts cannot be guessed")
        anim = ar.cstr(ar.u32(off))
        if not anim or not re.search(r"(?:ACTION|figatree)", anim):
            raise ValueError(f"row {row} does not look like a fighter animation row")
        key = f"{table_kind}-row-{row}"
        scripts[key] = read_script(ar, ar.u32(off+0xC))
        manifest.append({"row": row, "table": table_kind, "animation": anim,
                         "text": key + ".genoasm", "derived_from_user_disc": True})
    return scripts, manifest


def main():
    if "--package" in sys.argv:
        from .define import export_package
        ap = argparse.ArgumentParser(description="Export a source-only Geno definition package")
        ap.add_argument("--package", required=True, type=Path)
        ap.add_argument("--out", required=True, type=Path)
        args = ap.parse_args()
        try:
            export_package(args.package, args.out)
            print("Exported offline definition package and SHA-256 manifest.")
            return 0
        except (ValueError, OSError):
            print("Package export refused: invalid definition, unsafe payload or output unavailable.")
            return 1
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fighter", help="vanilla name/alias or exact Pl*.dat filename")
    ap.add_argument("--row", required=True, action="append", type=lambda x: int(x, 0))
    ap.add_argument("--table", choices=("action", "demo", "ftcmd"), default="action")
    ap.add_argument("--iso", help="own disc image (never printed)")
    ap.add_argument("--disc", choices=("vanilla", "akaneia", "ace"), default="vanilla")
    ap.add_argument("--out", required=True, type=Path, help="fresh directory OUTSIDE both repositories")
    args = ap.parse_args()
    try:
        out = safe_output(args.out)
        from tools.mex_port.mex_hsd import Gcm
        # Errors from Gcm may contain the private image path. Do not relay them.
        try:
            disc = Gcm(disc_path(args.iso, "GW_ISO_" + args.disc.upper()))
            scripts, manifest = read_fighter(disc, args.fighter, args.row, table_kind=args.table)
        except (OSError, KeyError, ValueError, struct.error, IndexError) as e:
            if isinstance(e, ValueError) and not isinstance(e, UnicodeError):
                # Own reader errors never include image paths; third-party errors may.
                message = str(e)
                if any(s in message for s in (".iso", ".gcm", "[Errno", ":\\", ":/")):
                    message = "disc/archive could not be read; check the image and fighter/table selection"
            else:
                message = "disc/archive could not be read; check the image and fighter/table selection"
            raise ValueError(message) from None
        manifest_path = out / "manifest.json"
        if manifest_path.exists():
            raise ValueError("manifest already exists; choose a fresh output directory")
        write_scripts(scripts, out)
        manifest_path.write_text(json.dumps({"notice": HEADER[2:].strip(), "rows": manifest}, indent=2) + "\n", encoding="utf-8")
        print(f"Exported {len(scripts)} script(s) outside the repositories. Disc-derived text must not be shared.")
        return 0
    except (ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
