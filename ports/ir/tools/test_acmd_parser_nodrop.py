import unittest
import hashlib
import json
from pathlib import Path
import tempfile

import acmd_parse as AP
from acmd_loss import verify_acmd_source


class ParserNoDropTest(unittest.TestCase):
    def test_unrecognized_mutating_call_reaches_converter(self):
        src = "// BODY @\napp::sv_module_access::unknown(luaState);\n"
        commands = AP.parse_body(src, None, {})
        self.assertEqual(commands[0]["cmd"], "sv_module_access::unknown")

    def test_frame_extra_argument_is_preserved(self):
        src = """// BODY @ synthetic
lib::L2CValue::L2CValue(aLStack_90,2);
lib::L2CValue::L2CValue(aLStack_91,5);
app::sv_animcmd::frame(plVar10,fVar11);
"""
        commands = AP.parse_body(src, None, {})
        self.assertEqual(commands[0]["args"], [2, 5])

    def test_smash_flag_extra_argument_is_preserved(self):
        src = """// BODY @ synthetic
lib::L2CValue::L2CValue(aLStack_90,FIGHTER_STATUS_ATTACK_FLAG_START_SMASH_HOLD);
lib::L2CValue::L2CValue(aLStack_91,5);
app::lua_bind::WorkModule__on_flag_impl(module,flag);
"""
        commands = AP.parse_body(src, None, {})
        self.assertEqual(commands[0]["cmd"], "WorkModule::on_flag")
        self.assertEqual(len(commands[0]["args"]), 2)

    def test_stale_parsed_json_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, "acmd.json")
            source.write_text("[]", encoding="utf-8")
            audit = {"version": 1, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                     "parser_sha256": hashlib.sha256(Path(AP.__file__).read_bytes()).hexdigest()}
            Path(str(source) + ".audit.json").write_text(json.dumps(audit), encoding="utf-8")
            self.assertEqual(verify_acmd_source(source), b"[]")
            source.write_text("[1]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale ACMD parse"):
                verify_acmd_source(source)


if __name__ == "__main__":
    unittest.main()
