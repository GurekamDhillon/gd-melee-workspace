#!/usr/bin/env python3
"""attr_apply.py - write calibrate_attrs.py's fitted Melee attributes into an installed fighter file.

calibrate_attrs.py --port <fighter> fits the Ultimate fighter's movement numbers to Melee's units
over the 26 fighters both games have and stores them in _build/tmp/ir/attr_calibration.json
("port": {"fighter", "attrs", "why"}). Until this module nothing read that file, so an installed
port kept its host's attributes (Sora: Marth's walk 1.6, weight 87, gravity 0.085...).

The values go into the fighter file's own common attribute block (ftData word 0 -> ftCo_DatAttrs,
the block the engine copies into every fighter at spawn). That route covers every ftCo_DatAttrs
field, which Geno's `attributes` key does not: geno_game.c's table has 40 names and lacks the
landing lags (normal/aerial) and the ledge-jump speeds. Geno overrides still apply on top.
"""
import json
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TYPES_H = os.path.join(ROOT, "melee", "src", "melee", "ft", "types.h")
DEFAULT_CALIBRATION = os.path.join(ROOT, "_build", "tmp", "ir", "attr_calibration.json")

# Fits that are not applied, with why. model_scaling scales the whole skeleton (ECB, camera, hitbox
# reach and the audited hitbox positions follow it); the installed body's size was set against the
# host's 1.15 and an unreviewed 13% size change is not a movement attribute.
HELD_BACK = {"model_scaling": "scales the whole skeleton; the body's size is not a movement attribute"}


def attr_layout(types_h=TYPES_H):
    """{field: (byte offset in ftCo_DatAttrs, is_int)} for its 32-bit fields, from the decomp struct."""
    with open(types_h, encoding="utf-8") as fh:
        src = fh.read()
    blk = src[src.index("typedef struct ftCo_DatAttrs {"):src.index("} ftCo_DatAttrs;")]
    return {nm: (int(off, 16), ty == "int")
            for off, ty, nm in re.findall(r"/\* \+([0-9A-F]{3}) fp\+[0-9A-F]+ \*/ (float|int) (\w+);", blk)}


def load_port_attrs(path, fighter):
    """(attrs to apply, {field: reason held back}) from a calibration file made with --port <fighter>."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    port = doc.get("port") or {}
    if port.get("fighter") != fighter:
        raise ValueError(f"{path} was calibrated for {port.get('fighter')!r}, not {fighter!r} "
                         f"(run calibrate_attrs.py --port {fighter})")
    layout = attr_layout()
    unknown = sorted(set(port["attrs"]) - set(layout))
    if unknown:
        raise ValueError(f"calibration names unknown ftCo_DatAttrs fields: {unknown}")
    held = {k: why for k, why in HELD_BACK.items() if k in port["attrs"]}
    return {k: v for k, v in port["attrs"].items() if k not in held}, held


def apply_to_block(w, fd, attrs):
    """Write attrs into the ftCo_DatAttrs block ftData fd points at; returns {field: {before, after}}."""
    layout = attr_layout()
    block = w.u32(fd)
    if not block:
        raise ValueError("ftData has no common attribute block")
    span = max(off for off, _ in layout.values()) + 4
    if block + span > len(w.data):
        raise ValueError(f"attribute block 0x{block:X} runs past the file ({len(w.data)} bytes)")
    rep = {}
    for name, value in attrs.items():
        off, is_int = layout[name]
        at = block + off
        if is_int:
            before = struct.unpack_from(">i", w.data, at)[0]
            struct.pack_into(">i", w.data, at, int(round(value)))
            rep[name] = {"before": before, "after": int(round(value))}
        else:
            before = struct.unpack_from(">f", w.data, at)[0]
            struct.pack_into(">f", w.data, at, float(value))
            rep[name] = {"before": round(before, 5), "after": round(struct.unpack_from(">f", w.data, at)[0], 5)}
    return rep


def resolve(option, fighter):
    """The installer's --attrs: 'off' -> None; 'auto' -> the default calibration when it is for this
    fighter (None otherwise); a path -> that file, which must be for this fighter."""
    if option == "off":
        return None
    if option == "auto":
        if not os.path.isfile(DEFAULT_CALIBRATION):
            return None
        try:
            attrs, held = load_port_attrs(DEFAULT_CALIBRATION, fighter)
        except ValueError:
            return None
        return DEFAULT_CALIBRATION, attrs, held
    attrs, held = load_port_attrs(option, fighter)
    return option, attrs, held


def kinetics_params(option, fighter):
    """acmd_to_ftcmd.translate's `kinetics` from the calibration, or None (--attrs off / no file).

    speed_ratio converts an Ultimate speed to Melee units with the fitted vertical launch speed
    ratio (jump_v_initial_velocity: the same quantity as a script-set rise); gravity and terminal
    are the calibrated Melee values the installed fighter will have.
    """
    choice = resolve(option, fighter)
    if not choice:
        return None
    path, attrs, _ = choice
    with open(path, encoding="utf-8") as fh:
        fits = json.load(fh)["fits"]
    return {"speed_ratio": fits["jump_v_initial_velocity"]["median_ratio"],
            "gravity": attrs["gravity"], "terminal": attrs["terminal_velocity"]}
