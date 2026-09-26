#!/usr/bin/env python3
"""acmd_parse.py - an Ultimate fighter's move scripts (ACMD), from our own Ghidra dump, as timelines.

    python ports/ir/tools/acmd_parse.py <fighter> <dump dir> [-o out.json]

<dump dir> is what ports/ir/tools/acmd/DumpAcmd.java wrote from lua2cpp_<fighter>.nro: one
decompiled C file per registered script, named by Hash40 (agent hash __ script hash), and
index.tsv. Nothing here reads a third-party dump.

Step 1, names: a Hash40 is CRC32(name) with len(name) in the top byte. Agent names are tried from
the fighter's motion folders (the fighter itself and its weapons/articles: trail, trail_fire...);
script names as <kind>_<action> over the fighter's own clip names (the letter-digit-digit prefix
stripped) and the upstream motion-label list in the Ultimate toolkit. Unresolved hashes are kept.
"""
import argparse
import csv
import json
import os
import re
import sys
import zlib
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from convert_ultimate_anim import FIGHTERS, TOOL  # noqa: E402

KINDS = ("game", "effect", "sound", "expression")


def hash40(name):
    return (len(name) << 32) | zlib.crc32(name.encode())


def name_tables(fighter):
    motion = os.path.join(FIGHTERS, fighter, "motion")
    agents = [fighter] + [f"{fighter}_{d}" for d in os.listdir(motion) if d != "body"]
    actions = set()
    for root, _, files in os.walk(motion):
        for f in files:
            if f.endswith(".nuanmb"):
                actions.add(re.sub(r"^[a-z]\d\d", "", f[:-7]))
                actions.add(f[:-7])
    labels = os.path.join(TOOL, "references", "motion-labels.txt")
    if os.path.exists(labels):
        for line in open(labels, encoding="utf-8", errors="replace"):
            n = line.strip().rsplit(".", 1)[0]
            if n:
                actions.add(re.sub(r"^[a-z]\d\d", "", n)); actions.add(n)
    # variants: Ultimate script names follow motion KINDS, which differ from clip names by a
    # trailing letter or number (clip attacks4s -> script attacks4) or a start/loop/end part
    more = set()
    for a in actions:
        more.add(a[:-1]); more.add(a[:-2])
        for suf in ("1", "2", "3", "s", "hi", "lw", "start", "loop", "end", "_l", "_r", "l", "r", "air"):
            more.add(a + suf)
    actions |= {m for m in more if m}
    scripts = {}
    for a in actions:
        for k in KINDS:
            n = f"{k}_{a}"
            scripts.setdefault(hash40(n), n)
    return {hash40(a): a for a in agents}, scripts


# ------------------------------------------------------------------ step 2: bodies -> timelines
# Ultimate's ATTACK argument order. When the capsule has no second point, x2/y2/z2 are left out of
# the decompiled call (33 values instead of 36).
ATTACK_ARGS = ["id", "part", "bone", "damage", "angle", "kbg", "fkb", "bkb", "size", "x", "y", "z",
               "x2", "y2", "z2", "hitlag", "sdi", "setoff_kind", "lr_check", "set_weight",
               "shield_damage", "trip", "rehit", "reflectable", "absorbable", "flinchless",
               "disable_hitlag", "direct", "ground_air", "hitbits", "collision_part",
               "friendly_fire", "effect", "sound_level", "sound_attr", "region"]
CTOR = re.compile(r"lib::L2CValue::L2CValue\(\w+,(.+)\);\s*$")
ASSIGN = re.compile(r"^\s*(\w+)\s*=\s*(.+);\s*$")
CALL = re.compile(r"app::sv_animcmd::(\w+)\(")
MODULE_CALL = re.compile(r"app::(\w+Module)::(\w+)\(")


class Nro:
    """Constants the decompiler leaves as addresses: NRO file offsets are memory offsets from
    the module base 0x7100000000 (checked: Sora's jab reads 2.8 and 0.3 there)."""
    BASE = 0x7100000000

    def __init__(self, path):
        self.data = open(path, "rb").read()

    def f32(self, addr):
        import struct
        return struct.unpack_from("<f", self.data, addr - self.BASE)[0]


def value(tok, env, nro, hashes):
    tok = tok.strip()
    if tok in env:
        return env[tok]
    if tok in ("true", "false"):
        return tok == "true"
    m = re.fullmatch(r"_UNK_([0-9a-f]+)|DAT_([0-9a-f]+)", tok)
    if m:
        return round(nro.f32(int(m.group(1) or m.group(2), 16)), 6)
    m = re.fullmatch(r"\*\(int \*\)\((?:\w+) \+ (0x[0-9a-f]+)\)|\*\(int \*\)\(PTR_const_value_table_+\w* \+ (0x[0-9a-f]+)\)", tok)
    if m:
        return {"const": m.group(1) or m.group(2)}
    m = re.fullmatch(r"-?0x[0-9a-f]+|-?\d+", tok)
    if m:
        v = int(tok, 0)
        if v > 0xFFFFFFFF:                      # a Hash40 (length byte on top)
            return hashes.get(v, hex(v))
        return v
    try:
        return float(tok)
    except ValueError:
        return tok


HELPER_CALL = re.compile(r"(?:func_0x0*|FUN_)([0-9a-f]{8,})\(param_2,(.*)\);", re.S)  # FUN_ once Ghidra defined it
PTR_CALL = re.compile(r"PTR_(\w+?)_[0-9a-f]{8,}\)")
CTOR_VAR = re.compile(r"lib::L2CValue::L2CValue\(\s*(?:\([^)]*\)\s*)?&?(\w+),(.+)\);\s*$")  # (L2CValue *)&uStack_60 too


def helper_names(dump):
    """ACMD macros are compiled as local helpers that push their arguments and call the engine
    through a named pointer (PTR_ATTACK_71005dcf28): the helper's name is that pointer's."""
    out = {}
    for f in os.listdir(os.path.join(dump, "helpers")):
        m = PTR_CALL.findall(open(os.path.join(dump, "helpers", f), encoding="utf-8").read())
        out[f[:-2]] = m[-1] if m else None
    return out


def statements(body):
    """Decompiled C split into statements (a call's argument list can span lines)."""
    buf = ""
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        buf = (buf + " " + s) if buf else s
        if buf.endswith((";", "{", "}")) or buf.startswith(("if", "else", "while", "do")):
            yield buf
            buf = ""


BIND = re.compile(r"app::lua_bind::(\w+?)_impl\((.*)")
COND = re.compile(r"^(?:\}\s*)?(?:else\s+)?if\s*\((.*)\)\s*\{$")


def parse_body(text, nro, hashes, helpers=None):
    """A script body as a timeline of commands. frame/wait carry the frame. A branch on the game's
    state (a work flag, a status...) is kept as such: each command carries the conditions it runs
    under ('when': [{test, holds}]), and an else restarts from the frame its if started at, so each
    path has its own timeline. The is_excute guards around every command block are transparent.
    Returns [{frame, cmd, args, when}]."""
    helpers = helpers or {}
    body = text.split("// BODY @", 1)[-1]
    env, pending, out, frame, var = {}, [], [], 0.0, {}
    guards, tests = set(), {}              # is_excute bool vars; bool var -> the test that set it
    stack = []                             # open blocks: {test, holds, start, transparent}
    last_bind = last_closed = last_test = None
    for line in statements(body):
        # ---- block structure ----------------------------------------------------------------
        m = re.match(r"^(\w+)\s*=\s*lib::L2CValue::operator_cast_to_bool", line)
        if m:
            guards.add(m.group(1))
        m = re.match(r"^(\w+)\s*=\s*app::lua_bind::(\w+?)_impl\s*\((.*)\);$", line)
        if m:
            arg = m.group(3).split(",", 1)[-1].strip().rstrip(")")
            shown = env.get(arg, arg)
            tests[m.group(1)] = f"{m.group(2).replace('__', '::')}({shown})"
            last_test = tests[m.group(1)]
        m = re.match(r"^(\w+)\s*=\s*lib::L2CValue::operator==", line)
        if m and last_test:                      # the result of the last engine test, compared
            tests[m.group(1)] = last_test
        cm = COND.match(line)
        if cm or line in ("else {", "} else {"):
            if line.startswith("}") and stack:
                closed = stack.pop()
            else:                                    # "}" came as its own statement just before
                closed = last_closed
            last_closed = None
            if cm:
                test = cm.group(1).strip()
                bare = re.sub(r"[()!\s]", "", test)
                transparent = bare in guards
                used = [v for v in re.findall(r"[a-z]Var\d+", test) if v in tests]
                label = tests[used[0]] + " : " + test if used else test
                stack.append({"test": label, "holds": not test.lstrip("(").startswith("!"),
                              "start": frame, "transparent": transparent})
            else:                                    # else: the other side of the branch just closed
                if closed is not None:
                    if not closed["transparent"]:
                        frame = closed["start"]
                    stack.append({"test": closed["test"], "holds": not closed["holds"],
                                  "start": closed["start"], "transparent": closed["transparent"]})
            continue
        if line == "}":
            last_closed = stack.pop() if stack else None
            continue
        last_closed = None
        when = [{"test": b["test"], "holds": b["holds"]} for b in stack if not b["transparent"]]

        m = HELPER_CALL.search(line)
        if m:
            name = helpers.get(m.group(1)) or ("helper_" + m.group(1))
            args = []
            for tok in m.group(2).split(","):
                tok = re.sub(r"^\([^)]*\)\s*", "", tok.strip()).lstrip("&")   # (L2CValue *)&uStack_60
                if tok.startswith("PTR_NIL") or (tok in env and env[tok] is None):
                    args.append(None)
                else:
                    args.append(var.get(tok, env.get(tok, tok)))
            out.append({"frame": frame, "cmd": name, "args": args, "when": when}); pending = []; continue
        m = CTOR_VAR.search(line)
        if m:
            v = value(m.group(2), env, nro, hashes)
            var[m.group(1)] = v
            pending.append(v); continue
        m = ASSIGN.match(line)
        if m and re.fullmatch(r"[fpi]Var\d+|puVar\d+", m.group(1)):
            env[m.group(1)] = value(m.group(2), env, nro, hashes)
            if isinstance(env[m.group(1)], str) and env[m.group(1)].startswith("PTR_NIL"):
                env[m.group(1)] = None                  # a variable holding nil (an absent argument)
            elif isinstance(env[m.group(1)], str) and env[m.group(1)].startswith("PTR_"):
                env[m.group(1)] = "table"
        m = CALL.search(line)
        if m:
            cmd = m.group(1)
            if cmd == "is_excute":
                continue
            args = pending; pending = []
            if cmd in ("frame", "wait") and args:
                v = args[-1]
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    frame = float(v) if cmd == "frame" else frame + float(v)
                    out.append({"frame": frame, "cmd": cmd, "args": [v], "when": when})
                else:                               # a frame from a parameter or constant: kept as is
                    out.append({"frame": frame, "cmd": cmd, "args": [v], "unresolved_frame": True, "when": when})
                continue
            out.append({"frame": frame, "cmd": cmd, "args": args, "when": when}); continue
        m = MODULE_CALL.search(line)
        if m and "L2CValue" not in line:
            out.append({"frame": frame, "cmd": f"{m.group(1)}::{m.group(2)}", "args": pending, "when": when}); pending = []
    for c in out:
        if c["cmd"] in ("ATTACK", "ATTACK_ABS") and len(c["args"]) in (33, 36):
            names = ATTACK_ARGS if len(c["args"]) == 36 else [n for n in ATTACK_ARGS if n not in ("x2", "y2", "z2")]
            c["named"] = dict(zip(names, c["args"]))
    return out


def motion_list(fighter):
    """The fighter's motion_list.bin (motion/body/c00), via upstream yamlist, keyed by the game
    script's Hash40 - the key the ACMD dump uses: cancel frame (Melee's IASA), intangibility
    window, blend frames, the clip it plays (Hash40 of the .nuanmb name) and its flags."""
    import shutil
    import subprocess
    import tempfile
    src = os.path.join(FIGHTERS, fighter, "motion", "body", "c00", "motion_list.bin")
    exe = os.path.join(TOOL, "apps", "yamlist", "yamlist.exe")
    clips = {}
    for f in os.listdir(os.path.dirname(src)):
        if f.endswith(".nuanmb"):
            clips[hash40(f)] = f[:-7]
    with tempfile.TemporaryDirectory() as tmp:     # yamlist rejects the workspace path
        b, y = os.path.join(tmp, "ml.bin"), os.path.join(tmp, "ml.yml")
        shutil.copy(src, b)
        subprocess.run([exe, "disasm", b, "-o", y], check=True, capture_output=True)
        text = open(y, encoding="utf-8").read()
    out = {}
    for blk in re.split(r'\n  "0x', text)[1:]:
        g = re.search(r'game_script: "(0x[0-9a-f]+)"', blk)
        if not g:
            continue
        num = lambda k: int(re.search(rf"{k}: (\d+)", blk).group(1)) if re.search(rf"{k}: (\d+)", blk) else None
        anim = re.search(r'- name: "(0x[0-9a-f]+)"', blk)
        out[int(g.group(1), 16)] = {
            "cancel_frame": num("cancel_frame"), "xlu_start": num("xlu_start"), "xlu_end": num("xlu_end"),
            "blend_frames": num("blend_frames"),
            "clip": clips.get(int(anim.group(1), 16)) if anim else None,
            "loop": "loop: true" in blk, "move": "move: true" in blk}
    return out


def load_index(dump):
    return list(csv.DictReader(open(os.path.join(dump, "index.tsv"), encoding="utf-8"), delimiter="\t"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fighter")
    ap.add_argument("dump")
    ap.add_argument("-o", "--out")
    ap.add_argument("--check-against", help="another dump's smashline-style scripts, to spot-check ours")
    a = ap.parse_args()
    agents, scripts = name_tables(a.fighter)
    rows = load_index(a.dump)
    res = Counter(); unresolved = Counter()
    for r in rows:
        ag = agents.get(int(r["agent_hash"], 16)); sc = scripts.get(int(r["script_hash"], 16))
        r["agent"] = ag or r["agent_hash"]; r["script"] = sc or r["script_hash"]
        res["agent " + ("ok" if ag else "unresolved")] += 1
        res["script " + ("ok" if sc else "unresolved")] += 1
        if not sc: unresolved[r["kind"]] += 1
    print(f"{len(rows)} scripts; {dict(res)}; unresolved scripts by kind {dict(unresolved)}")
    print("agents:", Counter(r["agent"] for r in rows).most_common())

    nro = Nro(os.path.join(TOOL, "workspace", "extracted", "prebuilt", "nro", "release", f"lua2cpp_{a.fighter}.nro"))
    hashes = dict(scripts)
    sk = os.path.join(HERE, "..", "..", "..", "_build", "tmp", "ir", f"{a.fighter}.ultimate-body.ir.json")
    if os.path.exists(sk):
        for j in json.load(open(sk, encoding="utf-8"))["assets"]["skeletons"][0]["joints"]:
            hashes[hash40(j["name"].lower())] = j["name"].lower()
    for n in ("top", "rot", "hip", "throw"):
        hashes[hash40(n)] = n
    effects = os.path.join(TOOL, "workspace", "extracted", "effect", "fighter", a.fighter)
    if os.path.isdir(effects):          # collision_attr_* and effect names seen in the effect folder
        for f in os.listdir(effects):
            hashes[hash40(os.path.splitext(f)[0])] = os.path.splitext(f)[0]
    for attr in ("normal", "cutup", "fire", "elec", "ice", "purple", "paralyze", "sleep", "bury", "stab",
                 "rush", "coin", "magic", "lay", "flower", "saving", "death", "turn", "search", "none",
                 "slip", "aura", "water", "curse", "sting", "cutup_metal", "punch", "kick", "normal_bullet"):
        hashes[hash40("collision_attr_" + attr)] = "collision_attr_" + attr
    helpers = helper_names(a.dump)
    for r in rows:
        path = os.path.join(a.dump, r["kind"], f"{r['agent_hash']}__{r['script_hash']}.c")
        r["commands"] = parse_body(open(path, encoding="utf-8").read(), nro, hashes, helpers)
    ml = motion_list(a.fighter)
    for r in rows:
        r["motion"] = ml.get(int(r["script_hash"], 16))
    print(f"motion list: {len(ml)} motions; {sum(1 for r in rows if r['motion'])} scripts joined to one")
    n_attack = sum(1 for r in rows for c in r["commands"] if c["cmd"] in ("ATTACK", "ATTACK_ABS"))
    print(f"parsed {len(rows)} scripts, {n_attack} ATTACK commands")
    if a.check_against:
        check_against(rows, a.check_against)
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)


REF_ATTACK = re.compile(r"macros::ATTACK\(agent, (.+)\);")
REF_FN = re.compile(r"fn ((?:game|effect|sound|expression)_\w+)\(")   # every fn: effect_ must end game_
REF_FRAME = re.compile(r"(frame|wait)\(agent\.lua_state_agent, ([\d.]+)\)")


def check_against(rows, ref_dir):
    """Compare each game script's ATTACK values (frame, id, bone, damage, angle, kbg, fkb, bkb, size,
    x, y, z) with another dump of the same module (smashline-style .txt files). A spot check of
    our extraction, not a source: a mismatch is reported, never copied."""
    ref = {}
    for root, _, files in os.walk(ref_dir):
        for f in files:
            if not f.endswith(".txt"):
                continue
            fn, frame = None, 0.0
            for line in open(os.path.join(root, f), encoding="utf-8", errors="replace"):
                m = REF_FN.search(line)
                if m:
                    fn, frame = m.group(1), 0.0
                    if fn.startswith("game_"): ref.setdefault(fn, [])
                    continue
                m = REF_FRAME.search(line)
                if m and fn:
                    frame = float(m.group(2)) if m.group(1) == "frame" else frame + float(m.group(2)); continue
                m = REF_ATTACK.search(line)
                if m and fn and fn.startswith("game_"):
                    p = [x.strip() for x in m.group(1).split(",")]
                    bone = re.search(r'"(\w+)"', p[2]).group(1)
                    ref[fn].append((frame, int(p[0]), bone, *[round(float(x), 2) for x in (p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11])]))
    ours = {}
    for r in rows:
        if r["kind"] != "game" or r["agent"] != r.get("agent") or not r["script"].startswith("game_"):
            continue
        if r["share"] or r["owner"] != "fighter":
            continue
        t = []
        for c in r["commands"]:
            n = c.get("named")
            if c["cmd"] == "ATTACK" and n and isinstance(n["id"], int):
                t.append((c["frame"], n["id"], n["bone"], *[round(float(n[k]), 2) for k in ("damage", "angle", "kbg", "fkb", "bkb", "size", "x", "y", "z")]))
        ours.setdefault(r["script"], t)
    same = diff = missing = 0; examples = []
    for fn, t in ours.items():
        if fn not in ref:
            missing += 1; continue
        if sorted(t) == sorted(ref[fn]):
            same += 1
        else:
            diff += 1
            if len(examples) < 5:
                examples.append((fn, sorted(set(t) ^ set(ref[fn]))[:3]))
    print(f"check: {same} scripts identical, {diff} differ, {missing} not in the reference")
    for e in examples:
        print("  differs:", e)


if __name__ == "__main__":
    sys.exit(main())
