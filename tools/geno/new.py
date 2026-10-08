"""Create a source-only native reference fighter; never read a disc."""
import argparse
import json
from pathlib import Path
import re
from . import script

JAB = """# Authored Hero jab: 12% instead of the inherited normal.
wait 2
hitbox slot=0 joint=0 damage=12 size=5 x=4 y=7 angle=361 kbg=100 bkb=30
wait 3
clear_hitboxes
wait 6
iasa
"""


SKELETON_FTILT = """# Forward tilt: edit this, run `python -m tools.geno.check <folder>` and `python -m tools.geno.report <folder> --frames`.
PUT ANIM_RATE 1.4
wait 6
hitbox slot=0 joint=55 damage=6 size=3.8 angle=38 kbg=95 bkb=25
wait 3
clear_hitboxes
wait 8
iasa
"""


# --template lua-counter: a down special as a counter answered in Lua (format 10; docs/geno.md section 23, lesson 13). The engine owns the
# counter window (geno.json "counter"); the Lua module reads the countered hit and scales the strike. Edit the numbers, run check.
LUA_COUNTER_LUA = """-- A counter, answered in Lua. The only state is ctx.state (declared in geno.json "lua": {"state": ...}); nothing else survives a call.
local MIN_POWER, MAX_POWER, SCALE = 9, 30, 1.5

local M = {}

function M.parry_frame(ctx)
  if ctx.self.action_frame >= 30 then ctx.go("auto") end       -- the window (frames 4-24, geno.json) has passed: a whiff
end

function M.answer_enter(ctx)
  -- ctx.self.hit_damage is the countered hit (the engine dropped its damage); hit_from is +1 in front, -1 behind, 0 unknown
  ctx.state.power = math.min(MAX_POWER, math.max(MIN_POWER, SCALE * ctx.self.hit_damage))
  if ctx.self.hit_from < 0 then ctx.turn() end
end

function M.answer_frame(ctx)
  ctx.hitbox_damage(3, ctx.state.power)                        -- bit n of the mask = hitbox slot n
end

return M
"""

LUA_COUNTER_PARRY = """# The stance: the animation only. The counter window is geno.json's "counter"; the whiff is lua/counter.lua.
wait 1
"""

LUA_COUNTER_ANSWER = """# The answer to a countered hit. Lua replaces these hitboxes' damage every frame (ctx.hitbox_damage); these numbers are only the shape.
wait 2
hitbox slot=0 joint=0 damage=14 size=6.0 x=3 y=6 angle=45 kbg=100 fkb=0 bkb=55
hitbox slot=1 joint=0 damage=14 size=4.0 x=-3 y=6 angle=45 kbg=100 fkb=0 bkb=55
wait 6
clear_hitboxes
"""


def lua_counter_data(define):
    return {"geno": 10, "fighters": [{
        "define": define,
        "attributes": {"walk_max_vel": 1.5},
        "lua": {"script": "lua/counter.lua", "state": {"power": "float"}},
        "states": [
            {"name": "Parry", "behavior": "geno.ground", "subaction": 295, "like": "motion:349", "phys": "auto", "coll": "both", "iasa": "none",
             "counter": {"from": 4, "to": 24, "target": "geno:Answer"}, "move_tag": "special", "lua": {"frame": "parry_frame"}},
            {"name": "Answer", "behavior": "geno.ground", "subaction": 296, "like": "motion:345", "phys": "auto", "coll": "both",
             "move_tag": "special", "lua": {"enter": "answer_enter", "frame": "answer_frame"}}],
        "specials": {"lw": "geno:Parry", "air_lw": "geno:Parry"},
        "subactions": [{"index": 295, "file": "moves/parry.words", "move_tag": "special"},
                       {"index": 296, "file": "moves/answer.words", "move_tag": "special"}]}]}


def create(root, key, name, base="mario", template=None):
    if base != "mario":
        raise ValueError("slice 1 supports only the native Mario preset")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,38}", key) or ".." in key:
        raise ValueError("key must be a portable lowercase identifier, at most 39 bytes")
    if not name or len(name.encode("ascii", errors="replace")) > 47 or not name.isascii() or not name.isprintable():
        raise ValueError("name must be printable ASCII, 1..47 bytes")
    root = Path(root)
    if root.exists():
        raise ValueError("output already exists; choose a fresh folder")
    if template not in (None, "striker-skeleton", "lua-counter"):
        raise ValueError("unknown template")
    data = {"geno": 6, "fighters": [{
        "define": {"key": key, "name": name, "base": "mario", "common": "melee.common.v1", "resources": "retail:mario"},
        "attributes": {"walk_max_vel": 1.8},
        "subactions": [{"index": 46, "file": "moves/hero-jab.words"}]}]}
    if template == "striker-skeleton":
        # a v7 header with the common attributes a move-set author tunes, one move to edit, and the eight
        # specials left unbound (the checker warns that each runs the donor's code until you bind a state)
        data = {"geno": 7, "fighters": [{
            "define": data["fighters"][0]["define"],
            "attributes": {"walk_max_vel": 1.5, "dash_initial_velocity": 2.0, "weight": 90, "landingairn_lag": 8},
            "subactions": [{"index": 55, "file": "moves/ftilt.words", "move_tag": "tilt"}]}]}
    if template == "lua-counter":
        root.mkdir(parents=True)
        (root / "files").mkdir()
        (root / "files/.gitkeep").write_text("", encoding="utf-8")
        (root / "moves").mkdir()
        (root / "lua").mkdir()
        (root / "mod.json").write_text(json.dumps({"id": key, "name": name, "version": "0.1.0", "kind": "fighter"}, indent=2)+"\n", encoding="utf-8")
        (root / "geno.json").write_text(json.dumps(lua_counter_data(data["fighters"][0]["define"]), indent=2)+"\n", encoding="utf-8")
        (root / "lua/counter.lua").write_text(LUA_COUNTER_LUA, encoding="utf-8")
        for stem, stub in (("parry", LUA_COUNTER_PARRY), ("answer", LUA_COUNTER_ANSWER)):
            (root / f"moves/{stem}.genoasm").write_text(stub, encoding="utf-8")
            (root / f"moves/{stem}.words").write_text(" ".join(f"0x{w:08X}" for w in script.assemble(stub))+"\n", encoding="utf-8")
        (root / "README.md").write_text("# "+name+"\n\nA Geno define with a Lua counter special (format 10): down special, a counter window in the engine, the answer\n"
            "scaled by the countered hit in lua/counter.lua. Offline only. Check it: `python -m tools.geno.check <this folder>`.\n"
            "Reference: docs/geno.md section 23; lesson docs/learn/geno-fighters/13-fighter-lua.md.\n", encoding="utf-8")
        return root
    # Melee's Mario Attack11 animation id is audited against the native state table.
    root.mkdir(parents=True)
    (root / "files").mkdir()  # prevent legacy whole-folder archive mounting
    (root / "files/.gitkeep").write_text("", encoding="utf-8")
    (root / "moves").mkdir()
    (root / "mod.json").write_text(json.dumps({"id": key, "name": name, "version": "0.1.0", "kind": "fighter"}, indent=2)+"\n", encoding="utf-8")
    (root / "geno.json").write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    stub = SKELETON_FTILT if template == "striker-skeleton" else JAB
    stem = "ftilt" if template == "striker-skeleton" else "hero-jab"
    (root / f"moves/{stem}.genoasm").write_text(stub, encoding="utf-8")
    words = script.assemble(stub)
    (root / f"moves/{stem}.words").write_text(" ".join(f"0x{w:08X}" for w in words)+"\n", encoding="utf-8")
    (root / "README.md").write_text("# "+name+"\n\nThe Geno engine native Mario-reference fixture. Offline only.\n"
        "Retail model, clips, effects and sounds are resolved from the user's disc. No disc data ships.\n"
        "Walk speed is 1.8; jab 1 is an authored 12% root-bone hitbox.\n"
        "All other states and scripts inherit the native Mario/common v1 preset.\n"
        "An integrator rebuild and full-stock/LAB verification are required.\n", encoding="utf-8")
    return root


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("key"); ap.add_argument("--name", default="Vanilla Hero")
    ap.add_argument("--base", default="mario"); ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--template", choices=["striker-skeleton", "lua-counter"],
                    help="striker-skeleton: a v7 header and one move stub to start a full move set from; lua-counter: a format 10 define whose down special is a counter answered in Lua")
    args = ap.parse_args()
    try:
        create(args.output, args.key, args.name, args.base, args.template)
        print("Created source-only Geno definition; integrator build required.")
        return 0
    except (ValueError, OSError):
        print("Cannot create definition: unsupported preset, invalid identity or output unavailable.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
