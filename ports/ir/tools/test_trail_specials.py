#!/usr/bin/env python3
"""Offline word-file checks for Sora's optional physical-special branches."""
import json
import os
import struct
import subprocess
import sys

import trail_specials_geno as sp


ROOT = sp.ROOT
OUT = os.path.join(ROOT, "_build", "tmp", "codex-specials", "test")
ACMD = os.path.join(ROOT, "_build", "tmp", "ir", "trail.acmd.json")
MAGIC = os.path.join(ROOT, "_build", "agents", "beta", "mods-sora-magic", "sora-magic-demo", "geno.json")
OPTIONS = ("--sonic-hit-branch", "--counter-backward", "--counter-rebound")


def generate(host, magic=False, options=OPTIONS):
    dest = os.path.join(OUT, host + ("-magic" if magic else "") + ("-all" if options else "-default"))
    args = [sys.executable, sp.__file__, "--host", host, "-o", dest, *options]
    if magic:
        args += ["--magic", MAGIC]
    subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    doc = json.load(open(os.path.join(dest, "geno.json"), encoding="utf-8"))["fighters"][0]
    clips = json.load(open(os.path.join(dest, "clips.json"), encoding="utf-8"))
    return dest, doc, clips


def decode(path):
    """Decode command boundaries and game frames from a Geno word file."""
    words = [int(w, 16) for line in open(path, encoding="utf-8") if not line.startswith("#")
             for w in line.split()]
    out, pos, frame = [], 0, 0
    while pos < len(words):
        w = words[pos]
        op = w >> 26
        if op == sp.GENO_OP:
            size = (w >> 16) & 15
            assert size > 0 and pos + size <= len(words)
            sub = (w >> 20) & 63
        elif op == 11:
            size, sub = 5, None
        else:
            size, sub = 1, None
        event = {"frame": frame, "offset": pos, "op": op, "sub": sub, "words": words[pos:pos + size]}
        out.append(event)
        pos += size
        if op == 1:
            frame += w & 0x3FFFFFF
        if w == 0:
            assert pos == len(words)
            break
    return out


def events_for(dest, doc, name):
    state = next(s for s in doc["states"] if s["name"] == name)
    overlay = next(o for o in doc["subactions"] if o["index"] == state["subaction"])
    return decode(os.path.join(dest, overlay["file"]))


def hits(events):
    out = []
    for e in events:
        if e["op"] != 11:
            continue
        w0, _, _, w3, w4 = e["words"]
        out.append((e["frame"], (w0 >> 23) & 7, w0 & 1023,
                    (w3 >> 23) & 511, (w3 >> 14) & 511, (w4 >> 23) & 511))
    return out


def f32(bits):
    return struct.unpack(">f", struct.pack(">I", bits))[0]


def check_sonic(dest, doc, default_dest, default_doc, dump):
    # game_specials2: 0xe9c8f6931.c lines 96-116, 300-311; game_specials3:
    # 0xeeb8859a7.c lines 96-116, 300-311. False flag = 3.0%, true = 5.2%.
    expected = {"SDash2": [(3.0, 108, 8, 80), (5.2, 108, 8, 80)],
                "SDash3": [(3.0, 46, 88, 80), (5.2, 46, 85, 80)]}
    hover = events_for(dest, doc, "SStart2")
    hover_get = [e for e in hover if e["frame"] == 0 and e["sub"] == 0x08]
    assert len(hover_get) == 1
    assert hover_get[0]["words"] == sp.GET(sp.var(sp.LAI, sp.SONIC_PREV_N), sp.V_ATTACK_CONNECTED_PREV)
    assert next(e for e in hover if e["frame"] == 0)["words"] == hover_get[0]["words"]
    assert not any(e["sub"] == 0x08 for e in events_for(default_dest, default_doc, "SStart2"))
    for name, want in expected.items():
        row = next(r for r in dump if r["script"] == "game_specials" + name[-1] and r["kind"] == "game")
        branch = [c["named"] for c in row["commands"] if c["cmd"] == "ATTACK" and c["frame"] == 3]
        assert len(branch) == 6
        assert [(d, a, k, b) for d, a, k, b in want] == sorted({
            (n["damage"], n["angle"], n["kbg"], n["bkb"]) for n in branch})
        assert all(c["when"][0]["holds"] == (c["named"]["damage"] == 3.0) for c in row["commands"]
                   if c["cmd"] == "ATTACK" and c["frame"] == 3)
        ev = events_for(dest, doc, name)
        assert not any(e["frame"] == 3 and e["sub"] == 0x12 and e["words"][1] in (0x3B, 0x3C)
                       for e in ev)
        f3 = [e for e in ev if e["frame"] == 3 and (e["op"] == 11 or
              (e["sub"] == 0x10 and (e["words"][0] >> 8) & 255 == sp.var(sp.LAI, sp.SONIC_PREV_N)))]
        assert [e["sub"] if e["op"] == sp.GENO_OP else 11 for e in f3] == [0x10, 11, 11, 11, 0x10, 11, 11, 11]
        for connected, group in enumerate((f3[:4], f3[4:])):
            guard = group[0]["words"]
            assert guard[1:] == [connected, 15]
            assert ((guard[0] >> 8) & 255) == sp.var(sp.LAI, sp.SONIC_PREV_N)
            assert ((guard[0] >> 4) & 7) == sp.EQ
            actual = hits(group[1:])
            dmg, angle, kbg, bkb = want[connected]
            assert actual == [(3, slot, round(dmg), angle, kbg, bkb) for slot in range(3)]
    # Dash 1 has no branch and must match the default generator byte for byte.
    assert events_for(dest, doc, "SDash1") == events_for(default_dest, default_doc, "SDash1")


def check_counter(dest, doc, clips):
    for name, back_name, clip in (("LwAttack", "LwAttackBack", "d03speciallwbackward"),
                                  ("LwAttackAir", "LwAttackBackAir", "d03specialairlwbackward")):
        ev = events_for(dest, doc, name)
        back = events_for(dest, doc, back_name)
        target = next(i for i, s in enumerate(doc["states"]) if s["name"] == back_name)
        initial = [e for e in ev if e["frame"] == 0]
        get_pos = next(i for i, e in enumerate(initial) if e["sub"] == 0x08 and e["words"][1] == sp.V_FACING)
        assert initial[get_pos]["words"][0] >> 8 & 255 == sp.var(sp.RAF, 6)
        assert initial[get_pos + 1]["sub"] == 0x20 and initial[get_pos + 1]["words"][1] == sp.HOOK_LOCKON
        guard = initial[get_pos + 2]
        assert guard["sub"] == 0x12 and guard["words"][1:] == [sp.V_FACING, sp.var(sp.RAF, 6), 2]
        assert guard["words"][0] & 0x80 and (guard["words"][0] >> 4) & 7 == sp.NE
        assert initial[get_pos + 3]["sub"] == 0x30 and initial[get_pos + 3]["words"][1] == sp.GENO(target)
        assert not any(e["sub"] == 0x20 and e["words"][1] == sp.HOOK_LOCKON for e in back)
        # 0xe5763d2b0.c / 0x1145a0283d.c: frame 7 hitboxes, resets at 10 and 11.
        assert sorted(set(h[0] for h in hits(ev))) == [7, 10, 11]
        assert hits(back) == hits(ev)
        assert len([e for e in back if e["sub"] == 0x3A]) == len([e for e in ev if e["sub"] == 0x3A])
        puts = [f32(e["words"][2]) for e in back if e["sub"] == 0x09 and e["words"][1] == sp.V_FWD_VEL]
        frames, dz = sp.clip_info(clip)
        assert frames == 60 and len(puts) == frames
        # lock-on turned Sora to the attacker: the clip's retreat (sum dz < 0) is a move toward it
        assert abs(sum(puts) + sum(dz)) < 1e-4 and sum(puts) > 0
        state = next(s for s in doc["states"] if s["name"] == back_name)
        assert clips["subaction_clips"][str(state["subaction"])] == clip
        assert clips["turn_clips"][str(state["subaction"])] == ("d03specialairlwturn" if "Air" in name else "d03speciallwturn")
        assert max(e["frame"] for e in back) == frames


def check_rebound(dest, doc):
    for name in ("LwRebound", "LwReboundAir"):
        ev = events_for(dest, doc, name)
        assert max(e["frame"] for e in ev) == 19
        assert not hits(ev)
        assert any(e["frame"] == 0 and e["op"] == 26 and e["words"][0] == sp.INTANGIBLE[0] for e in ev)
        assert any(e["frame"] == 19 and e["op"] == 26 and e["words"][0] == sp.NORMAL[0] for e in ev)
        assert not any(e["sub"] == 0x3A for e in ev)
    expected_targets = {"SStart": {"SDash1"}, "SStart2": {"SDash2", "SDash3"},
                        "SDash1": {"SStart2", "SEnd", "SEndAir"},
                        "SDash2": {"SStart2", "SEnd", "SEndAir"},
                        "SDash3": {"SEnd", "SEndAir"}, "LwAttack": {"LwAttackBack"},
                        "LwAttackAir": {"LwAttackBackAir"}}
    for state in doc["states"]:
        targets = set()
        for e in events_for(dest, doc, state["name"]):
            if e["sub"] == 0x30 and e["words"][1] >> 28 == 2:
                target = e["words"][1] & 0xFFFF
                assert 0 <= target < len(doc["states"])
                targets.add(doc["states"][target]["name"])
        assert targets == expected_targets.get(state["name"], set()), (state["name"], targets)
        if state["name"] in ("LwStart", "LwStartAir"):
            assert state["counter"]["target"] == "geno:%d" % next(i for i, s in enumerate(doc["states"])
                if s["name"] == ("LwAttackAir" if state["name"] == "LwStartAir" else "LwAttack"))


def main():
    dump = json.load(open(ACMD, encoding="utf-8"))
    magic_count = len(json.load(open(MAGIC, encoding="utf-8"))["fighters"][0]["states"])
    for host in ("marth", "kirby"):
        default_dest, default_doc, _ = generate(host, options=())
        dest, doc, clips = generate(host)
        assert [s["name"] for s in doc["states"]] == sp.STATES
        assert len(doc["states"]) == 17
        assert [s["subaction"] for s in doc["states"]] == [sp.HOSTS[host][n] for n in sp.STATES]
        check_sonic(dest, doc, default_dest, default_doc, dump)
        check_counter(dest, doc, clips)
        check_rebound(dest, doc)
        magic_dest, magic_doc, _ = generate(host, magic=True)
        assert [s["name"] for s in magic_doc["states"][magic_count:]] == sp.STATES
        for name, back_name in (("LwAttack", "LwAttackBack"), ("LwAttackAir", "LwAttackBackAir")):
            chg = [e for e in events_for(magic_dest, magic_doc, name) if e["sub"] == 0x30
                   and e["words"][1] >> 28 == 2]
            assert sp.GENO(magic_count + sp.STATES.index(back_name)) in [e["words"][1] for e in chg]
        print("%s: Sonic branches, backward lunge, rebound, and +%d magic offset passed" % (host, magic_count))


if __name__ == "__main__":
    main()
