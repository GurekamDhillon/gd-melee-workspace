"""Exact ftcmd assembler/disassembler. See README.md for the text grammar."""
import argparse
import importlib
import json
import math
from pathlib import Path
import re
import shlex
import struct
import sys
from .source import ROOT, constants, symbols, command_lengths, command_names, command_fields

C = constants()
S = symbols()
LENGTHS = command_lengths()
SUBS = {k.removeprefix("GENO_SUB_"): v for k, v in C.items() if k.startswith("GENO_SUB_")}
VALUES = {k.removeprefix("GENO_VAL_"): v for k, v in C.items() if k.startswith("GENO_VAL_") and k != "GENO_VAL_COUNT"}
for prefix, start, end in (("MOVE_F", 0x20, 8), ("MOVE_I", 0x28, 8), ("CMD_VAR", 0x17, 4)):
    VALUES.update({prefix + str(i): start+i for i in range(end)})
CONDS = {k.removeprefix("GENO_COND_"): v for k, v in C.items() if k.startswith("GENO_COND_") and k != "GENO_COND_COUNT"}
CMPS = {k.removeprefix("GENO_CMP_"): v for k, v in C.items() if k.startswith("GENO_CMP_")}
INT_VALUES = {"AIR", "ACTION_FRAME", "MOTION", "JUMPS_USED", "JUMPS_MAX", "BUTTONS_HELD", "BUTTONS_PRESSED", "FAST_FALL", "GENO_STATE", "LEDGE", "HIDDEN", "HIT_PORT", "HIT_COUNTER", "HIT_COUNT", "ARTICLES", "ATTACK_CONNECTED", "ATTACK_CONNECTED_PREV"} | {f"MOVE_I{i}" for i in range(8)} | {f"CMD_VAR{i}" for i in range(4)}
WRITABLE = {"AIR", "FACING", "VEL_X", "VEL_Y", "GROUND_VEL", "FWD_VEL", "JUMPS_USED", "ANIM_RATE", "LEDGE", "HIDDEN", "MOTION_GRAVITY", "ATTACK_CONNECTED", "FALL_LIMIT"} | {f"MOVE_F{i}" for i in range(8)} | {f"MOVE_I{i}" for i in range(8)} | {f"CMD_VAR{i}" for i in range(4)}
NAMES = command_names()
FIELDS = command_fields()
OPS = {name.lower(): i for i, name in enumerate(NAMES)}
OPS.update(frame=2, endloop=4, subroutine=5, clear_hitbox=15,
           clear_hitboxes=16, sound=17, throw_hitbox=34)


def encoder():
    # The existing translator uses sibling absolute imports; no source refactor needed.
    path = str(ROOT / "ports/ir/tools")
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module("acmd_to_ftcmd")


def word(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a script word")
    n = int(value, 0) if isinstance(value, str) else value
    if not isinstance(n, int) or not -2147483648 <= n <= 0xFFFFFFFF:
        raise ValueError(f"word {value!r} outside signed/unsigned 32-bit range")
    return n & 0xFFFFFFFF


def integer(value, low=0, high=0xFFFFFFFF):
    n = int(value, 0) if isinstance(value, str) else value
    if not isinstance(n, int) or isinstance(n, bool) or not low <= n <= high:
        raise ValueError(f"integer {value!r} outside {low}..{high}")
    return n


def fbits(value):
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("float must be finite")
    return struct.unpack(">I", struct.pack(">f", v))[0]


def var(token):
    m = re.fullmatch(r"(la_i|ra_i|la_f|ra_f):(\d+)", token.lower())
    if not m:
        raise ValueError(f"unknown variable {token!r}; use la_i:0, ra_i:0, la_f:0, ra_f:0")
    return ["la_i", "ra_i", "la_f", "ra_f"].index(m[1]) * 64 + integer(m[2], 0, 63)


def var_text(n):
    return ["la_i", "ra_i", "la_f", "ra_f"][(n & 255) >> 6] + ":" + str(n & 63)


def value_id(token):
    name = token.upper()
    if name in VALUES and name not in ("SPECIAL_F", "SPECIAL_I"):
        return VALUES[name]
    m = re.fullmatch(r"SPECIAL_([FI]):(\d+)", name)
    if m:
        return (0x1000 if m[1] == "F" else 0x2000) + integer(m[2], 0, C["GENO_SPECIAL_WORDS"]-1)
    raise ValueError(f"unknown engine value {token!r}")


def value_text(id_):
    for key, value in VALUES.items():
        if value == id_:
            return key + ":0" if key in ("SPECIAL_F", "SPECIAL_I") else key
    for prefix, base in (("SPECIAL_F", 0x1000), ("SPECIAL_I", 0x2000)):
        if base <= id_ < base + C["GENO_SPECIAL_WORDS"]:
            return prefix + ":" + str(id_ - base)
    raise ValueError(f"unknown engine value id {id_}")


def is_float_value(token):
    return token.upper() not in INT_VALUES and not token.upper().startswith("SPECIAL_I:")


def operand(token, floating=False):
    if re.match(r"^(la|ra)_[if]:", token, re.I):
        return var(token), 0x80
    if token.startswith("bits:"):
        return word(token[5:]), 0
    masks = {k.removeprefix("GENO_BTN_"): v for k, v in C.items() if k.startswith("GENO_BTN_")}
    masks.update({k.removeprefix("GENO_HBF_"): v for k, v in C.items() if k.startswith("GENO_HBF_")})
    masks.update({k.removeprefix("GENO_LINK_"): v for k, v in C.items() if k.startswith("GENO_LINK_")})
    if not floating and all(p.upper() in masks for p in token.split("|")):
        n = 0
        for p in token.split("|"):
            n |= masks[p.upper()]
        return n, 0
    return (fbits(token) if floating else word(token)), 0


def operand_text(n, flag, floating=False):
    if flag and n <= 255:
        return var_text(n)
    if flag:
        raise ValueError("noncanonical variable word")
    if floating:
        f = struct.unpack(">f", struct.pack(">I", n))[0]
        return repr(f) if math.isfinite(f) else f"bits:0x{n:08X}"
    return str(n if n < 0x80000000 else n - 0x100000000)


def target_word(token, states=()):
    names = {"auto": 0xFFFFFFFE, "helpless": 0xFFFFFFFD, "stay": 0xFFFFFFFC}
    if token.lower() in names:
        return names[token.lower()]
    parts = token.split("|")
    m = re.fullmatch(r"(motion|special|geno):(.+)", parts[0], re.I)
    if not m:
        return integer(token, 0, 65535)
    if m[1].lower() == "geno" and not re.fullmatch(r"(?:0x[\da-fA-F]+|\d+)", m[2]):
        matches = [i for i, s in enumerate(states) if s.lower() == m[2].lower()]
        if len(matches) != 1:
            raise ValueError(f"unresolved state {m[2]!r}")
        id_ = matches[0]
    else:
        id_ = integer(m[2], 0, 65535)
    n = ["motion", "special", "geno"].index(m[1].lower()) << 28 | id_
    for flag in parts[1:]:
        if flag.upper() not in ("RAW", "KEEP_FRAME"):
            raise ValueError(f"unknown target flag {flag}")
        n |= C["GENO_TGT_" + flag.upper()]
    return n


def target_text(n):
    names = {0xFFFFFFFE: "auto", 0xFFFFFFFD: "helpless", 0xFFFFFFFC: "stay"}
    if n in names:
        return names[n]
    if n & 0x03FF0000 or n >> 28 > 2:
        raise ValueError("noncanonical target")
    return ["motion", "special", "geno"][n >> 28] + ":" + str(n & 65535) + ("|RAW" if n & 0x08000000 else "") + ("|KEEP_FRAME" if n & 0x04000000 else "")


def escape(sub, payload=(), low=0):
    return [(59 << 26) | (SUBS[sub] << 20) | ((len(payload)+1) << 16) | low, *payload]


def condition(args):
    name = args[0].upper()
    if name not in CONDS:
        raise ValueError(f"unknown condition {name}")
    low = CONDS[name] << 8
    tail = args[1:]
    while tail and tail[-1].upper() in ("NOT", "ONCE"):
        low |= C["GENO_CHG_" + tail.pop().upper()]
    if name in ("ALWAYS", "ANIM_END", "GROUND", "AIR"):
        if tail:
            raise ValueError("condition takes no arguments")
        return low, []
    if name in ("PRESSED", "HELD", "FRAME"):
        if len(tail) != 1:
            raise ValueError("condition needs one argument")
        return low, [operand(tail[0])[0]]
    if name == "BIT":
        if len(tail) != 2:
            raise ValueError("BIT needs variable and bit index")
        return low, [var(tail[0]), integer(tail[1], 0, 31)]
    if len(tail) != 3 or tail[1].upper() not in CMPS:
        raise ValueError("condition needs A CMP B")
    a = var(tail[0]) if name == "VAR" else value_id(tail[0])
    floating = a >= 128 if name == "VAR" else is_float_value(tail[0])
    b, flag = operand(tail[2], floating)
    return low | flag | CMPS[tail[1].upper()] << 4, [a, b]


def assemble_line(tokens, states=()):
    name, *args = tokens
    lower, upper = name.lower(), name.upper()
    is_geno = upper in SUBS and (name == upper or lower not in OPS)
    if args and args[0].startswith("raw="):
        if len(args) != 1:
            raise ValueError("raw form needs one comma-separated word list")
        words = [word(v) for v in args[0][4:].split(",")]
        if not is_geno and lower in OPS and words[0] >> 26 != OPS[lower]:
            raise ValueError("raw opcode does not match name")
        if is_geno and (words[0] >> 26 != 59 or (words[0] >> 20) & 63 != SUBS[upper]):
            raise ValueError("raw sub-command does not match name")
        if lower not in OPS and upper not in SUBS:
            raise ValueError(f"unknown command {name}")
        if len(list(commands(words))) != 1:
            raise ValueError("raw form must contain exactly one command")
        return words
    if lower == "hitbox":
        defaults = dict(slot=0, joint=0, damage=8, size=4, x=0, y=0, z=0, angle=361, kbg=100, fkb=0, bkb=0, element=0, shield=0, ground=1, air=1)
        for token in args:
            key, value = token.split("=", 1)
            if key not in defaults:
                raise ValueError(f"unknown hitbox field {key}")
            defaults[key] = float(value) if key in ("damage", "size", "x", "y", "z") else int(value, 0)
        limits = {"slot": (0, 3), "joint": (0, 255), "damage": (0, 1023), "size": (0, 65535/256), "angle": (0, 511), "kbg": (0, 511), "fkb": (0, 511), "bkb": (0, 511), "element": (0, 31), "shield": (-128, 127), "ground": (0, 1), "air": (0, 1)}
        limits.update({k: (-128, 32767/256) for k in "xyz"})
        for key, (lo, hi) in limits.items():
            if not math.isfinite(defaults[key]) or not lo <= defaults[key] <= hi:
                raise ValueError(f"hitbox {key} outside {lo}..{hi}")
        p = defaults
        return encoder().hitbox_words(p["slot"], p["joint"], p["damage"], p["size"], p["x"], p["y"], p["z"], p["angle"], p["kbg"], p["fkb"], p["bkb"], p["element"], p["shield"], bool(p["ground"]), bool(p["air"]))
    if lower in OPS and not is_geno:
        op = OPS[lower]
        if args and all("=" in arg for arg in args):
            fields = {key: (wi, shift, width, signed) for key, wi, shift, width, signed in FIELDS.get(op, [])}
            aliases = {}
            for key in fields:
                short = key.split(".")[1]
                aliases[short] = key if short not in aliases else None
            if not fields:
                raise ValueError("no named fields for this command; use positional payload or raw form")
            words = [op << 26] + [0] * (LENGTHS[op]-1)
            seen = set()
            for token in args:
                key, v = token.split("=", 1)
                key = key if key in fields else aliases.get(key)
                if key not in fields or key in seen:
                    raise ValueError(f"unknown, ambiguous, or repeated field {token.split('=')[0]}")
                seen.add(key)
                wi, shift, width, signed = fields[key]
                n = integer(v, -(1 << (width-1)) if signed else 0, (1 << (width-1))-1 if signed else (1 << width)-1)
                words[wi] |= (n & ((1 << width)-1)) << shift
            return words
        if len(args) != LENGTHS[op]:
            if not args and LENGTHS[op] == 1:
                args = ["0"]
            else:
                raise ValueError(f"{name} needs {LENGTHS[op]} arguments: low26 payload, then {LENGTHS[op]-1} words")
        return [(op << 26) | integer(args[0], 0, (1 << 26)-1), *[word(a) for a in args[1:]]]
    if upper not in SUBS:
        raise ValueError(f"unknown command {name}")
    if upper in ("NOP", "ORIG", "CHGCLR"):
        if args:
            raise ValueError(f"{name} takes no arguments")
        return escape(upper)
    if upper == "SKIP":
        return escape(upper, [integer(args[0], 0, 65536)]) if len(args) == 1 else _bad("SKIP needs a word count")
    if upper == "CALL":
        if len(args) not in (1, 2) or args[0] not in S["hooks"]:
            raise ValueError("CALL needs a known hook and optional integer argument")
        return escape(upper, [S["hooks"][args[0]], word(args[1]) if len(args) == 2 else 0])
    if upper in ("CHG", "CHGAND"):
        if upper == "CHG":
            target = target_word(args.pop(0), states)
        low, payload = condition(args)
        return escape(upper, ([target] if upper == "CHG" else []) + payload, low)
    if upper in ("REHIT", "LINK", "HBDMG", "HBSTUN", "HBFLAGS"):
        if len(args) != 2:
            raise ValueError(f"{name} needs hitbox mask and operand")
        mask = integer(args[0], 0, 15)
        b, flag = operand(args[1], upper == "HBDMG")
        if flag and upper in ("REHIT", "LINK"):
            raise ValueError(f"{name} cannot use a variable")
        return escape(upper, [b], mask << 8 | flag)
    if upper == "GET":
        if len(args) != 2:
            raise ValueError("GET needs variable and value")
        return escape(upper, [value_id(args[1])], var(args[0]) << 8)
    if upper in ("PUT", "IFV"):
        if len(args) != (2 if upper == "PUT" else 4):
            raise ValueError(f"{name} needs value {'operand' if upper == 'PUT' else 'CMP operand skip_words'}")
        id_ = value_id(args[0])
        if upper == "PUT" and args[0].upper() not in WRITABLE:
            raise ValueError(f"engine value {args[0]} is read-only")
        b, flag = operand(args[1] if upper == "PUT" else args[2], is_float_value(args[0]))
        return escape(upper, [id_, b] + ([integer(args[3], 0, 65536)] if upper == "IFV" else []), flag | (CMPS[args[1].upper()] << 4 if upper == "IFV" else 0))
    if len(args) != (4 if upper == "IF" else 2):
        raise ValueError(f"{name} needs variable {'CMP operand skip_words' if upper == 'IF' else 'operand'}")
    a = var(args[0])
    if upper in ("SETBIT", "CLRBIT") and a >= 128:
        raise ValueError("bit operations need an int variable")
    b, flag = operand(args[2] if upper == "IF" else args[1], a >= 128)
    return escape(upper, [b] + ([integer(args[3], 0, 65536)] if upper == "IF" else []), a << 8 | flag | (CMPS[args[1].upper()] << 4 if upper == "IF" else 0))


def _bad(message):
    raise ValueError(message)


def assemble(text, states=()):
    out = []
    for line, source in enumerate(text.splitlines(), 1):
        try:
            tokens = shlex.split(source, comments=True)
            if not tokens:
                continue
            out.extend(assemble_line(tokens, states))
        except (ValueError, KeyError, IndexError, OverflowError) as error:
            raise ValueError(f"line {line}: {error}") from None
    return out


def commands(words):
    words = [word(w) for w in words]
    offset = 0
    while offset < len(words):
        w0 = words[offset]
        op = w0 >> 26
        if op > 59:
            raise ValueError(f"word {offset}: opcode {op} is outside the engine table")
        n = max(1, w0 >> 16 & 15) if op == 59 else LENGTHS[op]
        if offset + n > len(words):
            raise ValueError(f"word {offset}: truncated command; needs {n} words")
        yield offset, words[offset:offset+n]
        offset += n


def friendly(ws):
    w0 = ws[0]
    op = w0 >> 26
    if op != 59:
        if op == 11:
            _, w1, w2, w3, w4 = ws
            signed = lambda n: (n if n < 32768 else n-65536) / 256
            return (f"hitbox slot={w0 >> 23 & 7} joint={w0 >> 11 & 255} damage={w0 & 1023} size={(w1 >> 16)/256} "
                    f"x={signed(w1 & 65535)} y={signed(w2 >> 16)} z={signed(w2 & 65535)} angle={w3 >> 23} kbg={w3 >> 14 & 511} fkb={w3 >> 5 & 511} bkb={w4 >> 23} element={w4 >> 18 & 31} shield={(w4 >> 10 & 255) if (w4 >> 10 & 255)<128 else (w4 >> 10 & 255)-256} ground={w4 >> 1 & 1} air={w4 & 1}")
        if op in FIELDS and op not in (0, 1, 2, 3):
            args = []
            for key, wi, shift, width, signed in FIELDS[op]:
                n = ws[wi] >> shift & ((1 << width)-1)
                if signed and n >= 1 << (width-1):
                    n -= 1 << width
                args.append(f"{key}={n}")
            return NAMES[op] + " " + " ".join(args)
        return NAMES[op] + (" " + " ".join([str(w0 & 0x3FFFFFF), *[f"0x{w:08X}" for w in ws[1:]]]) if w0 & 0x3FFFFFF or len(ws) > 1 or op in (1, 2, 3) else "")
    name = next((k for k, v in SUBS.items() if v == (w0 >> 20 & 63)), None)
    if name is None:
        raise ValueError("unknown Geno sub-command")
    a, flag, cmp = w0 >> 8 & 255, w0 & 128, next(k for k, v in CMPS.items() if v == (w0 >> 4 & 7))
    if name in ("NOP", "ORIG", "CHGCLR"):
        return name
    if name == "CALL":
        hook = next(k for k, v in S["hooks"].items() if v == ws[1])
        return f"CALL {hook} {operand_text(ws[2], 0)}"
    if name == "SKIP":
        return f"SKIP {ws[1]}"
    if name in ("GET", "PUT", "IFV"):
        value = value_text(ws[1])
        if name == "GET":
            return f"GET {var_text(a)} {value}"
        b = operand_text(ws[2], flag, is_float_value(value))
        return f"PUT {value} {b}" if name == "PUT" else f"IFV {value} {cmp} {b} {ws[3]}"
    if name in ("REHIT", "LINK", "HBDMG", "HBSTUN", "HBFLAGS"):
        return f"{name} {a} {operand_text(ws[1], flag, name == 'HBDMG')}"
    if name in ("CHG", "CHGAND"):
        cond = next(k for k, v in CONDS.items() if v == a)
        p = ws[2:] if name == "CHG" else ws[1:]
        args = []
        if cond in ("PRESSED", "HELD", "FRAME"):
            args = [operand_text(p[0], 0)]
        elif cond == "BIT":
            args = [var_text(p[0]), str(p[1])]
        elif cond in ("VAR", "VALUE"):
            arg = var_text(p[0]) if cond == "VAR" else value_text(p[0])
            args = [arg, cmp, operand_text(p[1], flag, p[0] >= 128 if cond == "VAR" else is_float_value(arg))]
        return " ".join([name, *([target_text(ws[1])] if name == "CHG" else []), cond, *args,
                         *(["NOT"] if w0 & 8 else []), *(["ONCE"] if w0 & 4 else [])])
    b = operand_text(ws[1], flag, a >= 128)
    return f"{name} {var_text(a)} {cmp} {b} {ws[2]}" if name == "IF" else f"{name} {var_text(a)} {b}"


def disassemble(words):
    lines = []
    for offset, ws in commands(words):
        op = ws[0] >> 26
        name = NAMES[op] if op < 59 else next((k for k, v in SUBS.items() if v == (ws[0] >> 20 & 63)), None)
        if name is None:
            raise ValueError(f"word {offset}: unknown Geno sub-command {(ws[0] >> 20) & 63}")
        try:
            line = friendly(ws)
            if assemble(line) != ws:
                raise ValueError("noncanonical bits")
        except (ValueError, IndexError, KeyError, StopIteration, OverflowError):
            line = name + " raw=" + ",".join(f"0x{w:08X}" for w in ws)
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def read_words(text):
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [word(w) for w in data]
    except json.JSONDecodeError:
        pass
    out = []
    for line, source in enumerate(text.splitlines(), 1):
        for token in source.split("#", 1)[0].replace(",", " ").split():
            try:
                out.append(word(token))
            except ValueError as error:
                raise ValueError(f"line {line}: {error}") from None
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["asm", "disasm"])
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--words", action="store_true", help="asm: whitespace hex instead of a JSON array")
    args = ap.parse_args()
    try:
        text = args.input.read_text(encoding="utf-8-sig")
        if args.mode == "asm":
            words = assemble(text)
            result = "\n".join(f"0x{w:08X}" for w in words) + "\n" if args.words else json.dumps(words) + "\n"
        else:
            result = disassemble(read_words(text))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result, encoding="utf-8")
        else:
            print(result, end="")
        return 0
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
