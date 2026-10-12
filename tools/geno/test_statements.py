"""Statement encoding and exact round-trip checks; no disc or game launch."""
import json
import random
import re
import unittest

from tools.test_support import require_game
require_game("pc/geno/geno.h")
from tools.geno import check, script


class StatementTests(unittest.TestCase):
    def test_throw_known_vector_and_legacy_forms(self):
        # Hand-packed from CmdUnion: 6/3/23, 9/9/9/reserved5,
        # 9/4/3/4/reserved12. This catches incorrect alias shifts/defaults.
        expected = [0x88000008, 0xB4990000, 0x0F000000]
        friendly = "throw slot=0 damage=8 angle=361 kbg=100 fkb=0 bkb=30 element=0 sfx_severity=0 sfx_kind=0"
        legacy = "throw idx=0 damage=8 unk0=361 hit_x24=100 hit_x28=0 hit_x2C=30 element=0 sfx_severity=0 sfx_kind=0"
        qualified = "throw w0.idx=0 w0.damage=8 w1.unk0=361 w1.hit_x24=100 w1.hit_x28=0 w2.hit_x2C=30 w2.element=0 w2.sfx_severity=0 w2.sfx_kind=0"
        for text in (friendly, legacy, qualified, "throw 8 0xB4990000 0x0F000000",
                     "throw raw=0x88000008,0xB4990000,0x0F000000"):
            for name in ("throw", "throw_hitbox"):
                with self.subTest(text=text, name=name):
                    self.assertEqual(script.assemble(text.replace("throw", name, 1)), expected)
        self.assertEqual(script.disassemble(expected), friendly + "\n")

    def test_throw_defaults_and_maximum_encoded_fields(self):
        for text in ("throw", "throw slot=0", "throw idx=0", "throw_hitbox w0.idx=0"):
            self.assertEqual(script.assemble(text), [0x88000000, 0, 0])
        self.assertEqual(script.assemble("throw slot=7 damage=8388607 angle=511 kbg=511 fkb=511 bkb=511 element=15 sfx_severity=7 sfx_kind=15"),
                         [0x8BFFFFFF, 0xFFFFFFE0, 0xFFFFF000])

    def test_throw_release_known_vector_and_old_flags(self):
        self.assertEqual(script.assemble("throw_release"), [0x50000000])
        self.assertEqual(script.disassemble([0x50000000]), "throw_release\n")
        for value in (0, 1, 67108863):
            for text in (f"throw_flag {value}", f"throw_flag hit_idx={value}",
                         f"throw_flag w0.hit_idx={value}"):
                self.assertEqual(script.assemble(text), [0x50000000 | value])
        self.assertEqual(script.disassemble([0x50000001]), "throw_flag w0.hit_idx=1\n")

    def test_hurt_states_known_vectors_and_legacy_forms(self):
        for state, value in (("normal", 0), ("invincible", 1), ("intangible", 2)):
            for name, opcode in (("body_state", 26), ("hurtboxes_state", 27)):
                expected = [opcode << 26 | value]
                for text in (f"{name} state={state}", f"{name} w0.state={state}",
                             f"{name} state={value}", f"{name} w0.state={value}", f"{name} {value}"):
                    self.assertEqual(script.assemble(text), expected)
                self.assertEqual(script.disassemble(expected), f"{name} state={state}\n")
            expected = [0x70AC0000 | value]  # bone 43 in bits 25..18
            for bone in ("bone", "bone_idx", "w0.bone_idx"):
                for state_key in ("state", "w0.state"):
                    self.assertEqual(script.assemble(f"hurtbox_state {bone}=43 {state_key}={state}"), expected)
            self.assertEqual(script.assemble(f"hurtbox_state bone_idx=43 state={value}"), expected)
            self.assertEqual(script.disassemble(expected), f"hurtbox_state bone=43 state={state}\n")

    def test_legacy_numeric_states_preserve_their_encoded_range(self):
        for text, expected in (("body_state w0.state=67108863", [0x6BFFFFFF]),
                               ("hurtboxes_state state=3", [0x6C000003]),
                               ("hurtbox_state bone_idx=255 state=262143", [0x73FFFFFF])):
            self.assertEqual(script.assemble(text), expected)
            self.assertEqual(script.assemble(script.disassemble(expected)), expected)

    def test_statement_errors_and_duplicate_aliases(self):
        invalid = ("throw slot=8", "throw damage=8388608", "throw damage=1.5", "throw angle=512",
                   "throw kbg=-1", "throw fkb=512", "throw bkb=512", "throw element=16",
                   "throw sfx_severity=8", "throw sfx_kind=16", "throw joint=1",
                   "throw slot=0 idx=0", "throw angle=1 w1.unk0=1", "throw kbg=1 hit_x24=1",
                   "throw fkb=1 hit_x28=1", "throw bkb=1 w2.hit_x2C=1", "throw damage=1 damage=1",
                   "throw_release 1", "throw_release hit_idx=1", "body_state state=typo",
                   "hurtboxes_state state=-1", "body_state state=67108864",
                   "hurtbox_state bone=256", "hurtbox_state bone=-1", "hurtbox_state state=262144",
                   "hurtbox_state bone=1 bone_idx=1", "hurtbox_state state=normal w0.state=0",
                   "body_state state=intangible w0.state=2", "hurtboxes_state slot=0")
        for text in invalid:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "line 1"):
                script.assemble(text)

    def test_reserved_throw_bits_use_raw_fallback(self):
        for words in ([0x88000008, 0xB4990001, 0x0F000000],
                      [0x88000008, 0xB4990000, 0x0F000001]):
            self.assertIn("raw=", script.disassemble(words))
            self.assertEqual(script.assemble(script.disassemble(words)), words)

    def test_random_statement_words_roundtrip_exactly(self):
        rng = random.Random(0x5448524F57)
        for op in (20, 26, 27, 28, 34):
            for _ in range(500):
                words = [(op << 26) | rng.getrandbits(26)]
                words.extend(rng.getrandbits(32) for _ in range(script.LENGTHS[op] - 1))
                self.assertEqual(script.assemble(script.disassemble(words)), words)


class ExistingMoveTests(unittest.TestCase):
    def test_every_ports_genoasm_source_roundtrips(self):
        paths = sorted((script.ROOT / "ports").rglob("*.genoasm"))
        self.assertTrue(paths, "no authored move sources found")
        # a cross-port hitbox word 0 is written @HITW0:<ROLE>:0x<base>@ (build.py puts in the joint): for this test the base word stands for it
        texts = {path: re.sub(r"@HITW0:[A-Z_0-9]+:(0x[0-9A-Fa-f]+)@", r"\1", path.read_text(encoding="utf-8-sig")) for path in paths}
        roles = sorted({role for text in texts.values() for role in re.findall(r"@([A-Z][A-Z_0-9]*)@", text)})
        self.assertLessEqual(len(roles), 256, "role substitution exceeds encoded joint range")
        joints = {role: str(i) for i, role in enumerate(roles)}
        command_count = word_count = 0
        for path, text in texts.items():
            with self.subTest(path=str(path.relative_to(script.ROOT))):
                resolved = re.sub(r"@([A-Z][A-Z_0-9]*)@", lambda m: joints[m[1]], text)
                words = script.assemble(resolved)
                self.assertEqual(script.assemble(script.disassemble(words)), words)
                command_count += len(list(script.commands(words)))
                word_count += len(words)
        print(f"ports .genoasm: {len(paths)} sources, {len(roles)} substituted roles, {command_count} commands, {word_count} words")

    def test_every_ports_geno_json_move_fixture_roundtrips(self):
        # Discover every manifest and every subaction, including ignored local
        # fixtures when present. Missing referenced files fail, never skip.
        manifests = sorted((script.ROOT / "ports").rglob("geno.json"))
        word_arrays = word_files = command_count = word_count = 0
        for path in manifests:
            data = json.loads(check.json_text(path.read_text(encoding="utf-8-sig")))
            for fi, fighter in enumerate(data.get("fighters", [])):
                for si, move in enumerate(fighter.get("subactions", [])):
                    with self.subTest(manifest=str(path.relative_to(script.ROOT)), fighter=fi, subaction=si):
                        self.assertNotEqual("words" in move, "file" in move, "move needs exactly one words/file source")
                        if "words" in move:
                            words = [script.word(w) for w in move["words"]]
                            word_arrays += 1
                        else:
                            words = script.read_words((path.parent / move["file"]).read_text(encoding="utf-8-sig"))
                            word_files += 1
                        self.assertEqual(script.assemble(script.disassemble(words)), words)
                        command_count += len(list(script.commands(words)))
                        word_count += len(words)
        print(f"ports geno.json: {len(manifests)} manifests, {word_arrays} arrays, {word_files} files, {command_count} commands, {word_count} words")


if __name__ == "__main__":
    unittest.main()
