"""Join decomp action states to a locally built retail plan. No disc reads."""
import copy
import re
from pathlib import Path

from ports.ir.tools.plan_parts import COMMON
from . import previewability


def enum_values(text, name, known=None):
    """The source enums use integers, prior symbols and +/-. Reject other C syntax."""
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    match = re.search(r"\benum\s+" + re.escape(name) + r"\s*\{(.*?)\}", clean, re.S)
    if not match:
        raise ValueError(f"missing enum {name}")
    scope, result, value = dict(known or {}), {}, 0
    for item in match[1].split(","):
        item = item.strip()
        if not item:
            continue
        key, sep, expression = item.partition("=")
        key = key.strip()
        if not re.fullmatch(r"\w+", key):
            raise ValueError(f"unsupported enum member {item}")
        if sep:
            expression = re.sub(r"\s+", "", expression)
            pieces = re.findall(r"[+-]?(?:0[xX][0-9a-fA-F]+|[0-9]+|[A-Za-z_]\w*)", expression)
            if not pieces or "".join(pieces) != expression:
                raise ValueError(f"unsupported enum expression {expression}")
            value = 0
            for piece in pieces:
                token = piece.lstrip("+-")
                if token in scope:
                    number = scope[token]
                else:
                    try:
                        number = int(token, 0)
                    except ValueError:
                        raise ValueError(f"unknown enum symbol {token}") from None
                value += -number if piece.startswith("-") else number
        scope[key] = result[key] = value
        value += 1
    return result


def state_entries(text, symbols):
    rows = []
    for prefix, state, motion, sub in re.findall(
            r"// (ftCo|ftCa)_MS_(\w+) = (\d+)\s*\n\s*(\w+),", text):
        if sub not in symbols:
            raise ValueError(f"unknown subaction {sub} for {prefix}_MS_{state}")
        rows.append({"motion": int(motion), "state": state, "subaction": symbols[sub]})
    if not rows:
        raise ValueError("no motion-state entries found; source table format changed")
    return rows


def load_states(game):
    game = Path(game)
    common = (game / "src/melee/ft/kinds/ftCommon/forward.h").read_text(encoding="utf-8")
    captain = (game / "src/melee/ft/kinds/ftCaptain/forward.h").read_text(encoding="utf-8")
    symbols = enum_values(common, "ftCo_Submotion")
    symbols.update(enum_values(captain, "ftCa_Submotion", symbols))
    motions = enum_values(common, "ftCommon_MotionState")
    motions.update(enum_values(captain, "ftCaptain_MotionState", motions))
    rows = []
    for relative in ("src/melee/ft/ftmotionstates.c", "src/melee/ft/kinds/ftCaptain/ftcaptain.c"):
        rows.extend(state_entries((game / relative).read_text(encoding="utf-8"), symbols))
    rows.sort(key=lambda row: row["motion"])
    if [r["motion"] for r in rows] != list(range(motions["ftCa_MS_Count"])):
        raise ValueError("incomplete or duplicate Captain motion-state table")
    if symbols["ftCa_SM_Count"] != 318:
        raise ValueError("Captain's subaction layout changed; review the retail define contract")
    return rows


def move_tag(state):
    # Workbench currently requests engine lift through this tag, including air specials.
    if state.startswith(("AttackAir", "SpecialAir")):
        return "aerial"
    for prefix, tag in (("Attack1", "jab"), ("AttackDash", "dash_attack"),
                        ("AttackS3", "tilt"), ("AttackHi3", "tilt"), ("AttackLw3", "tilt"),
                        ("Attack", "smash"), ("Special", "special"), ("Throw", "throw"),
                        ("Catch", "grab"), ("Cliff", "ledge"), ("Damage", "damage"),
                        ("Down", "damage"), ("Passive", "tech"), ("Guard", "shield"),
                        ("Escape", "dodge"), ("Jump", "air"), ("Fall", "air"), ("Wait", "idle")):
        if state.startswith(prefix):
            return tag
    return "movement"


def make_rows(plan, states, scripts, seeds=()):
    seed_by_motion = {m: row for row in seeds for m in row.get("motions", [])}
    row_clips = plan["row_clips"]
    clips = plan["bank"]["clips"]
    rows, used = [], set()
    for state in sorted(states, key=lambda row: row["motion"]):
        motion, sub, name = state["motion"], state["subaction"], state["state"]
        if sub < -1 or sub >= len(row_clips):
            raise ValueError(f"{name}: subaction {sub} outside package row table")
        clip = row_clips[sub] if sub >= 0 else None
        if clip is not None and clip not in clips:
            raise ValueError(f"{name}: clip {clip!r} absent from bank")
        seed = copy.deepcopy(seed_by_motion.get(motion, {}))
        row_name = seed.get("name") or re.sub(r"(?<!^)(?=[A-Z][a-z])", "_", name).lower()
        if row_name in used:
            row_name += f"_{motion}"
        used.add(row_name)
        seed.update(name=row_name, motions=[motion], state=name, subaction=sub,
                    tag=seed.get("tag", move_tag(name)), pick={"clip": clip or ""},
                    availability="ready" if clip else "no-fixed-animation" if sub < 0 else "missing-clip")
        seed.pop("script", None)
        if sub in scripts:
            seed["script"] = scripts[sub]
        rows.append(seed)
    return previewability.annotate_gameplay({"moves": rows}, plan)["moves"]


def resolve_roles(plan, table):
    """Project-owned semantic table -> plan roles and assembly token substitutions.

    COMMON is the PlCo order used by the existing define tools, including WaistB;
    Fighter_Part in the decomp is off by one from slot 16 and cannot be used here.
    A missing optional role remains unknown, never joint 255 or an invented bone.
    """
    joints = {j["index"] for j in plan["joints"]}
    parts = plan["parts"]["part_to_joint"]
    roles, tokens = {}, {}
    for token, entry in table["roles"].items():
        for part in entry["parts"]:
            slot = COMMON.index(part)
            if slot >= len(parts):
                raise ValueError(f"parts table lacks {part}")
            joint = parts[slot]
            if joint == 255:
                continue
            if type(joint) is not int or joint not in joints:
                raise ValueError(f"{part}: invalid joint {joint}")
            roles[entry["role"]] = [joint]
            tokens[token] = joint
            break
        else:
            if entry.get("required"):
                raise ValueError(f"required role {token} has no retail part")
    return roles, tokens
