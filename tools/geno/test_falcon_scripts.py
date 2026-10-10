"""Synthetic ftcmd fidelity tests; local retail corpus is opt-in and never copied here."""
import os
import re
from pathlib import Path

import pytest
from tools.test_support import require_game

require_game("pc/geno/geno.h")
from tools.geno import script


@pytest.mark.parametrize("flags", [0, 1, 7, 31])
@pytest.mark.parametrize("sound", [0, 1, 127, 1023])
def test_hitbox_flags_stay_editable_and_exact(flags, sound):
    # Explicit synthetic words, including unused header bits: dropping any bit is a bug.
    words = [(11 << 26) | (2 << 23) | (11 << 19) | (7 << 11) | (1 << 10) | 9,
             (769 << 16) | 0xFF01, (513 << 16) | 0x8001,
             (361 << 23) | (101 << 14) | (17 << 5) | flags,
             (27 << 23) | (2 << 18) | (0xFE << 10) | sound]
    source = script.disassemble(words)
    assert source.startswith("hitbox slot=2 joint=7 damage=9 size=3.00390625")
    assert "raw=" not in source
    assert script.assemble(source) == words
    edited = source.replace("damage=9 ", "damage=13 ")
    assert script.assemble(edited) == [words[0] + 4, *words[1:]]


def test_relative_subroutine_and_goto_keep_every_word():
    words = [5 << 26, 3, 0, (1 << 26) | 5, 7 << 26, 3]
    assert script.assemble(script.disassemble(words)) == words


def test_local_falcon_every_overlay_roundtrips():
    package = Path(os.environ.get("GW_FALCON_PACKAGE", str(Path(__file__).resolve().parents[2] /
                   "_build/falcon-look/geno-falcon")))
    if not (package / "geno.json").is_file():
        pytest.skip("local Geno Falcon package missing (set GW_FALCON_PACKAGE)")
    import json
    document = json.loads((package / "geno.json").read_text(encoding="utf-8"))
    overlays = document["fighters"][0]["subactions"]
    assert overlays, "package was built without scripts"
    for overlay in overlays:
        words = ([script.word(w) for w in overlay["words"]] if "words" in overlay else
                 script.read_words((package / overlay["file"]).read_text(encoding="utf-8")))
        source = script.disassemble(words)
        assert script.assemble(source) == words, overlay["index"]
        # Workbench's source parser needs named fields, not hitbox raw= fallback.
        for line in source.splitlines():
            if line.startswith("hitbox "):
                assert re.search(r"joint=\d+", line), (overlay["index"], line)
                assert "raw=" not in line, (overlay["index"], line)
