#!/usr/bin/env python3
"""hitbox_words.py - the five 32-bit words of one Melee hitbox command, for a Geno script overlay.

    python hitbox_words.py --joint 2 --damage 8 --size 4
    python hitbox_words.py --joint 2 --damage 8 --size 4 --decode

Part of packet 3 of the Geno fighter course. The layout is the one `ports/ir/tools/acmd_to_ftcmd.py`
(`hitbox_words`) writes for the Ultimate-to-Melee pipeline, and the fields are those the LAB decodes
(`gd.timeline`, `lab events`: id, bone, damage, size, ox/oy/oz, angle, kbg, wbk, bkb, element,
shield_damage, hit_ground, hit_air). The source of the layout is the repo's own tool; the offset
axes were checked in the game on 2026-10-03: x, y, z are the bone's own axes, in the order
the LAB reports them (ox, oy, oz); the bone is turned, so the world direction depends on the pose.

  word 0  [31:26] 11 (hitbox)  [25:23] hitbox slot 0-3 (the id)  [22:11] joint  [10:0] damage
  word 1  [31:16] size x 256 (as an unsigned 16-bit fixed point)   [15:0] x offset x 256 (signed)
  word 2  [31:16] y offset x 256 (signed)                          [15:0] z offset x 256 (signed)
  word 3  [31:23] angle  [22:14] knockback growth  [13:5] weight-based (fixed) knockback
  word 4  [31:23] base knockback  [22:18] element  [17:10] shield damage  [7] 1
          [6:2] sound kind (1 for punches; 3 for slashes)  [1] hits ground  [0] hits air

It does not run the game and cannot tell you the joint number: read that from the LAB.
"""
import argparse


def s16(value):
    return int(round(value * 256)) & 0xFFFF


def hitbox_words(slot, joint, damage, size, x, y, z, angle, kbg, fkb, bkb, element, shield,
                 ground=True, air=True, sfx_kind=None):
    if sfx_kind is None:
        sfx_kind = 3 if element == 3 else 1
    w0 = (11 << 26) | ((slot & 7) << 23) | (joint << 11) | min(int(round(damage)), 1023)
    w1 = (min(int(round(size * 256)), 0xFFFF) << 16) | s16(x)
    w2 = (s16(y) << 16) | s16(z)
    w3 = ((int(angle) & 0x1FF) << 23) | ((int(kbg) & 0x1FF) << 14) | ((int(fkb) & 0x1FF) << 5)
    w4 = (((int(bkb) & 0x1FF) << 23) | ((element & 0x1F) << 18) | ((int(shield) & 0xFF) << 10) |
          (1 << 7) | (sfx_kind << 2) | (int(ground) << 1) | int(air))
    return [w0, w1, w2, w3, w4]


def _signed16(v):
    return v - 0x10000 if v & 0x8000 else v


def decode(words):
    w0, w1, w2, w3, w4 = words
    return {
        "opcode": w0 >> 26, "id": (w0 >> 23) & 7, "bone": (w0 >> 11) & 0xFFF, "damage": w0 & 0x7FF,
        "size": (w1 >> 16) / 256.0, "x": _signed16(w1 & 0xFFFF) / 256.0,
        "y": _signed16(w2 >> 16) / 256.0, "z": _signed16(w2 & 0xFFFF) / 256.0,
        "angle": w3 >> 23, "kbg": (w3 >> 14) & 0x1FF, "wbk": (w3 >> 5) & 0x1FF,
        "bkb": w4 >> 23, "element": (w4 >> 18) & 0x1F, "shield_damage": (w4 >> 10) & 0xFF,
        "hit_ground": bool((w4 >> 1) & 1), "hit_air": bool(w4 & 1),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--slot", type=int, default=0, help="hitbox id 0-3 (default 0)")
    ap.add_argument("--joint", type=int, required=True, help="the bone, read from the LAB")
    ap.add_argument("--damage", type=float, required=True, help="whole percent, 0-1023")
    ap.add_argument("--size", type=float, required=True, help="radius")
    ap.add_argument("--x", type=float, default=0.0, help="bone-local offset")
    ap.add_argument("--y", type=float, default=0.0)
    ap.add_argument("--z", type=float, default=0.0)
    ap.add_argument("--angle", type=int, default=361, help="launch angle; 361 is Sakurai's angle")
    ap.add_argument("--kbg", type=int, default=100, help="knockback growth")
    ap.add_argument("--fkb", type=int, default=0, help="weight-based (fixed) knockback")
    ap.add_argument("--bkb", type=int, default=30, help="base knockback")
    ap.add_argument("--element", type=int, default=0, help="0 normal, 1 fire, 2 electric, 3 slash, 5 ice")
    ap.add_argument("--shield", type=int, default=0, help="shield damage")
    ap.add_argument("--no-ground", action="store_true", help="does not hit grounded fighters")
    ap.add_argument("--no-air", action="store_true", help="does not hit airborne fighters")
    ap.add_argument("--decode", action="store_true", help="also print the fields read back from the words")
    a = ap.parse_args()
    if not 0 <= a.slot <= 3 or not 0 <= a.joint <= 0xFFF:
        ap.error("slot must be 0-3 and joint 0-4095")
    words = hitbox_words(a.slot, a.joint, a.damage, a.size, a.x, a.y, a.z, a.angle, a.kbg, a.fkb,
                         a.bkb, a.element, a.shield, not a.no_ground, not a.no_air)
    print("# hitbox: slot %d joint %d damage %g size %g angle %d kbg %d wbk %d bkb %d" %
          (a.slot, a.joint, a.damage, a.size, a.angle, a.kbg, a.fkb, a.bkb))
    print(" ".join("0x%08X" % w for w in words))
    if a.decode:
        for key, value in decode(words).items():
            print("  %-14s %s" % (key, value))


if __name__ == "__main__":
    main()
