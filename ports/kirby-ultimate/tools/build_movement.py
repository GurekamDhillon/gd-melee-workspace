#!/usr/bin/env python3
"""Build a playable, movement-only Ultimate Kirby Geno overlay on Melee Kirby.

This is an approximate Ultimate-to-Melee conversion, not an Ultimate runtime
emulator. Melee Kirby supplies his existing model, crouch states, action logic,
five aerial-jump states, collision body, and animations. Only fighter movement
parameters are overlaid. Source motion-list entry numbers are never treated as
Melee action IDs. No extracted asset bytes enter the pack.

The Ultimate fighter_param jump_y, mini_jump_y, and jump_aerial_y labels are
treated as heights. v=sqrt(2*g*h) is a continuous-physics approximation; it
does not model either game's exact frame integration. The five aerial impulses
retain Melee Kirby's decreasing per-hop ratios because the Ultimate IR has no
per-hop impulse sequence. Source-to-target values in the manifest make these
assumptions reviewable and tunable after a live movement check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
DEFAULT_BASELINE = ROOT / "experiment/brawl-kirby/analysis/melee_kirby.json"
MOD_ID = "ultimate-kirby-movement"


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def ir_fields(document: dict) -> dict[str, dict]:
    subject = document.get("subject", {})
    if (document.get("document_id"), subject.get("character"), subject.get("engine")) != (
        "kirby.ultimate", "Kirby", "ssbu.switch"
    ):
        raise ValueError("expected the kirby.ultimate SSBU Kirby IR")
    fields = {}
    for item in document["behavior"]["attributes"]["common"]:
        name = item.get("engine_name")
        if name in fields:
            raise ValueError(f"duplicate Ultimate parameter: {name}")
        fields[name] = item
    return fields


def baseline_hops(document: dict) -> list[float]:
    by_name = {item["name"]: item["value"] for item in document["special_attributes"]}
    names = [f"jumpaerial_jump{i}_vertical_momentum" for i in range(1, 6)]
    try:
        hops = [float(by_name[name]) for name in names]
    except KeyError as error:
        raise ValueError(f"Melee Kirby baseline lacks {error.args[0]}") from error
    if not all(math.isfinite(value) and value > 0 for value in hops):
        raise ValueError("Melee Kirby baseline has invalid aerial jump impulses")
    return hops


def convert(ir: dict, baseline: dict, ir_sha256: str, baseline_sha256: str) -> tuple[dict, dict, dict]:
    fields = ir_fields(ir)
    mappings: dict[str, dict] = {}

    def value(name: str) -> float:
        if name not in fields:
            raise ValueError(f"missing Ultimate movement field: {name}")
        raw = fields[name]["value"]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
            raise ValueError(f"invalid Ultimate movement field: {name}={raw!r}")
        return raw

    def record(target: str, sources: list[str], result: float | list[float], formula: str,
               confidence: str = "inferred") -> float | list[float]:
        mappings[target] = {
            "source_fields": sources,
            "source_values": {name: value(name) for name in sources},
            "formula": formula,
            "output": result,
            "confidence": confidence,
            "evidence": sorted({ev for name in sources for ev in fields[name].get("provenance", {}).get("evidence", [])}),
        }
        return result

    attrs = {}
    direct = {
        "walk_accel_mul": "walk_accel_mul",
        "walk_accel_base": "walk_accel_add",
        "walk_max_vel": "walk_speed_max",
        "ground_friction": "ground_brake",
        "dash_initial_velocity": "dash_speed",
        "dash_accel_mul": "run_accel_mul",
        "dash_accel_base": "run_accel_add",
        "dash_max_velocity": "run_speed_max",
        "jump_startup_time": "jump_squat_frame",
        "jump_h_initial_velocity": "jump_speed_x",
        "ground_to_air_jump_momentum_multiplier": "jump_speed_x_mul",
        "jump_h_max_velocity": "jump_speed_x_max",
        "air_jump_h_multiplier": "jump_aerial_speed_x_mul",
        "gravity": "air_accel_y",
        "terminal_velocity": "air_speed_y_stable",
        "air_drift_stick_mul": "air_accel_x_mul",
        "aerial_drift_base": "air_accel_x_add",
        "air_drift_max": "air_speed_x_stable",
        "aerial_friction": "air_brake_x",
        "fast_fall_velocity": "dive_speed_y",
    }
    for target, source in direct.items():
        formula = "source value; nearest Melee movement control"
        if target in {"dash_accel_mul", "dash_accel_base", "dash_max_velocity"}:
            formula += "; Ultimate run maps to Melee dash/run control"
        attrs[target] = record(target, [source], value(source), formula)

    walk_max = value("walk_speed_max")
    for target, ratio in (("slow_walk_max", "walk_slow_speed_mul"),
                          ("mid_walk_point", "walk_middle_ratio"),
                          ("fast_walk_min", "walk_fast_ratio")):
        attrs[target] = record(target, ["walk_speed_max", ratio],
                               round(walk_max * value(ratio), 6),
                               f"walk_speed_max * {ratio}")

    gravity = value("air_accel_y")
    if gravity <= 0:
        raise ValueError("air_accel_y must be positive for jump height conversion")
    for target, height in (("jump_v_initial_velocity", "jump_y"),
                           ("hop_v_initial_velocity", "mini_jump_y")):
        if value(height) <= 0:
            raise ValueError(f"{height} must be positive")
        attrs[target] = record(target, [height, "air_accel_y"],
                               round(math.sqrt(2 * gravity * value(height)), 6),
                               "sqrt(2 * air_accel_y * height); continuous-physics approximation",
                               "assumed")

    jumps_max = value("jump_count_max")
    if jumps_max != 6:
        raise ValueError("this Kirby proof of life requires six total jumps / five Melee air-jump states")
    record("jumps.max", ["jump_count_max"], int(jumps_max), "source total jump count")
    aerial_height = value("jump_aerial_y")
    if aerial_height <= 0:
        raise ValueError("jump_aerial_y must be positive")
    first_air_vy = math.sqrt(2 * gravity * aerial_height)
    hops = baseline_hops(baseline)
    air_vy = [round(first_air_vy * hop / hops[0], 6) for hop in hops]
    record("jumps.air_vy", ["jump_aerial_y", "air_accel_y"], air_vy,
           "sqrt(2 * air_accel_y * jump_aerial_y) * (Melee Kirby hop_i / hop_1); "
           "Ultimate has no per-hop impulse data in this IR", "assumed")

    geno = {
        "geno": 3,
        "fighters": [{
            "attach": "kirby",
            "name": "Kirby (Ultimate movement proof of life)",
            "attributes": attrs,
            "jumps": {"max": int(jumps_max), "air_vy": air_vy},
        }],
    }
    mod = {
        "id": MOD_ID,
        "name": "Kirby (Ultimate movement proof of life)",
        "version": "0.1.0",
        "kind": "fighter",
        "description": "Geno movement overlay on vanilla Melee Kirby; inferred from Ultimate 13.0.2 IR parameters. Existing Melee Kirby model, animations, crouch and status logic remain in use.",
        "requires": [],
        "conflicts": [],
    }
    manifest = {
        "source_document_id": ir["document_id"],
        "source_revision": ir["subject"].get("distribution", {}).get("version"),
        "source_ir_sha256": ir_sha256,
        "melee_kirby_baseline_sha256": baseline_sha256,
        "target": "Geno v3 overlay attached to vanilla Melee Kirby",
        "mappings": mappings,
        "melee_air_jump_baseline": hops,
        "omitted_fields": {
            "jump_initial_y": "Meaning and relation to jump_y are not established; no matching Melee parameter is asserted.",
            "squat_walk_type": "False in Ultimate; Melee Kirby's existing crouch actions handle crouch, with no crouch-walk added.",
            "run_animation_scaling": "Ultimate IR does not establish a conversion to Melee animation rate.",
            "ground_max_horizontal_velocity": "Ultimate IR has no clearly corresponding cap; retain Melee Kirby's value.",
            "body_and_actions": "Ultimate body collision and action/status transition tables are absent from the IR; existing Melee Kirby behavior supplies them.",
        },
        "limitations": [
            "Height-to-impulse conversion uses continuous kinematics; live timing/height must be measured in Melee.",
            "Air jump impulses use Melee Kirby's five-hop shape, scaled to Ultimate's inferred first-hop height; Ultimate per-hop velocities are unknown.",
            "Ultimate and Melee movement control fields are nearest semantic matches, not verified runtime equivalences.",
            "No Ultimate animations, model, collision body, status logic, or asset bytes are included.",
        ],
    }
    return mod, geno, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=DEFAULT_IR)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--out-parent", type=Path, default=ROOT / "_build/tmp/ultimate-kirby-mods")
    args = parser.parse_args()
    ir_bytes = args.ir.read_bytes()
    baseline_bytes = args.baseline.read_bytes()
    mod, geno, manifest = convert(
        json.loads(ir_bytes), json.loads(baseline_bytes),
        hashlib.sha256(ir_bytes).hexdigest(), hashlib.sha256(baseline_bytes).hexdigest(),
    )
    out = args.out_parent / MOD_ID
    out.mkdir(parents=True, exist_ok=True)
    # Without files/, the mod scanner treats the mod root as a legacy disc
    # payload and would expose geno.json and the manifest as disc files.
    (out / "files").mkdir(exist_ok=True)
    for name, document in (("mod.json", mod), ("geno.json", geno), ("source-manifest.json", manifest)):
        (out / name).write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out.resolve())


if __name__ == "__main__":
    main()
