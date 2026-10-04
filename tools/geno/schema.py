"""Generate editor schema and commented template from a reviewed engine contract."""
import argparse
import hashlib
import json
import re
from .source import ROOT, read, symbols, constants, uncomment

REGISTRY = "melee/pc/platform/geno_registry.c"
C = constants()
S = symbols()


def registry_text():
    return read("pc/platform/geno_registry.c") + "\n" + read("pc/platform/geno_define_registry.inc")


def registry_keys(text=None):
    text = uncomment(registry_text() if text is None else text)
    keys = set(re.findall(r'(?:jd_get|gn_num|gn_int|gn_vec)\([^;\n]*?"([a-z_]+)"', text))
    for name in ("fams", "cb_keys", "sp_keys", "ev_names", "despawn_keys", "hits_keys"):
        match = re.search(r"\b" + name + r"\[[^]]*\]\s*=\s*\{(.*?)\}", text, re.S)
        if not match:
            raise ValueError(f"missing registry key table {name}")
        keys.update(re.findall(r'"([a-z_]+)"', match.group(1)))
    return keys


def field(type_, description, default="unchanged / absent", section="7", **limits):
    return {"type": type_, "description": description,
            "x-engine-default": default, "x-reference": "geno.md §" + section,
            "x-source": REGISTRY, **limits}


def num(desc, default=0, section="19", **kw):
    return field("number", desc, default, section, **kw)


def integer(desc, default=0, section="19", **kw):
    return field("integer", desc, default, section, **kw)


def string(desc, default="", section="7", **kw):
    return field("string", desc, default, section, **kw)


def obj(props, required=(), **kw):
    return dict(type="object", properties=props, additionalProperties=False,
                **({"required": list(required)} if required else {}), **kw)


def arr(item, cap=None, **kw):
    return dict(type="array", items=item, **({"maxItems": cap} if cap is not None else {}), **kw)


def target(desc="Action target", **kw):
    return {"anyOf": [integer(desc, section="15.3", minimum=0, maximum=65535),
                      string(desc, section="15.3", pattern=r"^(auto|helpless|stay|[mM][oO][tT][iI][oO][nN]:.+|[sS][pP][eE][cC][iI][aA][lL]:.+|[gG][eE][nN][oO]:.+)$")], **kw}


def word():
    return {"anyOf": [{"type": "integer", "minimum": -2147483648, "maximum": 4294967295},
                      {"type": "string", "pattern": r"^(0[xX][0-9a-fA-F]+|[0-9]+)$"}]}


def build_schema():
    from .define import definition_schema
    boolean = field(["boolean", "number"], "Enable when nonzero", 0, "19")
    vector2 = arr(num("Coordinate"), 2)
    vector3 = arr(num("Coordinate"), 3)
    hit = obj({"damage": num("Damage percent", 1), "size": num("Hitbox radius", 3),
               "offset": vector3, "angle": integer("Launch angle", 361),
               "kbg": integer("Knockback growth", 100), "wkb": integer("Weight-set knockback"),
               "bkb": integer("Base knockback"), "element": integer("Hit element"),
               "shield_damage": integer("Shield damage"), "stun": integer("Extra hitstun", minimum=0, maximum=255),
               "sfx_severity": integer("Hit sound severity", 1), "sfx_kind": integer("Hit sound kind"),
               "start": integer("First active life frame", 1), "end": integer("Last active life frame; 0 = lifetime"),
               "slot": integer("Live hitbox slot", "entry index modulo 4", minimum=0, maximum=C["GENO_ART_HITBOXES"]-1),
               "hits": obj({k: dict(boolean, **{"x-engine-default": 1}) for k in ("ground", "air", "reflect", "absorb", "counter")})})
    article = obj({"name": string("Article name", section="19", maxLength=31),
                   "model": obj({"file": string("Model archive path", section="19", maxLength=63),
                                 "symbol": string("Model joint public symbol; absent uses first *_joint", section="19", maxLength=63)}, ("file",)),
                   "lifetime": num("Lifetime in logic frames", 60), "velocity": vector2,
                   "spawn": vector2, "scale": num("Model scale", 1), "spin": num("Model spin in degrees per frame"),
                   "max_live": integer("Live article limit", 4, minimum=1),
                   "homing": obj({k: num(k.replace("_", " ")) for k in ("turn", "range", "delay")}),
                   "despawn": obj({k: dict(boolean, **{"x-engine-default": 1}) for k in ("hit", "shield", "stage", "clank")}),
                   "spins": arr(obj({"joint": integer("Model joint index"), "z": num("Joint spin radians per frame")}), 4),
                   "bone": integer("Spawn joint; -1 = position", -1), "effect": integer("Melee effect id"),
                   "fx": string("Effect package name", section="20"),
                   "effects": arr({"anyOf": [integer("Melee effect id"), obj({"id": integer("Effect id"),
                            "frame": integer("Attach life frame", minimum=0, maximum=65535),
                            "joint": integer("Model joint", minimum=0, maximum=255),
                            "count": integer("Consecutive effect count", 1, minimum=1, maximum=256)})]}, 8),
                   "spawns": arr(vector2, C["GENO_ART_SPAWNS"]), "hitboxes": arr(hit, C["GENO_ART_HIT_ENTRIES"]),
                   "children": arr(obj({"article": {"anyOf": [integer("Article index", minimum=0, maximum=C["GENO_MAX_ARTICLES"]-1), string("Article name", section="19")]},
                            "frame": integer("First spawn frame", 1), "every": integer("Repeat interval; 0 = once"),
                            "count": integer("Spawn count", 1), "spawn": integer("Spawn variant", minimum=0, maximum=C["GENO_ART_SPAWNS"]-1)}, ("article",)), C["GENO_ART_CHILDREN"]),
                   **{k: num(k.replace("_", " ")) for k in ("gravity", "max_fall", "accel", "max_speed", "min_speed", "angle")}})
    state = obj({"name": string("State target name", section="16.1", maxLength=31),
                 "behavior": string("Callback bundle", section="16.2", enum=S["behaviors"]),
                 "subaction": {"anyOf": [integer("Animation row", -1, "16.1", minimum=0, maximum=1023),
                                         string("Use a motion's animation", section="16.1", pattern=r"^(motion|special):[0-9]+$")]},
                 "like": target("Copy motion flags, move id and camera callback"), "flags": word(),
                 "move_id": integer("Move id for staling", "from like / behavior", "16.1", minimum=0, maximum=255),
                 "next": target("Target on animation end"), "land": target("Target on landing"),
                 "landing_lag": num("Landing lag", 0, "16.1"),
                 "ledge": {"anyOf": [{"enum": ["none", "front", "both"]}, {"type": "integer", "minimum": 0, "maximum": 2}]},
                 "liftoff": dict(boolean, **{"x-engine-default": 1}), "origin": boolean,
                 "gravity": num("Root-motion gravity multiplier", 0, "17"),
                 "facing": string("Lock root-motion travel to entry facing", section="17", enum=["entry"]),
                 "counter": obj({"from": integer("First counter action frame", 1), "to": integer("Last counter action frame", 2147483647),
                                 "target": target("Target after a countered hit"), "negate": dict(boolean, **{"x-engine-default": 1})}),
                 **{slot: string("Override " + slot + " callback", "behavior callback", "16.2", enum=names) for slot, names in S["callbacks"].items()}})
    selector = obj({"select": string("Integer bank selector", section="19", pattern=r"^(la_i|ra_i):(?:[0-9]|[1-5][0-9]|6[0-3])$"),
                    "targets": arr(target(), C["GENO_SP_SELECT"], minItems=1)}, ("select", "targets"))
    overlay = obj({"index": integer("Subaction row to replace", section="15.5", minimum=0, maximum=1023),
                   "words": arr(word(), C["GENO_POOL_WORDS"]-1, minItems=1),
                   "file": string("Whitespace word file relative to mod root", section="15.5")}, ("index",),
                  oneOf=[{"required": ["words"], "not": {"required": ["file"]}}, {"required": ["file"], "not": {"required": ["words"]}}])
    specialattr = obj({"index": integer("Special attribute word index", section="15.5", minimum=0, maximum=C["GENO_SPECIAL_WORDS"]-1),
                       "offset": word(), "float": num("Float override", section="15.5"),
                       "int": integer("Integer override", section="15.5", minimum=-2147483648, maximum=2147483647)},
                      allOf=[{"anyOf": [{"required": ["index"]}, {"required": ["offset"]}]},
                             {"anyOf": [{"required": ["float"]}, {"required": ["int"]}]}])
    fighter = obj({"attach": string("Vanilla name/alias or existing fighter .dat file", maxLength=31),
                   "define": definition_schema(),
                   "common_states": arr(obj({"motion": integer("Native motion row", minimum=0, maximum=350),
                        "like": integer("Inherited motion row", minimum=0, maximum=350),
                        "subaction": integer("Installed retail animation row", minimum=0, maximum=1023),
                        "flags": integer("Motion flags", minimum=0, maximum=2147483647),
                        "move_id": integer("Stale move id", minimum=0, maximum=255),
                        **{slot: string("Callback override", enum=names) for slot, names in S["callbacks"].items()}}, ("motion",)), 64),
                   "name": string("Log display name", "target Pl file", maxLength=63),
                   "attributes": obj({key: (integer if is_int else num)("Common attribute " + key, "disc value", "7") for key, is_int in S["attrs"].items()}, maxProperties=C["GENO_MAX_ATTRS"]),
                   "jumps": obj({"max": integer("Total jumps including ground jump", "disc value", "10", minimum=1, maximum=250),
                                 "air_vy": arr(num("Per-air-jump vertical impulse", "disc value", "10"), C["GENO_MAX_JUMP_VY"])}),
                   "hooks": obj({key: arr(string("Hook name or name:integer", section="9"), C["GENO_EV_MAX_HOOKS"]) for key in ("on_init", "on_frame", "on_action", "on_land", "on_hit")}),
                   "states": arr(state, C["GENO_MAX_STATES"]), "articles": arr(article, C["GENO_MAX_ARTICLES"]),
                   "subactions": arr(overlay, C["GENO_MAX_OVERLAYS"]),
                   "special_attributes": arr(specialattr, C["GENO_MAX_SPECIAL"]),
                   "on_land": arr(obj({"from": target(), "to": target(), "keep_frame": field("boolean", "Keep current animation frame", False, "15.5")}, ("from", "to")), C["GENO_MAX_ONLAND"]),
                   "motion_anims": arr(obj({"motion": integer("Common motion id", section="19.12", minimum=0, maximum=1023),
                                            "subaction": integer("Animation row", section="19.12", minimum=0, maximum=1023)}, ("motion", "subaction")), C["GENO_MAX_MOTION_ANIM"]),
                   "specials": obj({key: {"anyOf": [target(), selector]} for key in ("n", "s", "hi", "lw", "air_n", "air_s", "air_hi", "air_lw")}),
                   "fx_bindings": string("Effect bindings JSON relative path", section="20"),
                   **{family: obj({key: field(["number", "boolean"], "Behavior parameter " + key, default, "16.4", **{"x-source": "melee/pc/geno/geno_game_v2.inc:geno_params"}) for key, default in params.items()}) for family, params in S["params"].items()}},
                  oneOf=[{"required": ["attach"], "not": {"required": ["define"]}},
                         {"required": ["define"], "not": {"required": ["attach"]}}])
    fighter["allOf"] = [{"if": {"required": ["define"]}, "then": {"properties": {
        field: {"items": {"properties": {key: {"maximum": 302}}}}
        for field, key in (("subactions", "index"), ("common_states", "subaction"),
                           ("states", "subaction"), ("motion_anims", "subaction"))}}}]
    result = obj({"geno": integer("Format version", C["GENO_VERSION"], "7", minimum=1, maximum=C["GENO_VERSION"]),
                  "fighters": arr(fighter, C["GENO_MAX_PROFILES"])}, ("geno", "fighters"))
    result.update({"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Geno fighter overlays",
                   "x-registry-keys": sorted(registry_keys()), "x-limits": limits()})
    result["x-source-contract"] = {path: hashlib.sha256(read(path).encode()).hexdigest() for path in
                                     ("pc/platform/geno_registry.c", "pc/platform/geno_define_registry.inc", "pc/geno/geno.h", "pc/geno/geno_game.c", "pc/geno/geno_game_v2.inc", "pc/geno/geno_profiles.inc", "pc/geno/geno_profile_storage.h", "pc/geno/geno_game_articles.inc")}
    return result


def limits():
    text = read("pc/geno/geno.h")
    result = {k: {"value": v, "source": f"melee/pc/geno/geno.h:{text[:text.index(k)].count(chr(10))+1}"}
              for k, v in C.items() if k.startswith(("GENO_MAX_", "GENO_POOL_", "GENO_ART_", "GENO_SPECIAL_WORDS", "GENO_EV_MAX", "GENO_SP_SELECT", "GENO_CHECK_CONDS", "GENO_VARS_PER_BANK"))}
    for k, v in re.findall(r"#define ((?:JDOC_|GN_MAX_)\w+) (\d+)", registry_text()):
        result[k] = {"value": int(v), "source": REGISTRY + f":{registry_text()[:registry_text().index(k)].count(chr(10))+1}"}
    result["JSON_DEPTH"] = {"value": 32, "source": REGISTRY + ":jd_value"}
    result["JSON_FILE_BYTES"] = {"value": 1 << 20, "source": REGISTRY + ":gn_read_file"}
    return result


def covered_keys(node=None):
    node = build_schema() if node is None else node
    out = set()
    if isinstance(node, dict):
        out.update(node.get("properties", {}))
        for value in node.values():
            out.update(covered_keys(value))
    elif isinstance(node, list):
        for value in node:
            out.update(covered_keys(value))
    return out


def template(node):
    lines = ["# Geno key reference (generated; do not edit)", "", "Regenerate with `python -m tools.geno.schema`.",
             "Use the adjacent minimal geno.json/mod.json pair as a starting point. Engine source wins.", "",
             "Every nested key is listed below. Defaults describe absence; inherited data needs your disc.", "",
             "| Key | Type / meaning | Engine default | Limits / reference |", "|---|---|---|---|"]
    def walk(n, prefix):
        if not isinstance(n, dict):
            return
        for key, value in n.get("properties", {}).items():
            path = prefix + key
            lim = "; ".join(f"{k}={value[k]}" for k in ("minimum", "maximum", "maxItems", "maxLength", "maxProperties", "enum", "pattern") if k in value)
            type_ = value.get("type", "choice")
            meaning = value.get("description", {"object": "Named settings", "array": "Ordered entries"}.get(type_ if isinstance(type_, str) else "", "See choice encodings"))
            default = value.get("x-engine-default", "absent")
            ref = value.get("x-reference", "geno.md §§7,15–20")
            cells = [path, f"{type_}: {meaning}", str(default), f"{lim}; {ref}; {value.get('x-source', REGISTRY)}"]
            lines.append("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
            walk(value, path + ".")
        if "items" in n:
            walk(n["items"], prefix.rstrip(".") + "[].")
        for branch in n.get("anyOf", []):
            walk(branch, prefix)
    walk(node, "")
    lines += ["", "## Runtime limits", "", "| Constant | Value | Source |", "|---|---|---|"]
    for name, info in limits().items():
        lines.append(f"| {name} | {info['value']} | {info['source']} |")
    lines += ["", "## Attach names and aliases", "", ", ".join(f"`{k}` ({v})" for k, v in S["vanilla"].items()), ""]
    return "\n".join(lines)


def artifacts():
    node = build_schema()
    missing = registry_keys() - covered_keys(node)
    if missing:
        raise ValueError("registry keys missing from schema: " + ", ".join(sorted(missing)))
    return {ROOT / "tools/geno/geno.schema.json": json.dumps(node, indent=2, ensure_ascii=False) + "\n",
            ROOT / "tools/geno/reference.md": script_reference(),
            ROOT / "docs/learn/geno-fighters/template/geno.json.md": template(node)}


def script_reference():
    from . import script
    lines = ["# Script command reference (generated)", "", "Regenerate: `python -m tools.geno.schema`.",
             "Source: melee/src/melee/ft/ftaction.c; melee/pc/geno/geno_game.c and geno_game_v2.inc; melee/pc/platform/gw_script.c.",
             "", "## Vanilla commands", "", "Fields are encoded integers. Word 0 excludes the opcode's high six bits.",
             "", "| Opcode | Name | Total words | Named fields (bit width; signed if marked) |", "|---|---|---|---|"]
    for op, name in enumerate(script.NAMES):
        fields = ", ".join(f"`{key}` ({width}{' signed' if signed else ''})" for key, wi, shift, width, signed in script.FIELDS.get(op, []))
        lines.append(f"| {op} | {name} | {script.LENGTHS[op]} | {fields or 'positional/raw form'} |")
    for title, names in (("Geno escape subcommands", script.SUBS), ("Engine values", script.VALUES),
                         ("Change-action conditions", script.CONDS), ("Comparisons", script.CMPS), ("Hooks", S["hooks"])):
        lines += ["", "## " + title, "", "| Name | Id |", "|---|---|"]
        lines += [f"| {key} | {value} |" for key, value in names.items()]
    lines += ["", "## Writable values", "", ", ".join(f"`{key}`" for key in sorted(script.WRITABLE))]
    lines += ["", "## Integer engine values", "", ", ".join(f"`{key}`" for key in sorted(script.INT_VALUES)),
              "", "SPECIAL_I:index is integer and SPECIAL_F:index is floating point. Both are read-only."]
    for prefix in ("GENO_BTN_", "GENO_HBF_", "GENO_LINK_"):
        lines += ["", "## " + prefix, "", "| Name | Bits |", "|---|---|"]
        lines += [f"| {key.removeprefix(prefix)} | 0x{value:X} |" for key, value in C.items() if key.startswith(prefix)]
    lines += ["", "## Callback names by slot", ""]
    for slot, names in S["callbacks"].items():
        lines.append(f"- {slot}: " + ", ".join(f"`{name}`" for name in names))
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    stale = []
    for path, text in artifacts().items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    if stale:
        print("stale generated files: " + ", ".join(stale))
    return bool(stale)


if __name__ == "__main__":
    raise SystemExit(main())
