"""A dedicated Ultimate Kirby row must preserve the existing ACE roster."""

from pathlib import Path
import json
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ports/kirby-ultimate/tools"))
sys.path.insert(0, str(ROOT / "tools/mex_port"))
from mex_hsd import Archive  # noqa: E402
sys.path.insert(0, str(ROOT / "experiment/brawl-kirby/tools"))
import texanim_keys  # noqa: E402

BASE = ROOT / "ports/halberd/mods-slot/metaknight-slot/files/MxDt.dat"
PLCO = ROOT / "ports/halberd/mods-slot/metaknight-slot/files/PlCo.dat"
MENU = ROOT / "ports/halberd/mods-slot/metaknight-slot/files/MnSlChr.usd"
STOCK = ROOT / "ports/halberd/mods-slot/metaknight-slot/files/IfAll.usd"
SOURCE = ROOT / "_build/tmp/ultimate-kirby-wave-native-lab-v2/source"
REPLACEMENT_REPORT = (ROOT / "_build/tmp/ultimate-kirby-wave-native-lab-v2/mods/"
                      "ultimate-kirby-slot/slot-build.json")


def label(ar: Archive, ptr: int) -> str:
    return bytes(ar.data[ptr:ar.data.index(0, ptr)]).decode("ascii") if ptr else ""


def texture_value(data: bytes | bytearray, texanim: int, frame: int) -> bytes:
    fobj = struct.unpack_from(">I", data,
                              struct.unpack_from(">I", data, texanim + 8)[0] + 8)[0]
    keys = texanim_keys._decode(data, fobj)
    return [entry[2] for entry in keys if entry[0] <= frame][-1]


@unittest.skipUnless(BASE.is_file(), "local ACE m-ex baseline required")
class AdditiveSlotTest(unittest.TestCase):
    def test_new_slot_preserves_existing_fighters_and_boss_rows(self):
        import build_additive_slot as slot

        before = Archive(BASE.read_bytes())
        after = Archive(slot.expand_mxdt(before.raw, icon_joint=58))
        rb, ra = before.public("mexData"), after.public("mexData")
        mb, ma = before.u32(rb), after.u32(ra)
        self.assertEqual(struct.unpack_from(">ii", before.data, mb + 4), (65, 65))
        self.assertEqual(struct.unpack_from(">ii", after.data, ma + 4), (66, 66))
        self.assertEqual(after.u32(ma + 12), before.u32(mb + 12) + 1)

        fb, fa = before.u32(rb + 8), after.u32(ra + 8)
        plb, pla = before.u32(fb + 4), after.u32(fa + 4)
        nb, na = before.u32(fb), after.u32(fa)
        db, da = before.u32(fb + 0xC), after.u32(fa + 0xC)
        for k in range(59):
            self.assertEqual(label(after, after.u32(pla + 8 * k)),
                             label(before, before.u32(plb + 8 * k)), k)
        self.assertEqual(label(after, after.u32(pla + 8 * 59)), "PlUk.dat")
        for k in range(59, 65):
            self.assertEqual(label(after, after.u32(pla + 8 * (k + 1))),
                             label(before, before.u32(plb + 8 * k)), k)
        for e in range(65):
            self.assertEqual(label(after, after.u32(na + 4 * e)),
                             label(before, before.u32(nb + 4 * e)), e)
            old = before.data[db + 3 * e]
            self.assertEqual(after.data[da + 3 * e], old + (old >= 59), e)
        self.assertEqual(label(after, after.u32(na + 4 * 65)), "Ultimate Kirby")
        self.assertEqual(after.data[da + 3 * 65], 59)

        aj = after.u32(fa + 0x1C)
        self.assertEqual(label(after, after.u32(aj + 4 * 59)), "PlUkAJ.dat")
        info = after.u32(fa + 0x10)
        self.assertEqual(after.data[info + 4 * 65], 8)
        costumes = after.u32(after.u32(fa + 0x14) + 4 * 59)
        self.assertEqual([label(after, after.u32(costumes + 16 * i)) for i in range(8)],
                         ["PlUk" + color + ".dat" for color in slot.COLORS])

    def test_optional_pivot_motion_extends_only_new_animation_count(self):
        import build_additive_slot as slot

        before = Archive(BASE.read_bytes())
        after = Archive(slot.expand_mxdt(before.raw, icon_joint=58, anim_count=480))
        fb = before.u32(before.public("mexData") + 8)
        fa = after.u32(after.public("mexData") + 8)
        tb = before.u32(fb + 8 * 4)
        ta = after.u32(fa + 8 * 4)
        self.assertEqual(after.u32(ta + 8 * 59 + 4), 480)
        for kind in range(59):
            self.assertEqual(after.data[ta + 8 * kind:ta + 8 * (kind + 1)],
                             before.data[tb + 8 * kind:tb + 8 * (kind + 1)])
        for kind in range(59, 65):
            self.assertEqual(after.data[ta + 8 * (kind + 1):ta + 8 * (kind + 2)],
                             before.data[tb + 8 * kind:tb + 8 * (kind + 1)])

    def test_hammer_motion_extension_raises_only_new_fighter_count(self):
        import build_additive_slot as slot

        before = Archive(BASE.read_bytes())
        after = Archive(slot.expand_mxdt(before.raw, icon_joint=58, anim_count=489))
        fb = before.u32(before.public("mexData") + 8)
        fa = after.u32(after.public("mexData") + 8)
        tb = before.u32(fb + 8 * 4)
        ta = after.u32(fa + 8 * 4)
        self.assertEqual(after.u32(ta + 8 * 59 + 4), 489)
        for kind in range(59):
            self.assertEqual(after.data[ta + 8 * kind:ta + 8 * (kind + 1)],
                             before.data[tb + 8 * kind:tb + 8 * (kind + 1)])
        for kind in range(59, 65):
            self.assertEqual(after.data[ta + 8 * (kind + 1):ta + 8 * (kind + 2)],
                             before.data[tb + 8 * kind:tb + 8 * (kind + 1)])

    @unittest.skipUnless(PLCO.is_file(), "local ACE fighter-common archive required")
    def test_fighter_common_tables_follow_inserted_internal_row(self):
        import build_additive_slot as slot

        before = Archive(PLCO.read_bytes())
        after = Archive(slot.expand_plco(before.raw))
        rb, ra = before.public("ftLoadCommonData"), after.public("ftLoadCommonData")
        for field in (4, 5):
            tb, ta = before.u32(rb + 4 * field), after.u32(ra + 4 * field)
            self.assertEqual([after.u32(ta + 4 * k) for k in range(59)],
                             [before.u32(tb + 4 * k) for k in range(59)])
            self.assertEqual(after.u32(ta + 4 * 59), before.u32(tb + 4 * 4))
            self.assertEqual([after.u32(ta + 4 * (k + 1)) for k in range(59, 65)],
                             [before.u32(tb + 4 * k) for k in range(59, 65)])

    @unittest.skipUnless(MENU.is_file() and STOCK.is_file(), "local ACE menu art required")
    def test_menu_and_stock_atlases_keep_old_frames_and_add_kirby(self):
        import build_additive_slot as slot

        before = Archive(MENU.read_bytes())
        menu, joint = slot.expand_menu(before.raw)
        after = Archive(menu)
        rb, ra = before.public("mexSelectChr"), after.public("mexSelectChr")
        self.assertEqual(before.u32(rb + 0x10), 65)
        self.assertEqual(after.u32(ra + 0x10), 66)
        self.assertGreater(joint, 20)
        tb = before.u32(before.u32(rb + 0xC) + 8)
        ta = after.u32(after.u32(ra + 0xC) + 8)
        for color in range(8):
            for ext in (0, 4, 51, 64):
                self.assertEqual(texture_value(after.data, ta, color * 66 + ext),
                                 texture_value(before.data, tb, color * 65 + ext))
            self.assertEqual(texture_value(after.data, ta, color * 66 + 65),
                             texture_value(before.data, tb, color * 65 + 4))

        before = Archive(STOCK.read_bytes())
        after = Archive(slot.expand_stock(before.raw))
        rb, ra = before.public("Stc_icns"), after.public("Stc_icns")
        self.assertEqual(struct.unpack_from(">HH", before.data, rb), (8, 65))
        self.assertEqual(struct.unpack_from(">HH", after.data, ra), (8, 66))
        tb = before.u32(before.u32(before.u32(rb + 4) + 8) + 8)
        ta = after.u32(after.u32(after.u32(ra + 4) + 8) + 8)
        for color in range(8):
            for kind in (0, 4, 53):
                self.assertEqual(texture_value(after.data, ta, 8 + color * 66 + kind),
                                 texture_value(before.data, tb, 8 + color * 65 + kind))
            self.assertEqual(texture_value(after.data, ta, 8 + color * 66 + 59),
                             texture_value(before.data, tb, 8 + color * 65 + 4))
            self.assertEqual(texture_value(after.data, ta, 8 + color * 66 + 65),
                             texture_value(before.data, tb, 8 + color * 65 + 64))

    @unittest.skipUnless(SOURCE.is_dir() and REPLACEMENT_REPORT.is_file(),
                         "local patched Kirby fighter and costumes required")
    def test_pack_adds_kirby_without_replacing_lucina(self):
        import build_additive_slot as slot

        previous = json.loads(REPLACEMENT_REPORT.read_text(encoding="utf-8"))
        costumes = [Path(row["source"]) for row in previous["costume_sources"]]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "ultimate-kirby-additive-slot"
            report = slot.build(SOURCE, BASE.parent, output, costumes)
            self.assertEqual(report["mode"], "additive")
            self.assertIsNone(report["replaces"])
            after = Archive((output / "files/MxDt.dat").read_bytes())
            root = after.public("mexData")
            fighter = after.u32(root + 8)
            names = after.u32(fighter)
            self.assertEqual(label(after, after.u32(names + 4 * 52)), "Lucina")
            self.assertEqual(label(after, after.u32(names + 4 * 65)), "Ultimate Kirby")
            self.assertEqual((output / "files/PlUk.dat").read_bytes(),
                             (SOURCE / "files/PlKb.dat").read_bytes())


if __name__ == "__main__":
    unittest.main()
