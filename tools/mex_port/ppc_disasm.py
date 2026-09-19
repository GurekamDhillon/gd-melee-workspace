#!/usr/bin/env python3
import argparse
import struct
import sys

FIELD_OP = 26


def sx(v, bits):
    sign = 1 << (bits - 1)
    return (v ^ sign) - sign


def spr_name(n):
    table = {
        1: "xer", 8: "lr", 9: "ctr", 268: "srr0", 269: "srr1",
        287: "pvr", 528: "gqr0", 529: "gqr1",
        912: "hid0", 914: "hid2", 920: "hid0",
        1008: "hid0", 1013: "dabr",
    }
    if n in table:
        return table[n]
    return f"spr{n}"


X_OPS = {
    40: ("subf", "X"), 266: ("add", "X"), 104: ("neg", "X"), 235: ("mullw", "X"),
    491: ("divw", "X"), 459: ("divwu", "X"), 28: ("and", "X"), 444: ("or", "X"),
    316: ("xor", "X"), 124: ("nor", "X"), 476: ("nand", "X"), 60: ("andc", "X"),
    284: ("eqv", "X"), 412: ("orc", "X"), 24: ("slw", "X"), 536: ("srw", "X"),
    792: ("sraw", "X"), 824: ("srawi", "X"), 26: ("cntlzw", "X"), 122: ("extsb", "X"),
    954: ("extsh", "X"), 58: ("extsw", "X"), 23: ("lwzx", "X"), 151: ("stwx", "X"),
    87: ("lbzx", "X"), 215: ("stbx", "X"), 279: ("lhzx", "X"), 407: ("sthx", "X"),
    343: ("lhax", "X"), 535: ("lfsx", "X"), 663: ("stfsx", "X"), 599: ("lfdx", "X"),
    727: ("stfdx", "X"), 20: ("lwarx", "X"), 150: ("stwcx.", "X"), 339: ("mfspr", "SPR"),
    467: ("mtspr", "SPR"), 19: ("mfcr", "MFCR"), 144: ("mtcrf", "MTCRF"),
    831: ("mfsr", "X"), 210: ("mtsr", "X"), 0: ("cmp", "CMP"), 32: ("cmpl", "CMP"),
    467 + 0: ("mtspr", "SPR"), 310: ("dcbt", "X"), 86: ("dcbf", "X"), 54: ("dcbst", "X"),
    1014: ("dcbz", "X"), 982: ("icbi", "X"), 306: ("tlbie", "X"), 256: ("sync", "NONE"),
    598: ("sync", "NONE"), 150 + 0: ("stwcx.", "X"),
    8: ("subfc", "X"), 10: ("addc", "X"), 138: ("adde", "X"), 200: ("subfze", "X"),
    202: ("addze", "X"), 232: ("subfme", "X"), 234: ("addme", "X"), 136: ("subfe", "X"),
    75: ("mulhw", "X"), 11: ("mulhwu", "X"),
}

D_OPS = {
    14: "addi", 15: "addis", 7: "mulli", 8: "subfic", 12: "addic", 13: "addic.",
    10: "cmpli", 11: "cmpi", 24: "ori", 25: "oris", 26: "xori", 27: "xoris",
    28: "andi.", 29: "andis.", 32: "lwz", 33: "lwzu", 34: "lbz", 35: "lbzu",
    36: "stw", 37: "stwu", 38: "stb", 39: "stbu", 40: "lhz", 41: "lhzu",
    42: "lha", 43: "lhau", 44: "sth", 45: "sthu", 46: "lmw", 47: "stmw",
    48: "lfs", 49: "lfsu", 50: "lfd", 51: "lfdu", 52: "stfs", 53: "stfsu",
    54: "stfd", 55: "stfdu",
}

DS_OPS = {58: "ld", 62: "std", 57: "ldu", 61: "stdu"}

X_DEST_RA = {28, 444, 316, 124, 476, 60, 284, 412, 24, 536, 792}


def decode(w, addr):
    op = (w >> FIELD_OP) & 0x3F

    if w == 0x60000000:
        return "nop"
    if w == 0x4E800020:
        return "blr"
    if w == 0x4E800420:
        return "bctr"
    if w == 0x4C000064:
        return "rfi"

    if op == 18:
        li = sx(w & 0x03FFFFFC, 26)
        aa = (w >> 1) & 1
        lk = w & 1
        mnem = "bl" if lk else "b"
        tgt = li if aa else addr + li
        return f"{mnem} 0x{tgt & 0xFFFFFFFF:08X}"

    if op == 16:
        bo = (w >> 21) & 0x1F
        bi = (w >> 16) & 0x1F
        bd = sx(w & 0xFFFC, 16)
        aa = (w >> 1) & 1
        lk = w & 1
        tgt = bd if aa else addr + bd
        cr_codes = {0: ("blt", "bge", "bso", "bns")}
        mnem = None
        if bo == 20 and lk == 0:
            mnem = "b"
        elif bo == 16:
            mnem = "bdz"
        elif bo == 18:
            mnem = "bdnz"
        elif bo in (12, 4) and (bi & 3) in (0, 1, 2, 3):
            bit = bi & 3
            if bit == 0:
                mnem = "blt" if bo == 12 else "bge"
            elif bit == 1:
                mnem = "bgt" if bo == 12 else "ble"
            elif bit == 2:
                mnem = "beq" if bo == 12 else "bne"
            else:
                mnem = "bso" if bo == 12 else "bns"
            if lk:
                mnem += "l"
        if mnem is None:
            mnem = f"bc {bo},{bi}"
        return f"{mnem} 0x{tgt & 0xFFFFFFFF:08X}"

    if op == 19:
        xo = (w >> 1) & 0x3FF
        if xo == 16:
            return "bclr"
        if xo == 528:
            return "bcctr"
        if xo == 33:
            return "crnor"
        return f"op19:{xo}"

    if op == 21:
        rs = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        sh = (w >> 11) & 0x1F
        mb = (w >> 6) & 0x1F
        me = (w >> 1) & 0x1F
        if mb == 0 and me == (31 - sh) % 32:
            return f"slwi r{ra},r{rs},{sh}"
        if me == 31 and sh == (32 - mb) % 32:
            return f"srwi r{ra},r{rs},{mb}"
        if sh == 0 and me == 31:
            return f"clrlwi r{ra},r{rs},{mb}"
        return f"rlwinm r{ra},r{rs},{sh},{mb},{me}"

    if op == 20:
        rs = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        return f"rlwimi r{ra},r{rs},{(w >> 11) & 0x1F},{(w >> 6) & 0x1F},{(w >> 1) & 0x1F}"

    if op == 23:
        rs = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        rb = (w >> 11) & 0x1F
        return f"rlwnm r{ra},r{rs},r{rb},{(w >> 6) & 0x1F},{(w >> 1) & 0x1F}"

    if op in D_OPS:
        mnem = D_OPS[op]
        rt = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        imm = sx(w & 0xFFFF, 16)
        uimm = w & 0xFFFF
        if mnem in ("cmpi", "cmpli"):
            bf = (w >> 23) & 7
            l = (w >> 21) & 1
            return f"{mnem} cr{bf},{l},r{ra},{uimm}"
        if mnem in ("addi", "addis", "mulli", "subfic", "addic", "addic."):
            return f"{mnem} r{rt},r{ra},{imm}"
        if mnem in ("ori", "oris", "xori", "xoris", "andi.", "andis."):
            return f"{mnem} r{ra},r{rt},0x{uimm:X}"
        if mnem in ("lwz", "lbz", "stw", "stb", "lhz", "lha", "sth", "lmw", "stmw"):
            return f"{mnem} r{rt},{imm}(r{ra})"
        if mnem in ("lfs", "lfd", "stfs", "stfd"):
            return f"{mnem} f{rt},{imm}(r{ra})"
        return f"{mnem} r{rt},r{ra},{imm}"

    if op == 31:
        xo = (w >> 1) & 0x3FF
        rt = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        rb = (w >> 11) & 0x1F
        entry = X_OPS.get(xo)
        if entry is None:
            return f"op31:{xo}"
        mnem, form = entry
        if form == "SPR":
            spr = ((w >> 16) & 0x1F) | (((w >> 11) & 0x1F) << 5)
            if mnem == "mfspr":
                return f"mfspr r{rt},{spr_name(spr)}"
            return f"mtspr {spr_name(spr)},r{rt}"
        if form == "MFCR":
            return f"mfcr r{rt}"
        if form == "MTCRF":
            return f"mtcrf 0x{(w >> 12) & 0xFF:X},r{rt}"
        if form == "CMP":
            bf = (w >> 23) & 7
            l = (w >> 21) & 1
            return f"{mnem} cr{bf},{l},r{ra},r{rb}"
        if form == "NONE":
            return mnem
        if mnem in ("srawi", "extsb", "extsh", "extsw", "cntlzw"):
            if mnem == "srawi":
                return f"{mnem} r{ra},r{rt},{rb}"
            return f"{mnem} r{ra},r{rt}"
        if mnem in ("lfsx", "lfdx", "stfsx", "stfdx"):
            return f"{mnem} f{rt},r{ra},r{rb}"
        if xo in X_DEST_RA:
            return f"{mnem} r{ra},r{rt},r{rb}"
        return f"{mnem} r{rt},r{ra},r{rb}"

    if op in DS_OPS:
        mnem = DS_OPS[op]
        rt = (w >> 21) & 0x1F
        ra = (w >> 16) & 0x1F
        ds = sx(w & 0xFFFC, 16)
        return f"{mnem} r{rt},{ds}(r{ra})"

    if op == 4:
        return f"ps_op4:{(w >> 1) & 0x3FF}"
    if op in (56, 60):
        return f"ps_op{op}:{(w >> 1) & 0x3FF}"

    return f".long 0x{w:08X}"


DOL_SECTIONS = [(0x80003100, 0x000100, 0x2420), (0x80005940, 0x002520, 0x3B1900)]


def va_to_offset(va):
    for vaddr, off, size in DOL_SECTIONS:
        if vaddr <= va < vaddr + size:
            return off + (va - vaddr)
    return None


def main():
    ap = argparse.ArgumentParser()
    # --dol disassembles the game's main.dol by virtual address. --raw disassembles a flat code
    # blob (e.g. an m-ex ftFunction dumped from the port with MELEE_MEX_DUMP_CODE), where
    # --base is the virtual address the blob was relocated to, so --start is still a real VA.
    ap.add_argument("--dol")
    ap.add_argument("--raw", help="flat code blob instead of a DOL")
    ap.add_argument("--base", help="VA the --raw blob is loaded at (e.g. 0x807F4D60)")
    ap.add_argument("--start", required=True)
    ap.add_argument("--count", type=int, default=16)
    args = ap.parse_args()
    va = int(args.start, 0)
    if args.raw:
        if args.base is None:
            print("--raw requires --base", file=sys.stderr)
            return 1
        base = int(args.base, 0)
        data = open(args.raw, "rb").read()
        off = va - base
        if off < 0 or off >= len(data):
            print(f"0x{va:08X} is outside the blob "
                  f"(0x{base:08X}..0x{base + len(data):08X})", file=sys.stderr)
            return 1
    else:
        if not args.dol:
            print("pass either --dol or --raw", file=sys.stderr)
            return 1
        off = va_to_offset(va)
        if off is None:
            print(f"0x{va:08X} is outside the mapped text sections", file=sys.stderr)
            return 1
        data = open(args.dol, "rb").read()
    for i in range(args.count):
        o = off + i * 4
        w = struct.unpack(">I", data[o:o + 4])[0]
        a = va + i * 4
        print(f"0x{a:08X}  {w:08X}  {decode(w, a)}")


if __name__ == "__main__":
    sys.exit(main())
