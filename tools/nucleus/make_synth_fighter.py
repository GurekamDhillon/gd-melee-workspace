#!/usr/bin/env python3
"""Build a SYNTHETIC MexManager-style fighter zip from one fighter ACE ADDED, for tests and Proof 1.

    python -I tools/nucleus/make_synth_fighter.py --iso "$GW_ISO_ACE" --out _build/nucleus-synthf [--internal K] [--list]

Takes one m-ex ADDED fighter of the owner's ACE disc (its MxDt.dat rows, its Pl/AJ/costume files) and writes what a MexManager export holds:
`fighter.json` (name, soundBank, announcerCall, victoryTheme, fighterMusic1/2, items, costumes[{file{fileName,jointSymbol,materialSymbol,visibilityIndex}}],
files{fighterDataPath,fighterDataSymbol,animFile,animCount,effectFile}, functions{<MexManager key>: guest address}), the fighter and animation files, and one
`<costume>.zip` per costume. The function names are the keys GD's installer reads (tools/nucleus/fighter_compat.py shows the same set). Packed as
`<out>/synth-fighter.zip`.

DISC-DERIVED OUTPUT: it lives under the (git-ignored) --out folder and is never committed or uploaded. Read-only on the disc.
Attribution: consults m-ex's layout (tools/mex_port/mex_hsd.py, dump_mxdt.py), copies none of its code.
"""
import argparse, io, json, os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "mex_port"))
import mex_hsd as H  # noqa: E402
import dump_mxdt as D  # noqa: E402

# MexManager "functions" key -> Arch_FighterFunc slot (same table as gw_nucleus_fighter.h nf_cb_keys)
CB = ["onLoad", "onRespawn", "onDestroy", "moveLogicPointer", "specialN", "specialNAir", "specialS", "specialSAir", "specialHi", "specialHiAir",
      "specialLw", "specialLwAir", "onAbsorb", "onItemPickup", "onMakeItemInvisible", "onMakeItemVisible", "onItemDrop", "onItemCatch",
      "onUnknownItemRelated", "onApplyHeadItem", "onRemoveHeadItem", "eyeTextureDamaged", "eyeTextureNormal", "onFrame", "onActionStateChange",
      "resetAttribute", "onModelRender", "onShadowRender", "onUnknownMultijump", "onActionStateChangeWhileEyeTextureIsChanged1", "onTwoEntryTable1",
      "enterFloat", "enterDoubleJump", "enterTether", "onLanding", "onSmashF", "onSmashHi", "onSmashLw", "onExtRstAnim", "onIndexExtRstAnim",
      "demoMoveLogicPointer", "onIntroL", "onIntroR", "onAppeal", "onCatch", "getSwordTrail"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--internal", type=int, default=0, help="m-ex internal fighter id (default: the first added fighter whose files are on the disc)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    g = H.Gcm(a.iso)
    ar = H.Archive(g.read("MxDt.dat")).relocate(0)
    md = D.MexData(ar)
    meta = md.metadata()
    n_int, n_ext = meta["internal_id_count"], meta["external_id_count"]
    f = {n: md.fighter_field(n) for n in D.FIGHTER_FIELDS}
    names_on_disc = {p.split("/")[-1] for p in g.files}

    def cstr(p):
        return ar.cstr(p) if p and ar.in_data(p) else None

    def ptr(p):
        return ar.u32(p) if ar.in_data(p) else 0

    ext_of = {}
    for e in range(n_ext):
        ext_of.setdefault(ar.u8(f["ft_kind_desc"] + e * 3), e)
    ff = md.root["fighter_function"]
    slots = [ar.u32(ff + s * 4) for s in range(46)]
    cands = []
    for k in range(27, n_int - 6):
        pl = cstr(ptr(f["pl_file"] + k * 8))
        if pl and pl in names_on_disc and k in ext_of:
            cands.append((k, ext_of[k], pl, cstr(ptr(f["names"] + ext_of[k] * 4))))
    if a.list:
        for c in cands:
            print(c)
        return 0
    pick = [c for c in cands if not a.internal or c[0] == a.internal][:1]
    if not pick:
        print("no such added fighter with a file on the disc", file=sys.stderr)
        return 1
    k, e, pl, name = pick[0]
    sym = cstr(ptr(f["pl_file"] + k * 8 + 4))
    anim = cstr(ptr(f["anim_filenames"] + k * 4))
    ncost = ar.u8(f["costume_info"] + e * 4)
    cf = ptr(f["costume_file"] + k * 4)
    costumes = []
    for c in range(ncost):
        row = cf + c * 16
        costumes.append({"name": "C%d" % c, "file": {"fileName": cstr(ptr(row)), "jointSymbol": cstr(ptr(row + 4)),
                                                      "materialSymbol": cstr(ptr(row + 8)), "visibilityIndex": ar.s32(row + 12)}})
    ssm = ar.u8(f["ssm_files"] + e * 0x10)
    music = ar.u32(f["fighter_music"] + e * 4)
    il = ptr(f["item_lookup"]) if False else f["item_lookup"] + k * 8
    n_items = ar.s32(il)
    fn = {"version": 0}
    for s, key in enumerate(CB):
        fn[key] = ar.u32(slots[s] + k * 4) if slots[s] else 0
    js = {
        "name": name, "seriesID": 11, "soundBank": ssm, "announcerCall": ar.s32(f["announcer_call"] + e * 4),
        "victoryTheme": ar.s32(f["victory_theme"] + e * 4), "fighterMusic1": music >> 16, "fighterMusic2": music & 0xFFFF,
        "items": [{}] * max(0, n_items), "costumes": costumes, "kirbyCostumes": [], "hasKirbyCostumes": False,
        "files": {"fighterDataPath": pl, "fighterDataSymbol": sym, "animFile": anim, "animCount": ar.s32(f["anim_num"] + k * 8 + 4),
                  "effectFile": "", "demoFile": "", "demoWait": "", "demoResult": "", "demoIntro": "", "demoEnding": ""},
        "functions": fn, "moveLogic": [],
    }
    os.makedirs(a.out, exist_ok=True)
    zp = os.path.join(a.out, "synth-fighter.zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("fighter.json", json.dumps(js, indent=2))
        z.writestr(pl, g.read(pl))
        z.writestr(anim, g.read(anim))
        for c in costumes:
            fnm = c["file"]["fileName"]
            if fnm and fnm in names_on_disc:
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as cz:
                    cz.writestr(fnm, g.read(fnm))
                z.writestr(fnm.rsplit(".", 1)[0] + ".zip", buf.getvalue())
    bad = [k2 for k2, v in fn.items() if isinstance(v, int) and v >= 0x100000 and not (0x80000000 <= v < 0x81800000)]
    print("wrote %s from ACE internal %d ext %d %s (%s) %d costumes, bank %d, %d items, %d callbacks outside the retail range"
          % (zp, k, e, pl, name, ncost, ssm, n_items, len(bad)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
