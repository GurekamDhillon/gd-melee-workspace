import unittest

import trail_fx_bindings as FX


def row(*commands):
    return {"agent": "trail", "script": "effect_test", "source_file": "effect/test.c",
            "share": False, "owner": "fighter", "commands": list(commands)}


class EffectNoDropTest(unittest.TestCase):
    def test_unknown_effect_macro_fails(self):
        with self.assertRaisesRegex(ValueError, "MYSTERY_EFFECT"):
            FX.census([row({"frame": 2, "cmd": "MYSTERY_EFFECT", "args": [1]})], {}, {"top": 0}, 1)

    def test_malformed_effect_call_fails(self):
        with self.assertRaisesRegex(ValueError, "EFFECT.*arguments"):
            FX.census([row({"frame": 2, "cmd": "EFFECT", "args": ["x"]})], {}, {"top": 0}, 1)

    def test_common_effect_requires_review(self):
        command = {"frame": 2, "cmd": "EFFECT", "args": ["sys_smoke", "top", 0, 0, 0, 0, 0, 0, 1]}
        with self.assertRaisesRegex(ValueError, "effect.common"):
            FX.census([row(command)], {}, {"top": 0}, 1)

    def test_after_image_requires_review(self):
        with self.assertRaisesRegex(ValueError, "AFTER_IMAGE_ON"):
            FX.census([row({"frame": 2, "cmd": "AFTER_IMAGE_ON", "args": []})], {}, {"top": 0}, 1)

    def test_unbound_package_requires_review(self):
        scripts = [{"agent": "trail", "script": "effect_test", "calls": [
            {"frame": 2, "effect": "own", "package": "P_Test", "source": ["effect/test.c", 0]}]}]
        with self.assertRaisesRegex(ValueError, "effect.unbound"):
            FX.audit_unbound(scripts, {"states": []})

    def test_effect_end_extra_args_require_review(self):
        call = {"frame": 2, "cmd": "EFFECT", "args": ["own", "top", 0, 0, 0, 0, 0, 0, 1]}
        end = {"frame": 4, "cmd": "EFFECT_OFF_KIND", "args": ["own", True]}
        own = {0: ("own", "P_Test")}
        with self.assertRaisesRegex(ValueError, "EFFECT_OFF_KIND.extra_args"):
            FX.census([row(call, end)], own, {"top": 0}, 1)

    def test_unresolved_effect_timing_fails(self):
        with self.assertRaisesRegex(ValueError, "frame.*unresolved"):
            FX.census([row({"frame": 0, "cmd": "frame", "args": ["variable"],
                            "unresolved_frame": True})], {}, {"top": 0}, 1)


if __name__ == "__main__":
    unittest.main()
