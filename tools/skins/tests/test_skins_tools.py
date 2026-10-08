"""Tests for tools/skins. No disc image needed: the DATs are synthetic HSD archives built here.

Run from the worktree root:  python -m pytest tools/skins/tests -q
"""

import json
import os
import struct
import sys
from pathlib import Path

import pytest

SKINS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKINS))
import skinlib  # noqa: E402
import skin_import  # noqa: E402


def build_hsd(publics=()):
    """A minimal HSD archive: header, a 0x20-byte zero data section, no relocs, no externs."""
    data = bytes(0x20)
    names = b""
    offsets = []
    for name in publics:
        offsets.append(len(names))
        names += name.encode("ascii") + b"\0"
    public_table = b"".join(struct.pack(">II", 0, off) for off in offsets)
    body = data + public_table + names
    header = struct.pack(">IIIII", 0x20 + len(body), len(data), 0, len(publics), 0)
    return header.ljust(0x20, b"\0") + body


FOX_PUBLICS = ("PlyFox5KBu_Share_joint", "PlyFox5KBu_Share_matanim_joint")


def write_dat(path, publics):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_hsd(publics))
    return path


def make_clean_mod(tmp_path, mod_id="tsk-fox-001"):
    dat = write_dat(tmp_path / "src" / "PlFxBu.dat", FOX_PUBLICS)
    mods = tmp_path / "mods"
    skinlib.write_skin_mod(str(mods), mod_id, "Test Fox 1", {"retail": "fox"}, [
        dict(name="Neon", src_dat=str(dat), joint="PlyFox5KBu_Share_joint",
             matanim="PlyFox5KBu_Share_matanim_joint", team="red", like=0, kirby_hat=0),
    ])
    return mods / mod_id


def edit_mod(mod_dir, fn):
    path = mod_dir / "mod.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_retail_table_is_27_in_fighter_kind_order():
    assert [k for k, _, _, _ in skinlib.RETAIL] == list(range(27))
    assert skinlib.RETAIL[0][1:] == ("mario", "Mr", "Mario")
    assert skinlib.RETAIL[7][1] == "seak" and skinlib.RETAIL[11][1] == "nana"


def test_builder_round_trips_through_archive():
    raw = build_hsd(FOX_PUBLICS)
    assert skinlib.Archive(raw).publics == [(FOX_PUBLICS[0], 0), (FOX_PUBLICS[1], 0)]
    assert skinlib.read_publics(raw) == list(FOX_PUBLICS)
    assert skinlib.read_publics(build_hsd()) == []


def test_classify_fox_costume():
    info = skinlib.classify_costume(build_hsd(FOX_PUBLICS))
    assert info["fighter"] == "fox"
    assert info["token"] == "Fox"
    assert info["colour"] == "Bu"
    assert info["joint"] == "PlyFox5KBu_Share_joint"
    assert info["matanim"] == "PlyFox5KBu_Share_matanim_joint"


def test_classify_without_matanim_and_with_empty_colour():
    info = skinlib.classify_costume(build_hsd(("PlyMario5K_Share_joint",)))
    assert info["fighter"] == "mario" and info["colour"] == "" and info["matanim"] is None


def test_dat_without_ply_symbols_raises():
    with pytest.raises(ValueError, match="no public symbol Ply"):
        skinlib.classify_costume(build_hsd(("sceneData", "ftCommonData")))


def test_nana_classifies_as_nana():
    assert skinlib.classify_costume(build_hsd(("PlyNana5K_Share_joint",)))["fighter"] == "nana"


def test_write_and_lint_clean_mod(tmp_path):
    mod = make_clean_mod(tmp_path)
    assert skinlib.lint_skin_mod(str(mod)) == []
    link = mod / "files" / "skins" / "tsk-fox-001" / "1.dat"
    assert link.read_bytes() == build_hsd(FOX_PUBLICS)
    doc = json.loads((mod / "mod.json").read_text(encoding="utf-8"))
    assert doc["kind"] == "skin" and doc["skin"]["format"] == 1
    assert doc["skin"]["target"] == {"retail": "fox"}
    assert "order" not in doc["skin"]
    assert doc["skin"]["costumes"][0] == {
        "name": "Neon", "file": "skins/tsk-fox-001/1.dat", "joint": "PlyFox5KBu_Share_joint",
        "matanim": "PlyFox5KBu_Share_matanim_joint", "team": "red", "like": 0, "kirby_hat": 0}


def test_write_skin_mod_with_art(tmp_path):
    from PIL import Image
    game = os.environ.get("GW_MELEE", skinlib.DEFAULT_GAME)
    if not os.path.isfile(os.path.join(game, "pc", "tools", "png2gx.py")):
        pytest.skip("png2gx.py not available (set GW_MELEE)")
    dat = write_dat(tmp_path / "PlFxBu.dat", FOX_PUBLICS)
    csp, stock = tmp_path / "csp.png", tmp_path / "stock.png"
    Image.new("RGB", (136, 188), (200, 40, 40)).save(csp)
    Image.new("RGBA", (24, 24), (40, 200, 40, 255)).save(stock)
    mod = Path(skinlib.write_skin_mod(str(tmp_path / "m"), "tsk-fox-art", "Art", {"retail": "fox"}, [
        dict(name="Art", src_dat=str(dat), joint="PlyFox5KBu_Share_joint",
             csp_png=str(csp), stock_png=str(stock))]))
    files = mod / "files" / "skins" / "tsk-fox-art"
    assert (files / "1_csp.gxtex").is_file() and (files / "1_stock.gxtex").is_file()
    assert skinlib.lint_skin_mod(str(mod)) == []


def test_lint_unknown_key_in_skin(tmp_path):
    mod = make_clean_mod(tmp_path)
    edit_mod(mod, lambda d: d["skin"].__setitem__("bogus", 1))
    assert any("bogus" in p for p in skinlib.lint_skin_mod(str(mod)))


def test_lint_missing_file(tmp_path):
    mod = make_clean_mod(tmp_path)
    os.remove(mod / "files" / "skins" / "tsk-fox-001" / "1.dat")
    assert any("not in files/" in p for p in skinlib.lint_skin_mod(str(mod)))


def test_lint_non_ascii_name(tmp_path):
    mod = make_clean_mod(tmp_path)
    edit_mod(mod, lambda d: d["skin"]["costumes"][0].__setitem__("name", "Neön"))
    assert any("name" in p and "printable ASCII" in p for p in skinlib.lint_skin_mod(str(mod)))


def test_lint_team_purple(tmp_path):
    mod = make_clean_mod(tmp_path)
    edit_mod(mod, lambda d: d["skin"]["costumes"][0].__setitem__("team", "purple"))
    assert any("purple" in p for p in skinlib.lint_skin_mod(str(mod)))


def test_lint_kirby_hat_9(tmp_path):
    mod = make_clean_mod(tmp_path)
    edit_mod(mod, lambda d: d["skin"]["costumes"][0].__setitem__("kirby_hat", 9))
    assert any("kirby_hat" in p for p in skinlib.lint_skin_mod(str(mod)))


def test_lint_no_costumes(tmp_path):
    mod = make_clean_mod(tmp_path)
    edit_mod(mod, lambda d: d["skin"].__setitem__("costumes", []))
    assert any("non-empty" in p for p in skinlib.lint_skin_mod(str(mod)))


def test_lint_rejects_unsafe_path_and_bad_kind(tmp_path):
    mod = make_clean_mod(tmp_path)

    def tamper(d):
        d["kind"] = "fighter"
        d["skin"]["costumes"][0]["file"] = "../../evil.dat"
    edit_mod(mod, tamper)
    problems = skinlib.lint_skin_mod(str(mod))
    assert any("kind" in p for p in problems)
    assert any(".." in p for p in problems)


def test_lint_unparseable_json(tmp_path):
    (tmp_path / "mod.json").write_text("{nope", encoding="utf-8")
    assert skinlib.lint_skin_mod(str(tmp_path))[0].startswith("mod.json does not parse")


def test_skin_import_single_file_writes_lintable_mod(tmp_path, capsys):
    inp = write_dat(tmp_path / "in" / "fox.dat", FOX_PUBLICS)
    out = tmp_path / "mods"
    assert skin_import.main([str(inp), "--out", str(out), "--author", "tester"]) == 0
    assert skinlib.lint_skin_mod(str(out / "fox")) == []
    assert "skin fox: retail:fox fox" in capsys.readouterr().out
    assert json.loads((out / "fox" / "mod.json").read_text(encoding="utf-8"))["authors"] == "tester"


def test_skin_import_folder_and_lint_only(tmp_path, capsys):
    inp = tmp_path / "in"
    write_dat(inp / "fox.dat", FOX_PUBLICS)
    write_dat(inp / "pikachu.usd", ("PlyPikachu5KBu_Share_joint",))
    out = tmp_path / "mods"
    assert skin_import.main([str(inp), "--out", str(out)]) == 0
    for mod in ("fox", "pikachu"):
        assert skinlib.lint_skin_mod(str(out / mod)) == []
    capsys.readouterr()
    assert skin_import.main(["--lint-only", str(out / "fox")]) == 0
    assert capsys.readouterr().out.strip() == "clean"


def test_skin_import_refuses_seak(tmp_path, capsys):
    inp = write_dat(tmp_path / "in" / "seak.dat", ("PlySeak5KBu_Share_joint",))
    out = tmp_path / "mods"
    assert skin_import.main([str(inp), "--out", str(out)]) == 1
    assert "Ice Climbers / Sheik costumes belong with Popo / Zelda" in capsys.readouterr().err
    assert not (out / "seak").exists()


def test_skin_import_refuses_nana(tmp_path, capsys):
    inp = write_dat(tmp_path / "in" / "nana.dat", ("PlyNana5K_Share_joint",))
    assert skin_import.main([str(inp), "--out", str(tmp_path / "mods")]) == 1
    assert "Ice Climbers" in capsys.readouterr().err


def test_skin_import_refuses_disc_image(tmp_path):
    with pytest.raises(SystemExit):
        skin_import.main([str(tmp_path / "game.iso"), "--out", str(tmp_path / "mods")])
