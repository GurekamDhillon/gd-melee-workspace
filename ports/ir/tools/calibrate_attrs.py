#!/usr/bin/env python3
"""calibrate_attrs.py - Ultimate fighter attributes -> Melee, fitted on the fighters both games have.

    python ports/ir/tools/calibrate_attrs.py [-o _build/tmp/ir/attr_calibration.json] [--port trail]

The port is semantic ("feels identical"), so an Ultimate number only has to land where Melee's
equivalent would. The 26 fighters in both games are ground truth: for each Melee common attribute
(ftCo_DatAttrs, melee/src/melee/ft/types.h) this reads the vanilla disc's value and the Ultimate
value (fighter_param.prc, upstream ParamXML with the toolkit's label file), maps the Ultimate side
to the same quantity (MAP; heights become launch speeds by v = sqrt(2 g h) with the fighter's own
Ultimate gravity), and fits melee = k * ultimate through the origin. Each fit reports the spread of
the per-fighter ratios; a wide spread says a single factor would mislead and the attribute needs
judgment instead. --port applies the fits to one Ultimate fighter.
"""
import argparse
import json
import math
import os
import re
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from convert_ultimate_anim import FIGHTERS, ROOT, TOOL  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "tools", "mex_port"))
import mex_hsd  # noqa: E402

# Ultimate fighter -> Melee fighter file (the vanilla disc's PlXx.dat)
PAIRS = {"mario": "PlMr", "donkey": "PlDk", "link": "PlLk", "samus": "PlSs", "yoshi": "PlYs",
         "kirby": "PlKb", "fox": "PlFx", "pikachu": "PlPk", "luigi": "PlLg", "ness": "PlNs",
         "captain": "PlCa", "purin": "PlPr", "peach": "PlPe", "koopa": "PlKp", "popo": "PlPp",
         "sheik": "PlSk", "zelda": "PlZd", "mariod": "PlDr", "falco": "PlFc", "marth": "PlMs",
         "younglink": "PlCl", "ganon": "PlGn", "mewtwo": "PlMt", "roy": "PlFe", "pichu": "PlPc",
         "gamewatch": "PlGw"}
v0 = lambda u, h: math.sqrt(2 * u["air_accel_y"] * u[h])
# Melee field -> (how to get the same quantity from Ultimate's params)
MAP = {
    "walk_max_vel": lambda u: u["walk_speed_max"],
    "ground_friction": lambda u: u["ground_brake"],
    "jab_2_input_window": lambda u: u["combo_attack_12_end"],
    "jab_3_input_window": lambda u: u["combo_attack_13_end"],
    "walk_accel_mul": lambda u: u["walk_accel_mul"],
    "walk_accel_base": lambda u: u["walk_accel_add"],
    "dash_initial_velocity": lambda u: u["dash_speed"],
    "dash_accel_mul": lambda u: u["run_accel_mul"],
    "dash_accel_base": lambda u: u["run_accel_add"],
    "ground_to_air_jump_momentum_multiplier": lambda u: u["jump_speed_x_mul"],
    "air_jump_h_multiplier": lambda u: u["jump_aerial_speed_x_mul"],
    "dash_max_velocity": lambda u: u["run_speed_max"],
    "jump_startup_time": lambda u: u["jump_squat_frame"],
    "jump_h_initial_velocity": lambda u: u["jump_speed_x"],
    "jump_h_max_velocity": lambda u: u["jump_speed_x_max"],
    "jump_v_initial_velocity": lambda u: v0(u, "jump_y"),
    "hop_v_initial_velocity": lambda u: v0(u, "mini_jump_y"),
    "air_jump_v_multiplier": lambda u: math.sqrt(u["jump_aerial_y"] / u["jump_y"]),
    "gravity": lambda u: u["air_accel_y"],
    "terminal_velocity": lambda u: u["air_speed_y_stable"],
    "fast_fall_velocity": lambda u: u["dive_speed_y"],
    "air_drift_max": lambda u: u["air_speed_x_stable"],
    "air_drift_stick_mul": lambda u: u["air_accel_x_mul"],
    "aerial_drift_base": lambda u: u["air_accel_x_add"],
    "aerial_friction": lambda u: u["air_brake_x"],
    "weight": lambda u: u["weight"],
    "model_scaling": lambda u: u["scale"],
    "initial_shield_size": lambda u: u["shield_radius"],
    "normal_landing_lag": lambda u: u["landing_frame"],
    "landingairn_lag": lambda u: u["landing_attack_air_frame_n"],
    "landingairf_lag": lambda u: u["landing_attack_air_frame_f"],
    "landingairb_lag": lambda u: u["landing_attack_air_frame_b"],
    "landingairhi_lag": lambda u: u["landing_attack_air_frame_hi"],
    "landingairlw_lag": lambda u: u["landing_attack_air_frame_lw"],
    "ledge_jump_horizontal_velocity": lambda u: u["cliff_jump_x_speed"],
    "ledge_jump_vertical_velocity": lambda u: v0(u, "cliff_jump_y"),
}


def ultimate_params():
    exe = os.path.join(TOOL, "apps", "ParamXML", "ParamXML-win-x64", "ParamXML.exe")
    prc = os.path.join(FIGHTERS, "common", "param", "fighter_param.prc")
    labels = os.path.join(TOOL, "references", "ParamLabels.csv")
    with tempfile.TemporaryDirectory() as tmp:
        xml = os.path.join(tmp, "fp.xml")
        subprocess.run([exe, "-d", prc, "-o", xml, "-l", labels], check=True, capture_output=True)
        text = open(xml, encoding="utf-8").read()
    out = {}
    for blk in re.findall(r"<struct[^>]*>(.*?)</struct>", text, re.S):
        f = dict(re.findall(r'<(?:float|int|byte|short|sbyte|ushort|uint)\s+hash="(\w+)">([^<]*)<', blk))
        k = re.search(r'hash="fighter_kind">fighter_kind_(\w+)<', blk)
        if k:
            out[k.group(1)] = {n: float(v) for n, v in f.items()}
    return out


def melee_attrs(iso):
    src = open(os.path.join(ROOT, "melee", "src", "melee", "ft", "types.h"), encoding="utf-8").read()
    blk = src[src.index("typedef struct ftCo_DatAttrs {"):src.index("} ftCo_DatAttrs;")]
    fields = re.findall(r"/\* \+([0-9A-F]{3}) fp\+[0-9A-F]+ \*/ (float|int) (\w+);", blk)
    g = mex_hsd.Gcm(iso)
    out = {}
    for ult, pl in PAIRS.items():
        ar = mex_hsd.Archive(g.read(pl + ".dat"))
        fd = ar.public([s for s, _ in ar.publics if s.startswith("ftData")][0])
        ca = ar.u32(fd)
        vals = {}
        for off, ty, nm in fields:
            raw = bytes(ar.data[ca + int(off, 16):ca + int(off, 16) + 4])
            vals[nm] = struct.unpack(">f" if ty == "float" else ">i", raw)[0]
        out[ult] = vals
    return out


def fit(pairs):
    """melee = k * ult through the origin; spread = the ratios' interquartile range / median."""
    rs = sorted(m / u for u, m in pairs if u)
    if not rs:
        return None
    med = rs[len(rs) // 2]
    q1, q3 = rs[len(rs) // 4], rs[(3 * len(rs)) // 4]
    k = sum(u * m for u, m in pairs) / sum(u * u for u, m in pairs)
    return {"k": round(k, 5), "median_ratio": round(med, 5),
            "spread": round((q3 - q1) / med, 3) if med else None, "n": len(rs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=os.path.join(ROOT, "_build", "tmp", "ir", "attr_calibration.json"))
    ap.add_argument("--port", help="apply the fits to this Ultimate fighter")
    a = ap.parse_args()
    iso = os.environ.get("GW_ISO_VANILLA")
    if not iso:
        sys.exit("GW_ISO_VANILLA is not set (source .env)")
    ult, mel = ultimate_params(), melee_attrs(iso)
    res = {}
    for field, get in MAP.items():
        pairs = []
        for u_name in PAIRS:
            if u_name in ult and u_name in mel:
                try:
                    pairs.append((get(ult[u_name]), mel[u_name][field]))
                except (KeyError, ValueError, ZeroDivisionError):
                    pass
        res[field] = fit(pairs)
        r = res[field]
        flag = "" if r and r["spread"] is not None and r["spread"] < 0.25 else "  <- wide: judgment"
        print(f"{field:34} k {r['k']:9.4f}  median {r['median_ratio']:9.4f}  spread {r['spread']}{flag}" if r else field)
    k = res.get("model_scaling")
    out = {"fits": res, "pairs": PAIRS}
    if a.port:
        u = ult[a.port]
        attrs, why = {}, {}
        for field, get in MAP.items():
            r = res[field]
            if r:
                attrs[field] = round(get(u) * r["median_ratio"], 5); why[field] = "median fit"
        # Judgment where one factor misleads (the fits' wide spreads):
        # - aerial landing lag: Melee's is the lag BEFORE an L-cancel halves it and Ultimate has no
        #   L-cancel, so 2x: an L-cancelled aerial lands exactly as in Ultimate (the cast's ~1.8-2.2)
        for d in ("n", "f", "b", "hi", "lw"):
            attrs[f"landingair{d}_lag"] = 2 * u[f"landing_attack_air_frame_{d}"]; why[f"landingair{d}_lag"] = "2x (L-cancel)"
        # - jumpsquat: every Ultimate fighter has 3, Melee's (3-8) is per-character identity: keep 3
        attrs["jump_startup_time"] = u["jump_squat_frame"]; why["jump_startup_time"] = "Ultimate's own"
        # - jump count: a count, not a scale; Kirby's 5 vs 6 would skew a fit. Ultimate's own number.
        attrs["max_jumps"] = int(u["jump_count_max"]); why["max_jumps"] = "Ultimate's own"
        # - air acceleration: the games split mul/base differently; fit the full-stick total
        tot = [(ult[n]["air_accel_x_mul"] + ult[n]["air_accel_x_add"],
                mel[n]["air_drift_stick_mul"] + mel[n]["aerial_drift_base"]) for n in PAIRS if n in ult and n in mel]
        k_tot = fit(tot)["median_ratio"]
        full = (u["air_accel_x_mul"] + u["air_accel_x_add"]) * k_tot
        base_share = u["air_accel_x_add"] / (u["air_accel_x_mul"] + u["air_accel_x_add"])
        attrs["aerial_drift_base"] = round(full * base_share, 5); attrs["air_drift_stick_mul"] = round(full * (1 - base_share), 5)
        why["aerial_drift_base"] = why["air_drift_stick_mul"] = f"full-stick total fit (k {k_tot}), split as Ultimate's"
        out["port"] = {"fighter": a.port, "attrs": attrs, "why": why}
        for f in attrs: print(f"  {f:34} {attrs[f]:>9}   {why[f]}")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
