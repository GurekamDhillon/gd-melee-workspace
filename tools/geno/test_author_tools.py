import copy
import json
from pathlib import Path
import random
import tempfile
import unittest
import subprocess
from unittest.mock import patch

from tools.test_support import require_game
require_game('pc/geno/geno.h')
from tools.geno import schema, script, check, export, source


class AuthorToolsTests(unittest.TestCase):
    def test_generated_files_current(self):
        for path, text in schema.artifacts().items():
            self.assertEqual(path.read_text(encoding="utf-8"), text, str(path))

    def test_registry_coverage(self):
        self.assertEqual(schema.registry_keys() - schema.covered_keys(), set())
        # A new lookup must trip the guard even before generation.
        self.assertIn("future_key", schema.registry_keys(schema.registry_text() +
                         '\n jd_get(d, e, "future_key");') - schema.covered_keys())

    def test_starter(self):
        self.assertEqual(check.validate_path(schema.ROOT / "docs/learn/geno-fighters/starter"), [])

    def test_hitbox_reuses_encoder(self):
        words = script.encoder().hitbox_words(0, 2, 8, 4, 0, 0, 0, 361, 100, 0, 30, 0, 0)
        self.assertEqual(script.assemble("hitbox joint=2 damage=8 size=4 bkb=30"), words)
        self.assertEqual(script.assemble(script.disassemble(words)), words)

    def test_every_vanilla_opcode_roundtrip(self):
        rng = random.Random(59)
        for op, length in enumerate(script.LENGTHS):
            for _ in range(20):
                words = [(op << 26) | rng.randrange(1 << 26)]
                words += [rng.randrange(1 << 32) for _ in range(length - 1)]
                self.assertEqual(script.assemble(script.disassemble(words)), words)

    def test_every_escape_roundtrip(self):
        rng = random.Random(5)
        for sub in script.SUBS.values():
            for length in range(1, 16):
                words = [(59 << 26) | (sub << 20) | (length << 16) | rng.randrange(65536)]
                words += [rng.randrange(1 << 32) for _ in range(length - 1)]
                self.assertEqual(script.assemble(script.disassemble(words)), words)

    def test_script_errors(self):
        for source in ("wait -1", "hitbox joint=999", "SET la_i:64 1", "CALL typo 0", "PUT typo 1"):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "line 1"):
                script.assemble(source)
        for words in ([11 << 26], [60 << 26]):
            with self.assertRaises(ValueError):
                script.disassemble(words)

    def test_validator_bad_examples(self):
        valid = {"geno": 5, "fighters": [{"attach": "kirby"}]}
        examples = [({"geno": 5, "fighters": [{"attach": "kirby", "jump": {}}]}, "jumps"),
                    ({"geno": "5", "fighters": []}, "type"),
                    ({"geno": 5, "fighters": [{"attach": "kiby"}]}, "attach"),
                    ({"geno": 5, "fighters": [{"attach": "kirby", "states": [{}] * 49}]}, "48"),
                    ({"geno": 5, "fighters": [{"attach": "kirby", "specials": {"n": "geno:Missing"}}]}, "Missing")]
        for data, expected in examples:
            with self.subTest(expected=expected):
                self.assertIn(expected, str(check.validate(data, Path.cwd())))
        self.assertEqual(check.validate(valid, Path.cwd()), [])

    def test_export_stub_and_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "out"
            # Synthetic output is outside the synthetic repositories even when
            # TEMP is deliberately kept inside the real workspace.
            with patch.object(schema, "ROOT", Path(directory) / "workspace"), \
                    patch.object(source, "GAME", Path(directory) / "game"):
                export.write_scripts({"row-0": [0x04000005, 0]}, dest)
            text = (dest / "row-0.genoasm").read_text()
            self.assertIn("must not be shared", text)
            self.assertEqual(script.assemble(text), [0x04000005, 0])
        with self.assertRaises(ValueError):
            export.safe_output(schema.ROOT / "_build/geno-export")

    def test_export_refuses_separate_game_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with patch.object(schema, "ROOT", base / "workspace"), \
                    patch.object(source, "GAME", base / "game"):
                for repo in (schema.ROOT, source.GAME):
                    with self.subTest(repo=repo.name), self.assertRaises(ValueError):
                        export.safe_output(repo / "_build/export")
                self.assertEqual(export.safe_output(base / "external"), (base / "external").resolve())

    def test_export_reader_stub(self):
        class ArchiveStub:
            data_size = 256
            publics = [("ftDataStub", 16)]
            reloc_set = {28, 64, 76}
            def u32(self, off):
                return {28: 64, 64: 128, 76: 160, 160: 0x04000005, 164: 0}[off]
            def cstr(self, off):
                return "PlyStub_ACTION_Test_figatree"
        class DiscStub:
            def read(self, name):
                self.name = name
                return b"stub"
        disc = DiscStub()
        scripts, manifest = export.read_fighter(disc, "kirby", [0], archive_factory=lambda _: ArchiveStub())
        self.assertEqual(disc.name, "PlKb.dat")
        self.assertEqual(scripts, {"action-row-0": [0x04000005, 0]})
        self.assertEqual(manifest[0]["row"], 0)
        with self.assertRaisesRegex(ValueError, "no relocated"):
            export.read_fighter(disc, "kirby", [1], archive_factory=lambda _: ArchiveStub())
        ar = ArchiveStub()
        with patch.object(ar, "u32", return_value=5 << 26), self.assertRaisesRegex(ValueError, "Subroutine"):
            export.read_script(ar, 160)

    def test_every_symbolic_escape(self):
        samples = {"NOP": "NOP", "SET": "SET la_i:1 2", "ADD": "ADD la_f:2 1.5", "SUB": "SUB ra_i:2 la_i:1",
                   "MUL": "MUL ra_f:0 2", "DIV": "DIV la_i:0 3", "RAND": "RAND la_f:0 1.0",
                   "SETBIT": "SETBIT la_i:0 2", "CLRBIT": "CLRBIT ra_i:0 3", "GET": "GET ra_f:0 STICK_X",
                   "PUT": "PUT ANIM_RATE 1.5", "IF": "IF la_i:0 EQ 2 0", "IFV": "IFV AIR EQ 1 0",
                   "SKIP": "SKIP 0", "ORIG": "ORIG", "CALL": "CALL geno.brake -1",
                   "CHG": "CHG geno:0 FRAME 12 ONCE", "CHGAND": "CHGAND AIR", "CHGCLR": "CHGCLR",
                   "REHIT": "REHIT 1 6", "LINK": "LINK 1 SPEED", "HBDMG": "HBDMG 1 5.5",
                   "HBSTUN": "HBSTUN 1 12", "HBFLAGS": "HBFLAGS 1 NO_HITLAG|FLINCHLESS"}
        self.assertEqual(set(samples), set(script.SUBS))
        for key, text in samples.items():
            with self.subTest(key=key):
                words = script.assemble(text)
                self.assertEqual(script.assemble(script.disassemble(words)), words)
                self.assertNotIn("raw=", script.disassemble(words))
        self.assertEqual(script.assemble("CHG motion:14 FRAME 12")[2], 12)

    def test_every_condition_value_hook(self):
        conditions = {"ALWAYS": "", "ANIM_END": "", "GROUND": "", "AIR": "", "PRESSED": "ATTACK|JUMP", "HELD": "SHIELD",
                      "BIT": "la_i:0 4", "VAR": "ra_i:0 GE 2", "FRAME": "5", "VALUE": "STICK_LEN GE 0.25"}
        self.assertEqual(set(conditions), set(script.CONDS))
        for name, args in conditions.items():
            text = f"CHG motion:14 {name} {args}"
            words = script.assemble(text)
            self.assertEqual(script.assemble(script.disassemble(words)), words)
        for name in script.VALUES:
            name = name + ":0" if name.startswith("SPECIAL_") else name
            words = script.assemble(f"GET la_f:0 {name}")
            self.assertEqual(script.assemble(script.disassemble(words)), words)
        for name in schema.S["hooks"]:
            words = script.assemble(f"CALL {name} 0")
            self.assertEqual(script.assemble(script.disassemble(words)), words)
        with self.assertRaisesRegex(ValueError, "read-only"):
            script.assemble("PUT SPECIAL_F:0 3")

    def test_named_vanilla_fields(self):
        for text in ("sfx behavior=0 sfx_id=123 volume=127 panning=64",
                     "gfx boneId=2 gfxID=123 offsetY=256", "cmd_var idx=1 value=1",
                     "smash_charge charge_frames=60 charge_rate=350 color_anim=119"):
            words = script.assemble(text)
            self.assertEqual(script.assemble(script.disassemble(words)), words)
            self.assertNotIn("raw=", script.disassemble(words))

    def test_all_schema_rules_have_failing_examples(self):
        tested = 0
        def walk(node):
            nonlocal tested
            if not isinstance(node, dict):
                return
            samples = {}
            if "type" in node:
                samples["type"] = None
            if "maximum" in node:
                samples["maximum"] = node["maximum"] + 1
            if "minimum" in node:
                samples["minimum"] = node["minimum"] - 1
            if "maxItems" in node:
                samples["maxItems"] = [None] * (node["maxItems"] + 1)
            if "maxLength" in node:
                samples["maxLength"] = "x" * (node["maxLength"] + 1)
            if "enum" in node:
                samples["enum"] = "not-a-valid-enumeration"
            if "pattern" in node:
                samples["pattern"] = "\x00!invalid!"
            if "additionalProperties" in node:
                samples["additionalProperties"] = {"unknown_key": 1}
            if "required" in node:
                samples["required"] = {}
            if "minItems" in node:
                samples["minItems"] = []
            if "maxProperties" in node:
                samples["maxProperties"] = {str(i): 0 for i in range(node["maxProperties"] + 1)}
            for rule, value in samples.items():
                with self.subTest(rule=rule, node=node.get("description", "container")):
                    self.assertTrue(any(e.validator == rule for e in check.Draft202012Validator(node).iter_errors(value)))
                    tested += 1
            for key in ("properties", "$defs"):
                for child in node.get(key, {}).values():
                    walk(child)
            if "items" in node:
                walk(node["items"])
            for key in ("anyOf", "oneOf", "allOf"):
                for child in node.get(key, []):
                    walk(child)
        walk(schema.build_schema())
        walk(check.mod_schema())
        self.assertGreater(tested, 300)

    def test_semantic_validation_rules(self):
        examples = [({"states": [{"name": "X"}, {"name": "x"}]}, "duplicate name"),
                    ({"states": [{"next": "geno:1"}]}, "index 1"),
                    ({"states": [{"like": "geno:NotAllowed"}]}, "unresolved"),
                    ({"states": [{"counter": {"from": 10, "to": 2}}]}, "from must"),
                    ({"hooks": {"on_init": ["geno.typo"]}}, "unknown hook"),
                    ({"hooks": {"on_init": ["geno.log:no"]}}, "invalid literal"),
                    ({"hooks": {"on_init": ["geno.count_frames:64"]}}, "0..63"),
                    ({"hooks": {"on_init": ["geno.article.spawn:0"]}}, "missing article"),
                    ({"articles": [{"children": [{"article": "Unknown"}]}]}, "no declared article"),
                    ({"articles": [{"children": [{"article": 0, "spawn": 1}]}]}, "variant missing"),
                    ({"special_attributes": [{"offset": 3, "float": 1}]}, "4-aligned"),
                    ({"subactions": [{"index": 1, "words": [0]}, {"index": 1, "words": [0]}]}, "duplicate overlay"),
                    ({"subactions": [{"index": 1, "file": "../bad.txt"}]}, "inside the mod"),
                    ({"subactions": [{"index": 1, "file": "missing.txt"}]}, "missing file"),
                    ({"subactions": [{"index": 1, "words": [str(2**32)]}]}, "32-bit"),
                    ({"fx_bindings": "missing.json"}, "missing file"),
                    ({"articles": [{"fx": "missing"}]}, "package not found")]
        for fields, expected in examples:
            data = {"geno": 5, "fighters": [{"attach": "kirby", **fields}]}
            with self.subTest(fields=fields):
                self.assertIn(expected, str(check.validate(data, Path.cwd())))
        both = {"geno": 5, "fighters": [{"attach": "kirby"}, {"attach": "PlKb.dat"}]}
        self.assertIn("same fighter", str(check.validate(both, Path.cwd())))

    def test_script_validation_rules(self):
        examples = [("IF la_i:0 EQ 1 1\nhitbox joint=2\nend", "boundary"),
                    ("CHGAND AIR", "preceding CHG"),
                    ("CHG geno:1 ALWAYS", "no declared state"),
                    ("CHG motion:14 ALWAYS\n" * 9, "cap exceeded"),
                    ("CHG motion:14 ALWAYS\nCHGAND AIR\nCHGAND AIR\nCHGAND AIR", "cap exceeded"),
                    ("loop 2", "without endloop"), ("loop_end", "without loop"),
                    ("call 0 0", "cannot resolve"),
                    ("CALL geno.count_frames 64", "0..63"), ("CALL geno.article.spawn 0", "missing article"),
                    ("SET raw=0xEC110000", "at least 2"), ("GET raw=0xEC820000,0xFFFF", "unknown engine value"),
                    ("CALL raw=0xEE030000,99,0", "unknown hook"),
                    ("CHG raw=0xEF020A00,0", "unknown change-action"),
                    ("PUT raw=0xEC930000,0x1000,0", "read-only")]
        for text, expected in examples:
            errors = []
            check.validate_script(script.assemble(text), "$", errors)
            with self.subTest(text=text):
                self.assertIn(expected, str(errors))

    def test_json_dialect_and_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            file = base / "geno.json"
            file.write_text('{"geno":5,//comment\n"fighters":[{"attach":"kirby",},],}')
            self.assertEqual(check.validate(check.load_json(file), base), [])
            file.write_text('{"geno":5,\n"fighters": [}')
            (base / "mod.json").write_text('{}')
            errors = check.validate_path(file)
            self.assertEqual(errors[0]["line"], 2)
            self.assertIn("column", errors[0])
            file.write_text('{"geno":5,"geno":4}')
            with self.assertRaisesRegex(ValueError, "duplicate key"):
                check.load_json(file)
            file.write_text('{"geno":NaN}')
            with self.assertRaisesRegex(ValueError, "nonfinite"):
                check.load_json(file)
            (base / "PlCo.dat").write_bytes(b"refused stub")
            self.assertIn("whole game", str(check.refusal_files(base)))

    def test_dom_and_pool_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            words = base / "long.txt"
            words.write_text("0\n" * 16384)
            data = {"geno": 5, "fighters": [{"attach": "kirby", "subactions": [{"index": 0, "file": "long.txt"}]}]}
            self.assertIn("GENO_POOL_WORDS", str(check.validate(data, base)))
        data = {"geno": 5, "fighters": [{"attach": "kirby", "subactions": [{"index": 0, "words": [0] * 4100}]}]}
        self.assertIn("JDOC_NODES", str(check.validate(data, Path.cwd())))

    def test_tree_script_roundtrips(self):
        # Read generated fighters too; emit only counts, never derived word data.
        result = subprocess.run(["rg", "--files", "--no-ignore", "--hidden", "-g", "geno.json",
                                 "-g", "!.git/**", "-g", "!melee/.git/**", "-g", "!_build/archived-worktrees/**",
                                 "-g", "!_build/archive/**", "-g", "!_build/agents/*/melee/**",
                                 "-g", "!_build/audit-20261003/mission-verify/**"], cwd=schema.ROOT, capture_output=True, text=True)
        if result.returncode not in (0, 1):
            self.fail("fixture inventory could not be read: " + result.stderr)
        checked = missing = 0
        for name in result.stdout.splitlines():
            file = schema.ROOT / name
            data = check.load_json(file)
            for fighter in data.get("fighters", []):
                for row in fighter.get("subactions", []):
                    if "words" in row:
                        words = [script.word(w) for w in row["words"]]
                    elif "file" in row:
                        source = file.parent / row["file"].replace("\\", "/")
                        if not source.is_file():
                            missing += 1
                            continue
                        words = script.read_words(source.read_text(encoding="utf-8-sig"))
                    else:
                        continue
                    with self.subTest(file=name, row=row.get("index")):
                        self.assertEqual(script.assemble(script.disassemble(words)), words)
                    checked += 1
        self.assertGreater(checked, 0)
        print(f"Geno corpus: {len(result.stdout.splitlines())} profiles files, {checked} overlay scripts round-tripped; {missing} missing external word files")

    def test_nested_typos_utf8_and_effect_bindings(self):
        typo = {"geno": 5, "fighters": [{"attach": "kirby", "specials": {"n": {"gruond": "motion:14"}}}]}
        self.assertIn("did you mean", str(check.validate(typo, Path.cwd())))
        self.assertIn("byte", str(check.schema_errors({"id": "é" * 40}, check.mod_schema())))
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = {"geno": 5, "fighters": [{"attach": "kirby", "fx_bindings": "fx.json"}]}
            (base / "fx.json").write_text(json.dumps({"geno_fx_bindings": 1, "states": [{"subaction": 0, "calls": [{"package": "missing"}]}]}))
            self.assertIn("cannot resolve", str(check.validate(data, base)))
            (base / "fx.json").write_text(json.dumps({"geno_fx_bindings": 1, "states": [{"subaction": 0, "calls": []}] * 97}))
            self.assertIn("FX_BIND_STATES", str(check.validate(data, base)))
            (base / "fx.json").write_text('{"geno_fx_bindings": 0, "states": []}')
            self.assertTrue(check.validate(data, base))


if __name__ == "__main__":
    unittest.main()
