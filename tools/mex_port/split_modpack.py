#!/usr/bin/env python3
"""Split a whole-disc mod pack into per-entity mods: one per added fighter, one per added stage,
plus the shared base they all require.

    python tools/mex_port/split_modpack.py --pack _build/packs/ace-set/ace --name ace --version 2.0.0
    python tools/mex_port/split_modpack.py --pack _build/packs/akaneia-set/akaneia --name akaneia \\
        --version 1.0.1 --enable akaneia-base,akaneia-sonic

Input: a pack folder as tools/mex_port/make_mod_from_disc.py writes it (the files a mod disc adds
to or changes on a vanilla disc, MxDt.dat among them). Output (default _build/mods-split/<name>/):
a mods folder the port reads directly (MELEE_MODS_DIR=<out>), laid out as gw_mods.h describes:

    <out>/<name>-base/mod.json + files/...     kind "base": MxDt.dat, menus, PlCo.dat, shared
                                               banks and music, everything not claimed below
    <out>/<name>-<fighter>/mod.json + files/   kind "fighter", requires <name>-base
    <out>/<name>-stage-<name>/mod.json + files/ kind "stage", requires <name>-base (MxDt stage name)

WHAT GOES WHERE, from MxDt.dat (never from file-name guesses alone):
  fighter (every m-ex fighter row with a Pl file - internal ids 27..n-7): its Pl file, animation
    file, costume files, result-screen file, demo files named by its ftDemo symbols, effect bank,
    sound bank, Kirby copy file and Kirby copy effect bank, ending movies/videos, and the Target
    Test stage its row names.
  stage (every stage-select icon naming an added stage, external id >= 33): its Gr file.
  A file two entities both claim (Wolf and Wolf SSBU share a result file; B. Falcon uses
  Captain Falcon's sound bank) stays in the base, so disabling one never breaks the other.

Why this is safe to disable piecemeal: the port builds its fighter slot table from the Pl files
that are present (gw_mex_slots_build) and its stage rows from the Gr files that are present
(gw_Mex_GrFile / gw_Mex_GrIsMex), so a row whose entity mod is off simply is not offered. The
base still carries the full MxDt.dat; see docs/mods-packaging.md for what that costs.

Files are HARD-LINKED from the pack when possible (same volume), else copied. Output is disc-derived
data - it lives under _build/ and must never be committed. Re-running replaces <out>/<name>-*.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dump_mxdt as d  # noqa: E402
from mex_hsd import Archive  # noqa: E402

FIRST_NEW_FIGHTER = 27     # m-ex internal ids 27.. are added fighters; the last six are bosses
FIRST_NEW_STAGE_EXT = 33   # external stage ids below this are retail (or retail Target Tests)
FIRST_NEW_STAGE_INT = 71   # GW_MEX_GR_FIRST_NEW
EFFECT_STRIDE = 12         # mexData.effect word 0: {char *file; char *symbol; u32 flags}
SSS_STRIDE = 0x20          # gw_mex_sss.h
SSS_EXT_OFF = 0x1C
STAGE_IDS_STRIDE = 12      # Arch_Map_StageIDs, word 0 = internal id
STAGE_ROW_FILE = 8         # StageData row word 2 = char *file


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "unnamed"


class Tables:
    def __init__(self, mxdt_path):
        raw = open(mxdt_path, "rb").read()
        self.ar = Archive(raw).relocate(0)
        self.md = d.MexData(self.ar)
        self.meta = self.md.metadata()

    def ptr(self, p):
        return self.ar.u32(p) if 0 < p and p + 4 <= len(self.ar.data) else 0

    def cstr(self, p):
        if not p or p >= len(self.ar.data):
            return None
        s = bytes(self.ar.data[p:p + 96]).split(b"\0")[0]
        try:
            s = s.decode("ascii")
        except UnicodeDecodeError:
            return None
        return s if s and all(32 <= ord(c) < 127 for c in s) else None

    def ff(self, name):
        return self.md.fighter_field(name)

    def ext_of_internal(self):
        """ft_kind_desc: per EXTERNAL id, 3 bytes {internal, extra, transform}; first ext wins."""
        out = {}
        base = self.ff("ft_kind_desc")
        for e in range(self.meta["external_id_count"]):
            out.setdefault(self.ar.u8(base + e * 3), e)
        return out

    def effect_file(self, eid):
        if eid is None or eid == 0xFF:
            return None
        t = self.ptr(self.md.root["effect"])
        return self.cstr(self.ptr(t + eid * EFFECT_STRIDE)) if t else None

    def ssm_file(self, sid):
        t = self.ptr(self.md.root["ssm"])  # ssm +0: char *Files[]
        name = self.cstr(self.ptr(t + sid * 4)) if t and sid is not None else None
        return "audio/us/" + name if name else None

    def stage_file_for_ext(self, ext):
        ids = self.ptr(self.md.root["stage"])
        if not ids or ext < 0 or ext >= self.meta["external_stage_count"]:
            return None, None
        g = self.ar.s32(ids + ext * STAGE_IDS_STRIDE)
        if g < 0 or g >= self.meta["internal_stage_count"]:
            return None, None
        row = self.ptr(self.md.root["stage_desc"] + g * 4)
        return g, (self.cstr(self.ptr(row + STAGE_ROW_FILE)) if row else None)

    def stage_name(self, g):
        """Arch_Map +0x10: stage names by INTERNAL id (m-ex's MXDT_GRNAME)."""
        names = self.ptr(self.md.root["stage"] + 0x10)
        return self.cstr(self.ptr(names + g * 4)) if names and g is not None else None

    def sss_exts(self):
        menu = self.md.root["menu"]  # mexData +0x04, already a data offset
        tbl = self.ptr(menu + 0x08)
        out = []
        for i in range(self.meta["sss_icon_count"]):
            out.append(self.ar.s32(tbl + i * SSS_STRIDE + SSS_EXT_OFF))
        return out


def fighter_claims(t, k, e):
    """-> (name, [disc paths]) for m-ex internal fighter k (external e)."""
    files = []
    pl = t.cstr(t.ptr(t.ff("pl_file") + k * 8))
    if not pl:
        return None, []
    files.append(pl)
    files.append(t.cstr(t.ptr(t.ff("anim_filenames") + k * 4)))
    name = t.cstr(t.ptr(t.ff("names") + e * 4)) if e is not None else None
    if e is not None:
        ncost = t.ar.u8(t.ff("costume_info") + e * 4)
        cf = t.ptr(t.ff("costume_file") + k * 4)
        for c in range(ncost if cf else 0):
            files.append(t.cstr(t.ptr(cf + c * 16)))
        for fld in ("result_file", "vi_files", "endclassicfiles", "endadventurefiles",
                    "endallstarfiles", "endmoviefiles"):
            files.append(t.cstr(t.ptr(t.ff(fld) + e * 4)))
        files.append(t.ssm_file(t.ar.u8(t.ff("ssm_files") + e * 0x10)))
        tt_ext = t.ar.u16(t.ff("target_test_lookup") + e * 2)
        g, gr = t.stage_file_for_ext(tt_ext)
        if gr and g is not None and g >= FIRST_NEW_STAGE_INT:
            files.append(gr)
    demo = t.ptr(t.ff("ftdemo") + k * 4)
    for i in range(4):
        sym = t.cstr(t.ptr(demo + i * 4)) if demo else None
        if sym:
            files.append(sym + ".dat")
    files.append(t.effect_file(t.ar.u8(t.ff("effect_index") + k)))
    kd = t.md.root["kirby_data"]
    cap = t.ptr(kd + 0x00)
    files.append(t.cstr(t.ptr(cap + k * 8)) if cap else None)
    kef = t.ptr(kd + 0x10)
    files.append(t.effect_file(t.ar.u8(kef + k)) if kef else None)
    return name or pl, [f.lstrip("/") for f in files if f]


def pack_index(pack):
    """lower-case disc path -> real relative path, for every file in the pack."""
    idx = {}
    for dp, _, fns in os.walk(pack):
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), pack).replace("\\", "/")
            idx[rel.lower()] = rel
    return idx


def resolve(idx, path):
    """A claimed disc path -> the pack's relative paths it names ([] when not in the pack). A
    stage name without an extension is a prefix: <p>.dat, <p>.usd, <p>1..9.dat."""
    p = path.lstrip("/").lower()
    if p in idx:
        return [idx[p]]
    if "." not in os.path.basename(p):
        cands = [p + ".dat", p + ".usd"] + [f"{p}{i}.dat" for i in range(1, 10)]
        return [idx[c] for c in cands if c in idx]
    return []


def place(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--pack", required=True, help="pack folder (contains MxDt.dat)")
    ap.add_argument("--name", required=True, help="short pack name, the id prefix (ace, akaneia)")
    ap.add_argument("--version", default="", help="the mod build's version, recorded in mod.json")
    ap.add_argument("--out", default=None, help="mods folder to write (default _build/mods-split/<name>)")
    ap.add_argument("--enable", default=None,
                    help="comma-separated ids to write into <out>/enabled.txt (default: leave it)")
    ap.add_argument("--dry-run", action="store_true", help="print the split, write nothing")
    args = ap.parse_args()

    pack = os.path.abspath(args.pack)
    mxdt = os.path.join(pack, "MxDt.dat")
    if not os.path.isfile(mxdt):
        print(f"split_modpack: no MxDt.dat in {pack}", file=sys.stderr)
        return 1
    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    out = os.path.abspath(args.out or os.path.join(root, "_build", "mods-split", args.name))
    t = Tables(mxdt)
    idx = pack_index(pack)
    manifest = {}
    mpath = pack.rstrip("\\/") + ".gdm_pack.json"
    if os.path.isfile(mpath):
        manifest = json.load(open(mpath, encoding="utf-8")).get("files", {})

    entities = []  # (id, kind, name, [pack rel paths])
    ext_of = t.ext_of_internal()
    n_int = t.meta["internal_id_count"]
    for k in range(FIRST_NEW_FIGHTER, n_int - 6):
        name, claims = fighter_claims(t, k, ext_of.get(k))
        if not claims:
            continue
        files = sorted({r for c in claims for r in resolve(idx, c)})
        if not any(f.lower() == claims[0].lower() for f in files):
            print(f"  skip fighter {k} {name}: its {claims[0]} is not in the pack")
            continue
        entities.append((f"{args.name}-{slug(name)}", "fighter", name, files))
    seen_ext = set()
    for ext in t.sss_exts():
        if ext < FIRST_NEW_STAGE_EXT or ext in seen_ext:
            continue
        seen_ext.add(ext)
        g, gr = t.stage_file_for_ext(ext)
        if not gr or g is None or g < FIRST_NEW_STAGE_INT:
            continue
        files = sorted(set(resolve(idx, gr)))
        if not files:
            print(f"  skip stage ext {ext} {gr}: not in the pack")
            continue
        stem = os.path.splitext(os.path.basename(gr.lstrip("/")))[0]
        title = t.stage_name(g) or stem
        entities.append((f"{args.name}-stage-{slug(title)}", "stage", title, files))

    # ids must be unique: suffix duplicates (two rows sharing a display name)
    seen = {}
    for i, (eid, kind, name, files) in enumerate(entities):
        if eid in seen:
            seen[eid] += 1
            entities[i] = (f"{eid}-{seen[eid]}", kind, name, files)
        else:
            seen[eid] = 1

    # a file claimed twice stays in the base
    owners = {}
    for eid, _, _, files in entities:
        for f in files:
            owners.setdefault(f, set()).add(eid)
    shared = {f for f, o in owners.items() if len(o) > 1}
    claimed = {f for f in owners if f not in shared}
    base_id = f"{args.name}-base"
    mods = [(base_id, "base", f"{args.name.upper()} base", sorted(set(idx.values()) - claimed))]
    for eid, kind, name, files in entities:
        own = [f for f in files if f not in shared]
        mods.append((eid, kind, name, own))

    total = 0
    for eid, kind, name, files in mods:
        size = sum(os.path.getsize(os.path.join(pack, f)) for f in files)
        total += size
        print(f"{eid:34} {kind:8} {len(files):4} files {size / 1e6:9.1f} MB  {name}")
    print(f"{len(mods)} mods ({len(entities)} entities), {len(shared)} shared files kept in the base, "
          f"{total / 1e6:.1f} MB")
    if args.dry_run:
        return 0

    os.makedirs(out, exist_ok=True)
    for dn in os.listdir(out):  # replace what a previous run of THIS pack wrote
        if dn.lower().startswith(args.name.lower() + "-") and os.path.isdir(os.path.join(out, dn)):
            shutil.rmtree(os.path.join(out, dn))
    for eid, kind, name, files in mods:
        mdir = os.path.join(out, eid)
        h = hashlib.sha256()
        for f in sorted(files, key=str.lower):
            place(os.path.join(pack, f), os.path.join(mdir, "files", *f.split("/")))
            digest = manifest.get(f, {}).get("sha256")
            if digest is None:
                with open(os.path.join(pack, f), "rb") as fp:
                    digest = hashlib.sha256(fp.read()).hexdigest()
            h.update(f"{f.lower()}:{digest}\n".encode())
        meta = {
            "id": eid,
            "name": name,
            "version": args.version,
            "kind": kind,
            "pack": args.name,
            "description": (f"{args.name.upper()} shared data: m-ex tables (MxDt.dat), menus, common "
                            f"fighter data, shared banks and music. Every {args.name} fighter and stage "
                            f"mod requires it." if kind == "base" else
                            f"{name} from {args.name.upper()} {args.version}".strip()),
            "requires": [] if kind == "base" else [base_id],
            "conflicts": [],
            "hash": h.hexdigest()[:32],
            "files": len(files),
        }
        with open(os.path.join(mdir, "mod.json"), "w", encoding="utf-8", newline="\n") as fp:
            json.dump(meta, fp, indent=2)
            fp.write("\n")
    if args.enable is not None:
        ids = [s.strip() for s in args.enable.split(",") if s.strip()]
        with open(os.path.join(out, "enabled.txt"), "w", encoding="utf-8", newline="\n") as fp:
            fp.write("# written by split_modpack.py\n")
            for i in ids:
                fp.write(i + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
