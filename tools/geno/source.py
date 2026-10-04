"""Read the local engine contract, never a disc or generated fighter asset."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / "melee"


def read(relative):
    return (GAME / relative).read_text(encoding="utf-8")


def uncomment(text):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def constants():
    text = uncomment(read("pc/geno/geno.h"))
    out = {}
    for name, value in re.findall(r"\b(GENO_\w+)\s*=\s*(0x[\da-fA-F]+|\d+)", text):
        out[name] = int(value, 0)
    for name, value in re.findall(r"^#define\s+(GENO_\w+)\s+(0x[\da-fA-F]+|\d+)\b", text, re.M):
        out[name] = int(value, 0)
    return out


def table(text, name):
    match = re.search(r"\b" + re.escape(name) + r"\s*\[[^]]*\]\s*=\s*\{(.*?)\n\};", text, re.S)
    if not match:
        raise ValueError(f"engine table {name} missing; update source extractor")
    return match.group(1)


def symbols():
    c = constants()
    game = read("pc/geno/geno_game.c")
    v2 = read("pc/geno/geno_game_v2.inc")
    hooks = {name: c[id_] for id_, name in re.findall(r'\{\s*(GENO_HOOK_\w+),\s*"([^"]+)"', table(game, "geno_hooks"))}
    attrs = dict((name, bool(int(kind))) for name, kind in
                 re.findall(r"GENO_ATTR\((\w+),\s*([01])\)", table(game, "geno_attrs")))
    behaviors = re.findall(r'\{\s*GENO_BHV_\w+,\s*"([^"]+)"', table(v2, "geno_bhvs"))
    callbacks = {slot.lower(): ["like"] for slot in ("ANIM", "IASA", "PHYS", "COLL")}
    for slot, name in re.findall(r'GENO_CB_(ANIM|IASA|PHYS|COLL),\s*"([^"]+)"', table(v2, "geno_cbs")):
        callbacks[slot.lower()].append(name)
    params = {family: {} for family in ("glide", "tornado", "drill", "cape")}
    for family, name, expr, default in re.findall(
            r'\{\s*"(\w+)",\s*"([^"]+)",\s*(GENO_P_\w+(?:\s*\+\s*\d+)?),\s*(.*?)\}',
            uncomment(table(v2, "geno_params")), re.S):
        value = default.strip().replace("(f32)", "")
        value = re.sub(r"(?<=\d)f\b", "", value)
        for key in sorted(c, key=len, reverse=True):
            value = re.sub(r"\b" + key + r"\b", str(c[key]), value)
        if not re.fullmatch(r"[\d.()|+\-\s]+", value):
            raise ValueError(f"unparsed parameter default {default}")
        params[family][name] = eval(value, {"__builtins__": {}})
    for family, end in (("glide", 21), ("tornado", 19), ("drill", 5), ("cape", 5)):
        rows = list(params[family].items())
        for i in range(end + 1):
            params[family].setdefault(f"w{i:02}", rows[i][1])
    vanilla = {}
    for code, name, alias in re.findall(r'\{\s*"(\w+)",\s*"(\w+)",\s*(NULL|"\w+")\s*\}',
                                       table(read("pc/platform/geno_registry.c"), "gn_vanilla")):
        vanilla[name] = "Pl" + code + ".dat"
        if alias != "NULL":
            vanilla[alias.strip('"')] = "Pl" + code + ".dat"
    return dict(hooks=hooks, attrs=attrs, behaviors=behaviors, callbacks=callbacks,
                params=params, vanilla=vanilla)


def command_lengths():
    raw = table(read("src/melee/ft/ftaction.c"), "ftAction_803C0870")
    return [1, 1, 1, 1, 1, 2, 1, 2, 1, 1] + [int(v) for v in re.findall(r"\d+", raw)]


def command_names():
    return re.findall(r'"([^"]+)"', table(read("pc/platform/gw_script.c"), "gs_cmd_names"))[:59]


def command_fields():
    """Extract named bitfields from the decomp's CmdUnion structs.

    Multiword command families are mapped to the command table, not to unverified
    external command lists. Unknown fields retain the decomp's own names.
    """
    text = uncomment(read("src/melee/lb/types.h"))
    structs = {name: body for name, body in re.findall(r"struct (\w+)\s*\{(.*?)\};", text, re.S)}
    union = re.search(r"union CmdUnion\s*\{(.*?)\};", text, re.S)[1]
    members = {member: struct for struct, member in re.findall(r"struct (\w+) (\w+)\s*;", union)}
    ft = uncomment(read("src/melee/ft/ftaction.c"))
    functions = re.findall(r"ftAction_\w+", table(ft, "ftAction_803C06E8"))
    # Each entry's structure order is the actual command word order.
    multi = {10: [f"spawn_gfx_{i}" for i in range(5)],
             11: [f"spawn_hitbox_{i}" for i in range(5)],
             17: [f"sound_effect_{i}" for i in range(3)],
             34: [f"set_throw_hitbox_{i}" for i in range(3)],
             38: ["pseudo_random_sfx_0", "pseudo_random_sfx_1", "raw"],
             39: [f"stage_sfx_{i}" for i in range(4)] + ["raw"] * 3,
             40: ["set_tex_anim"], 54: ["footstep_fx_0", "sound_effect_1", "sound_effect_2"],
             55: ["unk_fx_0", "sound_effect_1", "sound_effect_2"],
             56: ["smash_charge_0", "smash_charge_1"], 58: [f"wind_fx_{i}" for i in range(4)]}
    result = {}
    for op in range(59):
        if op in multi:
            names = multi[op]
        elif op < 10:
            names = {0: ["Command_00"], 1: ["Command_00"], 2: ["Command_02"], 3: ["Command_03"], 9: ["Command_09"]}.get(op, [])
        else:
            body = re.search(r"void " + functions[op-10] + r"\([^;]*?\)\s*\{(.*?)\n\}", ft, re.S)
            used = re.findall(r"cmd->u->(\w+)\.", body[1]) if body else []
            names = [members[used[0]]] if used else []
        fields = []
        for wi, name in enumerate(names):
            shift = 32
            rows = re.findall(r"([us]\d+)\s+(\w+)\s*(?::\s*(\d+))?\s*;", structs.get(name, ""))
            for typ, field, width in rows:
                width = int(width) if width else int(typ[1:])
                shift -= width
                if shift < 0:
                    raise ValueError(f"struct {name} crosses command word; update extractor")
                if wi == 0 and shift == 26 and width == 6:
                    continue  # opcode
                fields.append((f"w{wi}.{field}", wi, shift, width, typ.startswith("s")))
        if fields:
            result[op] = fields
    return result
