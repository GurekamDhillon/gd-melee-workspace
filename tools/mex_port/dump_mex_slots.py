#!/usr/bin/env python3
"""Reconcile an m-ex disc's MxDt.dat against the port's m-ex fighter slot table (read-only).

    python tools/mex_port/dump_mex_slots.py --iso "C:/iso/SSBM ACE Build v2.0.0.iso"
    python tools/mex_port/dump_mex_slots.py --iso C:/iso/Akaneia.iso --compare "C:/iso/ACE.iso"

Reproduces, offline, exactly what `gw_mex_slots_build()` (pc/platform/gw_mex_ftfunction_runtime.c)
does at runtime: walk m-ex INTERNAL ids from GW_MEX_FIRST_NEW (27) up to internal_id_count - 6
(m-ex keeps the six retail bosses last), skip rows with no `Pl` file or whose `Pl` file is not on
the disc, and hand each surviving row the next dense port slot.

FOUR index spaces appear here and every column says which one it is:
  mex_int  - m-ex INTERNAL fighter id       (pl_file, costume_file, ftdemo, anim_*, item_lookup)
  mex_ext  - m-ex EXTERNAL id               (names, costume_info, ssm, result_file)
  port_Ft  - the port's FighterKind         (Ft_Kind_Mex0 0x21 + slot)
  port_Ch  - the port's CharacterKind       (ChKind_Mex0 0x22 + slot)

Also reports, per fighter, what an import has to supply: clone base, ftFunction code size and
override count, debug-symbol count, effect-bank index, costume count and article count.

Nothing is written; every ISO is opened read-only.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mex_hsd import Archive, Gcm  # noqa: E402
import dump_mxdt as d  # noqa: E402

GW_MEX_FIRST_NEW = 27  # gw_mex_ftfunction_runtime.c
GW_MEX_SLOTS = 31      # gw_mex_ftfunction_runtime.c / Ft_Kind_None - Ft_Kind_Mex0
PORT_FT_MEX0 = 0x21
PORT_CK_MEX0 = 0x22
N_RETAIL_BOSSES = 6

RETAIL = ["Mario", "Fox", "Captain", "DK", "Kirby", "Koopa", "Link", "Sheik", "Ness", "Peach",
          "Popo", "Nana", "Pikachu", "Samus", "Yoshi", "Purin", "Mewtwo", "Luigi", "Mars",
          "Zelda", "CLink", "DrMario", "Falco", "Pichu", "GameWatch", "Ganon", "Emblem"]


class Disc:
    def __init__(self, iso):
        self.gcm = Gcm(iso)
        self.basenames = {os.path.basename(p): p for p in self.gcm.files}
        self.ar = Archive(self.gcm.read("MxDt.dat"))
        self.md = d.MexData(self.ar)
        self.meta = self.md.metadata()
        self.n_int = self.meta["internal_id_count"]
        self.n_ext = self.meta["external_id_count"]
        self.f = {name: self.md.fighter_field(name) for name in d.FIGHTER_FIELDS}
        self.ext_of = {}
        for e in range(self.n_ext):
            self.ext_of.setdefault(self.ar.u8(self.f["ft_kind_desc"] + e * 3), e)
        ff = self.md.root["fighter_function"]
        self.slot_tables = []
        for s in range(46):
            t = self.ar.u32(ff + s * 4)
            if t == 0 or t >= len(self.ar.data):
                break
            self.slot_tables.append(t)
        self.onload = [self.ar.u32(self.slot_tables[0] + k * 4) for k in range(self.n_int)]
        self.retail_by_onload = {}
        for k in range(GW_MEX_FIRST_NEW):
            self.retail_by_onload.setdefault(self.onload[k], k)
        self._items = self.md.item_lookup(self.f["item_lookup"], self.n_int)

    def pl(self, k):
        p = self.f["pl_file"] + k * 8
        return self.ar.cstr(self.ar.u32(p)), self.ar.cstr(self.ar.u32(p + 4))

    def name(self, k):
        e = self.ext_of.get(k)
        return (e, self.ar.cstr(self.ar.u32(self.f["names"] + e * 4)) if e is not None else None)

    def anim_count(self, k):
        """anim_num is STRIDE 8 with the count in the SECOND word (the first is always 0).

        Proven from the data, not from mxdt.h: on both discs every +0 word is zero and carries no
        relocation, and the six retail bosses' counts (345, 344, 295, 295, 316, 296) sit at
        internal 35..40 on Akaneia and at 59..64 on ACE - they move with internal_id_count exactly
        as a stride-8 per-internal-kind array must. A stride-4 read returns 0 for every even
        internal kind and another fighter's count for every odd one.
        """
        return self.ar.u32(self.f["anim_num"] + k * 8 + 4)

    def effect_index(self, k):
        return self.ar.data[self.f["effect_index"] + k]  # u8 array, stride 1

    def costume_count(self, k):
        e = self.ext_of.get(k)
        return self.ar.u8(self.f["costume_info"] + e * 4) if e is not None else 0

    def article_count(self, k):
        return self._items[k][1]

    def ftfunction(self, pl):
        """(code_size, n_overrides, n_debug_symbols, derived_code_size, has_itFunction)."""
        a = Archive(self.gcm.read(self.basenames[pl]))
        pubs = dict(a.publics)
        if "ftFunction" not in pubs:
            return (None, 0, 0, 0, "itFunction" in pubs)
        a.relocate(0)
        h = pubs["ftFunction"]
        irt, n_irt = a.u32(h + 0x04), a.u32(h + 0x08)
        derived = 0
        for i in range(n_irt):
            derived = max(derived, (a.u32(irt + i * 8) & 0x00FFFFFF) + 4)
        return (a.u32(h + 0x14), a.u32(h + 0x10), a.u32(h + 0x18), derived, "itFunction" in pubs)


def verdict(n_wanted):
    if n_wanted > GW_MEX_SLOTS:
        return "DOES NOT FIT - %d over" % (n_wanted - GW_MEX_SLOTS)
    if n_wanted == GW_MEX_SLOTS:
        return "FITS EXACTLY, 0 spare"
    return "FITS, %d spare" % (GW_MEX_SLOTS - n_wanted)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iso", required=True, help="the m-ex disc to reconcile (read-only)")
    ap.add_argument("--compare", help="a second m-ex disc; marks which Pl files it also ships")
    args = ap.parse_args()

    disc = Disc(args.iso)
    other = None
    if args.compare:
        o = Disc(args.compare)
        other = set(x for x in (o.pl(k)[0] for k in range(o.n_int)) if x)

    hi = disc.n_int - N_RETAIL_BOSSES
    print("%s: internal_id_count %d, external_id_count %d, css_icon_count %d"
          % (os.path.basename(args.iso), disc.n_int, disc.n_ext, disc.meta["css_icon_count"]))
    print("new-fighter INTERNAL range [%d, %d] = %d rows; internal %d..%d are the %d retail bosses"
          % (GW_MEX_FIRST_NEW, hi - 1, hi - GW_MEX_FIRST_NEW, hi, disc.n_int - 1, N_RETAIL_BOSSES))
    print("")
    hdr = ("%4s %7s %7s %7s %7s %-17s %-10s %11s %4s %3s %3s %3s %8s %3s %4s"
           % ("slot", "port_Ft", "port_Ch", "mex_int", "mex_ext", "name", "Pl", "clone base",
              "anim", "eff", "cos", "art", "codeSize", "ovr", "syms"))
    print(hdr + ("%6s" % "also" if other is not None else ""))

    slot = 0
    dropped = []
    for k in range(GW_MEX_FIRST_NEW, hi):
        e, nm = disc.name(k)
        pl = disc.pl(k)[0]
        if not pl:
            print("%4s %7s %7s %7d %7s %-17s %-10s SKIPPED: row has no Pl file"
                  % ("--", "--", "--", k, e, nm, "-"))
            continue
        if pl not in disc.basenames:
            print("%4s %7s %7s %7d %7s %-17s %-10s SKIPPED: not on the disc"
                  % ("--", "--", "--", k, e, nm, pl))
            continue
        cs, ovr, syms, _derived, _it = disc.ftfunction(pl)
        b = disc.retail_by_onload.get(disc.onload[k])
        base = "%d:%s" % (b, RETAIL[b]) if b is not None else "0:Mario*"
        size = "none" if cs is None else ("0 (*)" if cs == 0 else "0x%05X" % cs)
        row = ("%4d %#7x %#7x %7d %7s %-17s %-10s %11s %4d %3d %3d %3d %8s %3d %4d"
               % (slot, PORT_FT_MEX0 + slot, PORT_CK_MEX0 + slot, k, e, nm, pl, base,
                  disc.anim_count(k), disc.effect_index(k), disc.costume_count(k),
                  disc.article_count(k), size, ovr, syms))
        if other is not None:
            row += "%6s" % ("yes" if pl in other else "-")
        print(row)
        if slot >= GW_MEX_SLOTS:
            dropped.append((k, pl))
        slot += 1

    print("")
    print("%d fighters want a slot; GW_MEX_SLOTS is %d -> %s" % (slot, GW_MEX_SLOTS, verdict(slot)))
    if dropped:
        print("  would be dropped: "
              + ", ".join("internal %d (%s)" % (k, pl) for k, pl in dropped))
    print("  'clone base' = the retail kind sharing this fighter's fighter_function[0]; "
          "* = none does, so gw_Mex_FtBaseKind falls back to Mario (0).")
    print("  '0 (*)' codeSize = the blob declares codeSize 0 and no debug symbols; the real size "
          "has to be recovered (gw_mex_ftfunction.c rejects codeSize 0 outright).")


if __name__ == "__main__":
    main()
