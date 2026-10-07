"""Validate a Geno overlay without launching the game or opening a disc."""
import argparse
import difflib
import json
import math
from pathlib import Path
import re
import struct
import sys
from jsonschema import Draft202012Validator
from . import schema, script, source


def diagnostic(path, message, source="melee/pc/platform/geno_registry.c", **extra):
    return dict(path=path, message=message, source=source, **extra)


def json_text(text):
    """Replace // comments and trailing commas with spaces, preserving error locations."""
    chars = list(text)
    quoted = escaped = False
    i = 0
    while i < len(chars):
        c = chars[i]
        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
            i += 1
            continue
        if c == '"':
            quoted = True
        elif c == "/" and i+1 < len(chars) and chars[i+1] == "/":
            while i < len(chars) and chars[i] not in "\r\n":
                chars[i] = " "
                i += 1
            continue
        i += 1
    text = "".join(chars)
    # Do not match punctuation inside strings.
    quoted = escaped = False
    for i, c in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c == "," and re.match(r"\s*[}\]]", text[i+1:]):
            chars[i] = " "
    return "".join(chars)


def load_json(path):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError(f"duplicate key {key!r}: the engine uses the first occurrence")
            result[key] = value
        return result
    def reject(value):
        raise ValueError(f"nonfinite JSON number {value}")
    return json.loads(json_text(path.read_text(encoding="utf-8-sig")), object_pairs_hook=pairs, parse_constant=reject)


def schema_errors(data, node, path="$"):
    errors = []
    validator = Draft202012Validator(node)
    pending = list(validator.iter_errors(data))
    while pending:
        e = pending.pop(0)
        if e.validator in ("anyOf", "oneOf") and e.context:
            # Prefer branches matching the input's shape; retain useful nested typo diagnostics.
            shaped = [child for child in e.context if child.validator != "type"]
            if shaped:
                pending[0:0] = shaped
                continue
        p = path + "".join(f"[{v}]" if isinstance(v, int) else "." + v for v in e.absolute_path)
        message = e.message
        if e.validator == "additionalProperties" and isinstance(e.instance, dict):
            allowed = e.schema.get("properties", {})
            unknown = set(e.instance) - set(allowed)
            for key in sorted(unknown):
                nearest = difflib.get_close_matches(key, allowed, n=1, cutoff=0)
                errors.append(diagnostic(p + "." + key, f"unknown key {key!r}" + (f"; did you mean {nearest[0]!r}?" if nearest else "")))
            continue
        if e.validator == "type":
            message = "wrong type: " + message
        if e.validator in ("maxItems", "maxLength", "maxProperties", "minimum", "maximum"):
            message = f"{e.validator}={e.validator_value}: " + message
        errors.append(diagnostic(p, message))
    # C's fixed buffers count encoded bytes, whereas JSON Schema counts characters.
    def bytes_check(value, rule, p):
        if isinstance(value, str) and "maxLength" in rule and len(value.encode("utf-8")) > rule["maxLength"]:
            errors.append(diagnostic(p, f"UTF-8 string exceeds fixed buffer's {rule['maxLength']} byte payload"))
        if isinstance(value, dict):
            for key, child in value.items():
                bytes_check(child, rule.get("properties", {}).get(key, {}), p + "." + key)
        if isinstance(value, list):
            for i, child in enumerate(value):
                bytes_check(child, rule.get("items", {}), p + f"[{i}]")
        for branch in rule.get("anyOf", []):
            if Draft202012Validator(branch).is_valid(value):
                bytes_check(value, branch, p)
    bytes_check(data, node, path)
    return errors


def local_file(base, value, path, errors, *, payload=False):
    if not isinstance(value, str):
        return None
    relative = Path(value.replace("\\", "/"))
    if ".." in value or relative.is_absolute() or re.match(r"^[A-Za-z]:", value) or value.startswith(("/", "\\")):
        errors.append(diagnostic(path, "file path must stay inside the mod; '..' is refused by the engine"))
        return None
    roots = [base / "files"] if payload and (base / "files").is_dir() else [base]
    for root in roots:
        candidate = root / relative
        if not candidate.resolve().is_relative_to(base.resolve()):
            errors.append(diagnostic(path, "file symlink escapes the mod folder"))
            return None
        if candidate.is_file():
            return candidate
    errors.append(diagnostic(path, f"missing file {value!r}"))
    return None


def validate_target(value, states, path, errors, *, named=True):
    try:
        token = str(value)
        n = script.target_word(token, states if named else ())
        if n >> 28 == 2 and (n & 65535) >= len(states):
            raise ValueError(f"Geno state index {n & 65535} has no declared state")
    except (ValueError, TypeError) as e:
        errors.append(diagnostic(path, str(e)))


def validate_script(words, path, errors, states=(), articles=()):
    try:
        rows = list(script.commands(words))
        script.disassemble(words)
    except (ValueError, TypeError) as e:
        errors.append(diagnostic(path, str(e)))
        return
    boundaries = {o for o, _ in rows} | {len(words)}  # engine appends End at len(words)
    checks = conds = 0
    loops = 0
    for offset, ws in rows:
        w0, op = ws[0], ws[0] >> 26
        p = path + f"[word {offset}]"
        if op == 3:
            loops += 1
            if loops > 1:
                errors.append(diagnostic(p, "nested loop exceeds the decomp's event_return[3] declaration; its size is marked uncertain", "melee/src/melee/lb/types.h:CommandInfo"))
        elif op == 4:
            loops -= 1
            if loops < 0:
                errors.append(diagnostic(p, "endloop without loop"))
        elif op in (5, 7):
            errors.append(diagnostic(p, "absolute Subroutine/Goto pointer cannot resolve in a portable overlay; export stops on these"))
        elif op in (11, 12, 13, 15) and (w0 >> 23 & 7) > 3:
            errors.append(diagnostic(p, "hitbox slot must be 0..3", "melee/src/melee/ft/ftaction.c"))
        if op != 59:
            continue
        sub = next(k for k, v in script.SUBS.items() if v == w0 >> 20 & 63)
        minimum = {"NOP": 1, "ORIG": 1, "CHGCLR": 1, "CALL": 2, "PUT": 3, "IF": 3, "IFV": 4, "CHG": 2, "CHGAND": 1}.get(sub, 2)
        if len(ws) < minimum:
            errors.append(diagnostic(p, f"{sub} needs at least {minimum} words; engine substitutes zero for missing operands"))
            continue
        if sub in ("SKIP", "IF", "IFV"):
            skip = ws[{"SKIP": 1, "IF": 2, "IFV": 3}[sub]]
            if skip > 65536 or offset + len(ws) + skip not in boundaries:
                errors.append(diagnostic(p, f"{sub} forward skip {skip} does not land on a command boundary inside this overlay"))
        if sub in ("GET", "PUT", "IFV"):
            try:
                value = script.value_text(ws[1])
                if sub == "PUT" and value not in script.WRITABLE:
                    raise ValueError(f"{value} is read-only")
            except ValueError as e:
                errors.append(diagnostic(p, str(e), "melee/pc/geno/geno_game.c:geno_val_get/put"))
        if sub == "CALL":
            hook = next((k for k, v in schema.S["hooks"].items() if v == ws[1]), None)
            if hook is None:
                errors.append(diagnostic(p, f"unknown hook id {ws[1]}"))
            else:
                validate_hook(hook, ws[2] if len(ws)>2 else 0, articles, p, errors)
        if sub in ("CHG", "CHGAND"):
            cond = w0 >> 8 & 255
            if cond not in script.CONDS.values():
                errors.append(diagnostic(p, f"unknown change-action condition {cond}"))
            needed = (2 if sub == "CHG" else 1) + (0 if cond <= 3 else 1 if cond in (4, 5, 8) else 2)
            if len(ws) < needed:
                errors.append(diagnostic(p, f"change condition needs {needed} words"))
            if sub == "CHG":
                checks += 1
                conds = 1
                try:
                    validate_target(script.target_text(ws[1]), states, p, errors)
                except ValueError as e:
                    errors.append(diagnostic(p, str(e)))
            else:
                conds += 1
                if checks == 0:
                    errors.append(diagnostic(p, "CHGAND requires a preceding CHG"))
            if checks > schema.C["GENO_MAX_CHECKS"] or conds > schema.C["GENO_CHECK_CONDS"]:
                errors.append(diagnostic(p, "change-action check/condition cap exceeded (GENO_MAX_CHECKS / GENO_CHECK_CONDS)"))
            if cond == script.CONDS["VALUE"] and len(ws) >= needed:
                try:
                    script.value_text(ws[2 if sub == "CHG" else 1])
                except ValueError as e:
                    errors.append(diagnostic(p, str(e)))
        if sub == "CHGCLR":
            checks = conds = 0
    if loops > 0:
        errors.append(diagnostic(path, "loop without endloop"))


def validate_hook(name, arg, articles, path, errors):
    if name in ("geno.jumps.to_var", "geno.count_frames") and not 0 <= arg < schema.C["GENO_VARS_PER_BANK"]:
        errors.append(diagnostic(path, "hook variable index must be 0..63"))
    if name == "geno.article.spawn":
        index, variant = arg & 255, arg >> 8 & 255
        if index >= len(articles):
            errors.append(diagnostic(path, f"spawn references missing article {index}"))
        elif variant and variant >= len(articles[index].get("spawns", [])):
            errors.append(diagnostic(path, f"spawn variant {variant} does not exist"))


GXTX_FORMATS = {0: "I4", 1: "I8", 2: "IA4", 3: "IA8", 4: "RGB565", 5: "RGB5A3", 6: "RGBA8", 8: "C4", 9: "C8", 10: "C14X2"}


def presentation_checks(fighter, p, base, errors):
    """Slice 6: the files a define names as its own art (icon, portrait, stock). Each is a .gxtex in the package's files/ folder.
    A file that is not built yet is a warning (the engine falls back and logs once); a file that is there must be a v1 container whose
    sizes fit, and a stock icon must not need a palette (the HUD path carries none)."""
    import struct
    pres = fighter.get("presentation")
    if not isinstance(pres, dict):
        return
    for key in ("icon", "portrait", "stock"):
        value = pres.get(key)
        names = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        for j, name in enumerate(names):
            where = p + ".presentation." + key + ("" if isinstance(value, str) else "[%d]" % j)
            if ".." in name or "/" in name or "\\" in name or ":" in name:
                errors.append(diagnostic(where, "must be a plain file name"))
                continue
            path = Path(base) / "files" / name
            if not path.is_file():
                WARNINGS.append(diagnostic(where, "files/%s is not there (build it with pc/tools/png2gx.py); the game draws the fallback" % name))
                continue
            blob = path.read_bytes()
            if len(blob) < 64 or blob[:4] != b"GXTX" or struct.unpack(">I", blob[4:8])[0] != 1:
                errors.append(diagnostic(where, "files/%s is not a v1 .gxtex" % name))
                continue
            fmt, w, h, _tf, _tn, isz, tsz, ioff, toff = struct.unpack(">9I", blob[8:44])
            if fmt not in GXTX_FORMATS or ioff + isz > len(blob) or (tsz and toff + tsz > len(blob)) or not (0 < w <= 1024 and 0 < h <= 1024):
                errors.append(diagnostic(where, "files/%s: format %d, %dx%d, image %d@%d do not fit" % (name, fmt, w, h, isz, ioff)))
            elif key == "stock" and fmt >= 8:
                errors.append(diagnostic(where, "a stock icon cannot use a palette format (%s): encode it as rgb5a3 or rgba8" % GXTX_FORMATS[fmt]))


def package_files(base, name):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or ".." in name:
        return []
    return list(base.glob("fx/**/" + name + ".gfx.json")) + list(base.glob("fx/" + name + "/*.gfx.json"))


WARNINGS = []


def graph_checks(fighter, p, base, errors):
    """Define-level checks over the whole package: IASA with no callback, unreachable states, unbound specials."""
    states = fighter.get("states", [])
    names = [s_.get("name", "") for s_ in states]
    overlays = {}
    for o in fighter.get("subactions", []):
        try:
            overlays[o["index"]] = [script.word(w) for w in o["words"]] if "words" in o else script.read_words((base / o["file"]).read_text(encoding="utf-8-sig"))
        except (ValueError, OSError, KeyError):
            continue
    # (a) a state whose script runs IASA while its iasa callback is none
    for j, state in enumerate(states):
        sub = state.get("subaction")
        words = overlays.get(sub) if isinstance(sub, int) else None
        if not words:
            continue
        try:
            has_iasa = any(ws[0] >> 26 == 23 for _o, ws in script.commands(words))
        except (ValueError, TypeError):
            continue
        if has_iasa and state.get("iasa", "none") == "none":
            errors.append(diagnostic(p + f".states[{j}]", f"state {state.get('name', j)!r} runs an IASA command but its iasa callback is none; set \"iasa\": \"interrupt\"", "docs/geno.md section 16.2 (IASA trap)"))
    # (b) a state nothing targets
    refs = set()

    def ref(value):
        try:
            n = script.target_word(str(value), names)
            if n >> 28 == 2:
                refs.add(n & 65535)
        except (ValueError, TypeError):
            pass
    for v in fighter.get("specials", {}).values():
        for t in (v["targets"] if isinstance(v, dict) else [v]):
            ref(t)
    for state in states:
        for key in ("next", "land"):
            if key in state:
                ref(state[key])
        if "counter" in state and "target" in state["counter"]:
            ref(state["counter"]["target"])
    for row in fighter.get("on_land", []):
        ref(row["from"])
        ref(row["to"])
    for words in overlays.values():
        try:
            for _o, ws in script.commands(words):
                if ws[0] >> 26 == 59 and (ws[0] >> 20 & 63) == script.SUBS["CHG"] and len(ws) > 1 and ws[1] >> 28 == 2:
                    refs.add(ws[1] & 65535)
        except (ValueError, TypeError):
            pass
    for j, state in enumerate(states):
        if j not in refs:
            errors.append(diagnostic(p + f".states[{j}]", f"state {state.get('name', j)!r} is never targeted by a special, next, land, counter, on_land or CHG: unreachable"))
    # (c) unbound specials run the donor's code
    specials = fighter.get("specials", {})
    for key in ("n", "s", "hi", "lw", "air_n", "air_s", "air_hi", "air_lw"):
        if specials.get(key) is None and (not key.startswith("air_") or specials.get(key[4:]) is None):
            WARNINGS.append(diagnostic(p + ".specials." + key, "unbound: this special runs the donor's (Mario's) code"))


def validate(data, base):
    del WARNINGS[:]
    if any("moves" in f for f in data.get("fighters", []) if isinstance(f, dict)):
        from .define import expand_moves
        try:
            data = expand_moves(data)
        except (ValueError, KeyError) as e:
            return [diagnostic("$.fighters[].moves", str(e))]
    errors = schema_errors(data, schema.build_schema())
    if errors:  # avoid cascades / crashes on structurally invalid data
        return errors
    counts = dict(nodes=0, arena=0, depth=0)
    def count(value, depth=0):
        counts["nodes"] += 1
        counts["depth"] = max(counts["depth"], depth)
        if isinstance(value, str):
            counts["arena"] += len(value.encode("utf-8")) + 1
        elif isinstance(value, dict):
            for k, v in value.items():
                counts["arena"] += len(k.encode("utf-8")) + 1
                count(v, depth+1)
        elif isinstance(value, list):
            for v in value:
                count(v, depth+1)
        elif isinstance(value, float) and (not math.isfinite(value) or abs(value) > 3.4028234663852886e38):
            errors.append(diagnostic("$", "number cannot be represented as a finite engine float"))
    count(data)
    for key, constant in (("nodes", "JDOC_NODES"), ("arena", "JDOC_ARENA"), ("depth", "JSON_DEPTH")):
        cap = schema.limits()[constant]["value"]
        if counts[key] > cap:
            errors.append(diagnostic("$", f"JSON {key} {counts[key]} exceeds {constant}={cap}"))
    pool = 0
    slots = 0
    attaches = set()
    for i, fighter in enumerate(data["fighters"]):
        p = f"$.fighters[{i}]"
        if "define" in fighter:
            from .define import validate_definition
            errors.extend(diagnostic(path, message) for path, message in validate_definition(data, fighter, p))
            graph_checks(fighter, p, base, errors)
            presentation_checks(fighter, p, base, errors)
        elif "common_states" in fighter:
            errors.append(diagnostic(p+".common_states", "common state overrides require define"))
        attach = fighter.get("attach", "mario")
        resolved = schema.S["vanilla"].get(attach.lower(), attach.lower() if attach.lower().endswith(".dat") else None)
        if resolved is None:
            suggestion = difflib.get_close_matches(attach.lower(), schema.S["vanilla"], n=1)
            errors.append(diagnostic(p + ".attach", "unknown attach name" + (f"; did you mean {suggestion[0]!r}?" if suggestion else "")))
        elif "attach" in fighter and resolved.lower() in attaches:
            errors.append(diagnostic(p + ".attach", "another profile attaches to the same fighter; later profile shadows it"))
        elif "attach" in fighter:
            attaches.add(resolved.lower())
        states = [s.get("name", "") for s in fighter.get("states", [])]
        articles = fighter.get("articles", [])
        for label, names in (("states", states), ("articles", [a.get("name", "") for a in articles])):
            seen = set()
            for j, name in enumerate(names):
                if name and name.lower() in seen:
                    errors.append(diagnostic(p + f".{label}[{j}].name", "duplicate name; references resolve ambiguously"))
                seen.add(name.lower())
        for j, state in enumerate(fighter.get("states", [])):
            for key in ("like", "next", "land"):
                if key in state:
                    validate_target(state[key], states, p+f".states[{j}].{key}", errors, named=key != "like")
            if "counter" in state:
                ctr = state["counter"]
                if "target" in ctr:
                    validate_target(ctr["target"], states, p+f".states[{j}].counter.target", errors)
                if ctr.get("from", 1) > ctr.get("to", 2147483647):
                    errors.append(diagnostic(p+f".states[{j}].counter", "counter from must not exceed to"))
        for key, v in fighter.get("specials", {}).items():
            for target in v["targets"] if isinstance(v, dict) else [v]:
                validate_target(target, states, p+".specials."+key, errors)
        for j, row in enumerate(fighter.get("on_land", [])):
            for key in ("from", "to"):
                validate_target(row[key], states, p+f".on_land[{j}].{key}", errors)
        for event, refs in fighter.get("hooks", {}).items():
            for j, ref in enumerate(refs):
                name, _, arg = ref.partition(":")
                try:
                    if name not in schema.S["hooks"]:
                        raise ValueError(f"unknown hook {name!r}")
                    arg = script.integer(arg or "0", -2147483648, 2147483647)
                    validate_hook(name, arg, articles, p+f".hooks.{event}[{j}]", errors)
                except ValueError as e:
                    errors.append(diagnostic(p+f".hooks.{event}[{j}]", str(e)))
        for j, attr in enumerate(fighter.get("special_attributes", [])):
            if "offset" in attr:
                try:
                    off = script.word(attr["offset"])
                    if off % 4 or off//4 >= schema.C["GENO_SPECIAL_WORDS"]:
                        raise ValueError("special offset must be 4-aligned and inside 265 words")
                except ValueError as e:
                    errors.append(diagnostic(p+f".special_attributes[{j}].offset", str(e)))
        used = set()
        for j, overlay in enumerate(fighter.get("subactions", [])):
            slots += 1
            op = p+f".subactions[{j}]"
            if overlay["index"] in used:
                errors.append(diagnostic(op, "duplicate overlay row shadows another script"))
            used.add(overlay["index"])
            try:
                if "words" in overlay:
                    words = [script.word(w) for w in overlay["words"]]
                else:
                    path = local_file(base, overlay["file"], op+".file", errors)
                    if path is None:
                        continue
                    words = script.read_words(path.read_text(encoding="utf-8-sig"))
                if not words:
                    raise ValueError("overlay must not be empty")
                pool += len(words) + 1
                validate_script(words, op, errors, states, articles)
            except (ValueError, OSError) as e:
                errors.append(diagnostic(op, str(e)))
        for j, article in enumerate(articles):
            ap = p+f".articles[{j}]"
            if "model" in article:
                model = article["model"]
                file = local_file(base, model["file"], ap+".model.file", errors, payload=True)
                if file:
                    try:
                        from tools.mex_port.mex_hsd import Archive
                        ar = Archive(file.read_bytes())
                        if "symbol" in model:
                            ar.public(model["symbol"])
                        elif not any(name.endswith("_joint") for name, _ in ar.publics):
                            raise ValueError("no default *_joint public symbol")
                    except (ValueError, KeyError, struct.error) as e:
                        errors.append(diagnostic(ap+".model.symbol", "model archive/symbol cannot resolve: " + str(e)))
            if "fx" in article and not package_files(base, article["fx"]):
                errors.append(diagnostic(ap+".fx", "effect package not found in mod fx/; externally mounted packages cannot be checked offline", "melee/pc/platform/gw_fx.c"))
            names = [a.get("name", "").lower() for a in articles]
            for k, child in enumerate(article.get("children", [])):
                ref = child["article"]
                index = names.index(ref.lower()) if isinstance(ref, str) and ref.lower() in names else ref if isinstance(ref, int) else -1
                if not 0 <= index < len(articles):
                    errors.append(diagnostic(ap+f".children[{k}].article", "child names no declared article"))
                elif child.get("spawn", 0) and child["spawn"] >= len(articles[index].get("spawns", [])):
                    errors.append(diagnostic(ap+f".children[{k}].spawn", "child spawn variant missing"))
        if "fx_bindings" in fighter:
            file = local_file(base, fighter["fx_bindings"], p+".fx_bindings", errors)
            if file:
                try:
                    binding = load_json(file)
                    # Reuse the IR contract, removing converter-only requirements.
                    fx_schema = json.loads((schema.ROOT / "ports/ir/schema/fx_bindings.schema.json").read_text(encoding="utf-8"))
                    fx_schema["required"] = ["geno_fx_bindings", "states"]
                    state_rule = fx_schema["properties"]["states"]["items"]
                    state_rule["required"] = ["subaction", "calls"]
                    call_rule = fx_schema["$defs"]["Call"]
                    call_rule["required"] = ["package"]
                    call_rule["properties"]["package"].pop("pattern", None)
                    binding_errors = schema_errors(binding, fx_schema, p + ".fx_bindings")
                    errors.extend(binding_errors)
                    if binding_errors:
                        continue
                    fx_source = source.read("pc/platform/gw_fx_internal.h")
                    caps = {name: int(value) for name, value in re.findall(r"#define (FX_BIND_\w+)\s+(\d+)", fx_source)}
                    rows = binding.get("states", []) if isinstance(binding, dict) else []
                    if len(rows) > caps["FX_BIND_STATES"]:
                        errors.append(diagnostic(p + ".fx_bindings", "exceeds FX_BIND_STATES=" + str(caps["FX_BIND_STATES"]), "melee/pc/platform/gw_fx_internal.h"))
                    total = 0
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        calls = row.get("calls", [])
                        if not isinstance(calls, list):
                            continue
                        active = [c for c in calls if isinstance(c, dict) and all(w.get("holds", True) for w in c.get("when", []) if isinstance(w, dict))]
                        total += len(active)
                        if len(active) > caps["FX_BIND_PER_STATE"]:
                            errors.append(diagnostic(p + ".fx_bindings", "exceeds FX_BIND_PER_STATE=" + str(caps["FX_BIND_PER_STATE"])))
                        for call in active:
                            package = call.get("package")
                            if isinstance(package, str) and not package_files(base, package):
                                errors.append(diagnostic(p + ".fx_bindings", "effect package cannot resolve: " + package))
                    if total > caps["FX_BIND_CALLS"]:
                        errors.append(diagnostic(p + ".fx_bindings", "exceeds FX_BIND_CALLS=" + str(caps["FX_BIND_CALLS"])))
                except (ValueError, OSError) as e:
                    errors.append(diagnostic(p+".fx_bindings", str(e)))
    if pool > schema.C["GENO_POOL_WORDS"]:
        errors.append(diagnostic("$", f"overlay pool including appended End words {pool} exceeds GENO_POOL_WORDS={schema.C['GENO_POOL_WORDS']} (global across all mounting mods)"))
    if slots > schema.limits()["GN_MAX_SLOTS"]["value"]:
        errors.append(diagnostic("$", "overlay slots exceed GN_MAX_SLOTS=256 (global across all mounting mods)"))
    return errors


def mod_schema():
    sizes = dict(id=63, name=127, version=31, kind=15, pack=31, description=127, hash=79)
    props = {key: {"type": "string", "maxLength": cap} for key, cap in sizes.items()}
    props["kind"]["enum"] = ["base", "fighter", "stage", "misc", "script"]
    props.update({key: schema.arr({"type": "string", "maxLength": 63}, 8) for key in ("requires", "conflicts")})
    props["engine"] = schema.obj({"pobj_palette": {"type": "integer", "minimum": 0, "maximum": 1}})
    return schema.obj(props)


def refusal_files(base):
    errors = []
    for file in base.rglob("*"):
        if not file.is_file():
            continue
        n = file.name.lower()
        reason = None
        if file.suffix.lower() in (".iso", ".gcm", ".dol", ".ssm", ".hps"):
            reason = "disc image, executable, or whole game audio bank"
        elif n in ("mxdt.dat", "plco.dat", "ifall.dat", "ifall.usd", "mnslchr.usd", "mnslchr.dat", "codes.gct"):
            reason = "whole game/table/menu archive or disc patch"
        elif re.fullmatch(r"pl.+\.(dat|usd)", n) or re.fullmatch(r"gr.+\.(dat|usd)", n):
            reason = "whole fighter/stage archive; provenance cannot establish shareability"
        if reason:
            errors.append(diagnostic(str(file.relative_to(base)), "refused for sharing: " + reason, "AGENTS.md: no disc-derived data"))
    return errors


def validate_path(path):
    path = Path(path)
    base = path if path.is_dir() else path.parent
    geno = base / "geno.json" if path.is_dir() else path
    errors = []
    for file, node in ((geno, None), (base / "mod.json", mod_schema())):
        try:
            if node is None and file.stat().st_size > 1 << 20:
                raise ValueError("geno.json exceeds engine gn_read_file 1 MiB limit")
            data = load_json(file)
            errors += validate(data, base) if node is None else schema_errors(data, node, "mod.json")
        except json.JSONDecodeError as e:
            errors.append(diagnostic(file.name, f"JSON syntax: {e.msg}", line=e.lineno, column=e.colno))
        except (ValueError, OSError) as e:
            errors.append(diagnostic(file.name, str(e)))
    errors += refusal_files(base)
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path)
    ap.add_argument("--json", action="store_true", help="machine-readable diagnostics")
    args = ap.parse_args()
    errors = validate_path(args.path)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": WARNINGS}, indent=2))
    elif errors:
        for error in errors:
            location = f":{error['line']}:{error['column']}" if "line" in error else ""
            print(f"{error['path']}{location}: {error['message']} [{error['source']}]")
    else:
        print("OK: Geno fighter package and mod metadata validated (offline; disc rows and gameplay require LAB checks)")
    if not args.json:
        for w in WARNINGS:
            print(f"WARNING {w['path']}: {w['message']}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
